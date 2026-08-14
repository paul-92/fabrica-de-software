"""Bounded, same-origin Private Beta remote acceptance smoke."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import http.cookiejar
import json
import os
import re
import socket
import sys
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener


class SmokeError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"{stage}: {message}")


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("response is not bounded JSON") from exc


class Transport(Protocol):
    def request(self, method: str, url: str, *, json_body: dict[str, Any] | None = None) -> Response: ...


class PortProbe(Protocol):
    def is_reachable(self, host: str, port: int) -> bool: ...


class SocketPortProbe:
    def __init__(self, timeout: float = 2.0) -> None: self.timeout = timeout
    def is_reachable(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=self.timeout): return True
        except OSError: return False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibTransport:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies), _NoRedirect())

    def request(self, method: str, url: str, *, json_body: dict[str, Any] | None = None) -> Response:
        data = None if json_body is None else json.dumps(json_body).encode("utf-8")
        request = Request(url, data=data, method=method, headers={"Accept": "application/json"})
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(request, timeout=self.timeout) as raw:
                return Response(raw.status, dict(raw.headers.items()), raw.read(1_048_577))
        except HTTPError as exc:
            return Response(exc.code, dict(exc.headers.items()), exc.read(1_048_577))
        except (OSError, URLError) as exc:
            raise SmokeError("network", "request failed or timed out") from exc


_SENSITIVE_KEYS = re.compile(r"^(?:password|secret|access_token|refresh_token|cookie|authorization|workspace_(?:root|path))$", re.I)
_ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:\\|/(?:opt|var|home|root|srv|tmp)/)")


def _assert_safe(value: Any, stage: str) -> None:
    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if _SENSITIVE_KEYS.search(str(key)):
                    raise SmokeError(stage, "response exposes a sensitive field")
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str) and _ABSOLUTE_PATH.search(item):
            raise SmokeError(stage, "response exposes an absolute workspace path")
    walk(value)


class RemoteSmoke:
    def __init__(self, base_url: str, email: str, password: str, runtime_id: str,
                 *, release_id: str = "unknown", transport: Transport | None = None,
                 tenant_b: tuple[str, str] | None = None, tenant_transport: Transport | None = None,
                 port_probe: PortProbe | None = None, timeout: float = 10.0) -> None:
        parsed = urlsplit(base_url.rstrip("/"))
        if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise SmokeError("configuration", "base URL must be an HTTPS origin")
        if timeout <= 0 or timeout > 30:
            raise SmokeError("configuration", "timeout must be greater than zero and at most 30 seconds")
        self.base = base_url.rstrip("/")
        self.email, self.password, self.runtime_id = email, password, runtime_id
        self.release_id, self.transport, self.tenant_b = release_id, transport or UrllibTransport(timeout), tenant_b
        self.tenant_transport = tenant_transport
        self.port_probe = port_probe or SocketPortProbe(min(timeout, 2.0))
        self.started = time.monotonic()
        self.execution_id: str | None = None

    def _call(self, stage: str, method: str, path: str, expected: set[int], body=None) -> Response:
        try:
            response = self.transport.request(method, self.base + path, json_body=body)
        except SmokeError as exc:
            raise SmokeError(stage, str(exc).split(": ", 1)[-1]) from exc
        if len(response.body) > 1_048_576:
            raise SmokeError(stage, "response exceeds the 1 MiB smoke bound")
        if response.status not in expected:
            raise SmokeError(stage, f"unexpected HTTP status {response.status}")
        if response.body and "json" in response.headers.get("Content-Type", "application/json").lower():
            try: _assert_safe(response.json(), stage)
            except ValueError as exc: raise SmokeError(stage, str(exc)) from exc
        return response

    def run(self) -> dict[str, Any]:
        self._call("https", "GET", "/", {200})
        http_url = "http://" + urlsplit(self.base).netloc + "/"
        redirect = self.transport.request("GET", http_url)
        location = redirect.headers.get("Location", "")
        if redirect.status not in {301, 302, 307, 308} or not location.startswith(self.base):
            raise SmokeError("http_redirect", "HTTP does not redirect to the HTTPS origin")
        self._call("health", "GET", "/api/v1/health", {200})
        self._call("public_ready", "GET", "/api/v1/ready", {404})
        host = urlsplit(self.base).hostname
        if host is None or any(self.port_probe.is_reachable(host, port) for port in (3000, 8000)):
            raise SmokeError("private_ports", "an application upstream port is publicly reachable")
        self._call("anonymous_private", "GET", "/api/v1/projects", {401})
        login = self._call("login", "POST", "/api/v1/access/login", {200}, {"email": self.email, "password": self.password})
        cookie = login.headers.get("Set-Cookie", "").lower()
        if not all(flag in cookie for flag in ("secure", "httponly", "samesite=lax", "path=/")):
            raise SmokeError("login", "session cookie security attributes are incomplete")
        principal = self._call("session", "GET", "/api/v1/access/session", {200}).json()
        quota_before = self._call("quota_before", "GET", "/api/v1/ai-quotas/me", {200}).json()
        project = self._call("project", "POST", "/api/v1/projects", {201}, {"name": f"Private Beta smoke {datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"}).json()
        project_id = project["project_id"]
        session = self._call("project_session", "POST", f"/api/v1/projects/{project_id}/sessions", {201}, {"title": "Controlled remote smoke"}).json()
        session_id = session["session_id"]
        instruction = "Create smoke_check.py with a function returning 'ok' and a focused pytest test for it."
        request_body = {"session_id": session_id, "runtime_id": self.runtime_id, "instruction": instruction, "execution_mode": "workspace_write"}
        prepared = self._call("prepare", "POST", f"/api/v1/projects/{project_id}/engineering/prepare", {201}, request_body).json()
        if prepared.get("status") != "prepared" or not prepared.get("operational_plan"):
            raise SmokeError("prepare", "execution was not prepared without mutation")
        self.execution_id = prepared["execution_id"]
        approved = self._call("approve", "POST", f"/api/v1/projects/{project_id}/engineering/{self.execution_id}/approve", {200}, request_body).json()
        validations = approved.get("validations") or []
        gate = approved.get("quality_gate") or {}
        if not validations or any(item.get("status") != "passed" for item in validations):
            raise SmokeError("validation", "real validators did not pass")
        if gate.get("decision") != "passed" or approved.get("status") != "completed":
            raise SmokeError("quality_gate", "Quality Gate did not pass")
        usage = self._call("usage", "GET", f"/api/v1/projects/{project_id}/executions/{self.execution_id}/ai-usage", {200}).json()
        items = usage.get("items", [])
        if not items or any(item.get("execution_id") != self.execution_id for item in items):
            raise SmokeError("usage", "provider usage is not attributed to the execution")
        quota_after = self._call("quota_after", "GET", "/api/v1/ai-quotas/me", {200}).json()
        before_calls = (quota_before.get("usage") or {}).get("calls")
        after_calls = (quota_after.get("usage") or {}).get("calls")
        if not isinstance(before_calls, int) or not isinstance(after_calls, int) or after_calls <= before_calls:
            raise SmokeError("quota", "quota call usage did not increase")
        history = self._call("history", "GET", f"/api/v1/projects/{project_id}/sessions/{session_id}/executions", {200}).json()
        if self.execution_id not in {item.get("execution_id") for item in history.get("items", [])}:
            raise SmokeError("history", "execution is absent from session history")
        reopened = self._call("reopen", "GET", f"/api/v1/projects/{project_id}/executions/{self.execution_id}", {200}).json()
        if reopened.get("session_id") != session_id:
            raise SmokeError("reopen", "direct execution URL cannot reconstruct state")
        if self.tenant_b:
            other = self.tenant_transport or UrllibTransport(getattr(self.transport, "timeout", 10.0))
            other.request("POST", self.base + "/api/v1/access/login", json_body={"email": self.tenant_b[0], "password": self.tenant_b[1]})
            denied = (
                other.request("GET", self.base + f"/api/v1/projects/{project_id}"),
                other.request("GET", self.base + f"/api/v1/projects/{project_id}/executions/{self.execution_id}"),
            )
            if any(item.status not in {403, 404} for item in denied):
                raise SmokeError("tenant_isolation", "tenant B can access tenant A state")
        else:
            raise SmokeError("tenant_isolation", "tenant B smoke credentials are required")
        self._call("logout", "POST", "/api/v1/access/logout", {200})
        self._call("logout_session", "GET", "/api/v1/access/session", {401})
        return {"release_id": self.release_id, "timestamp": datetime.now(UTC).isoformat(),
                "execution_id": self.execution_id, "status": "passed",
                "latency_ms": round((time.monotonic() - self.started) * 1000)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ASEP Private Beta remote smoke")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        required = {name: os.environ.get(name, "") for name in ("ASEP_SMOKE_EMAIL", "ASEP_SMOKE_PASSWORD", "ASEP_SMOKE_RUNTIME_ID", "ASEP_SMOKE_TENANT_B_EMAIL", "ASEP_SMOKE_TENANT_B_PASSWORD")}
        if any(not value for value in required.values()):
            raise SmokeError("configuration", "required smoke credential environment is incomplete")
        result = RemoteSmoke(args.base_url, required["ASEP_SMOKE_EMAIL"], required["ASEP_SMOKE_PASSWORD"], required["ASEP_SMOKE_RUNTIME_ID"],
                             release_id=os.environ.get("ASEP_RELEASE_ID", "unknown"), timeout=args.timeout,
                             tenant_b=(required["ASEP_SMOKE_TENANT_B_EMAIL"], required["ASEP_SMOKE_TENANT_B_PASSWORD"])).run()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (SmokeError, KeyError, ValueError) as exc:
        message = str(exc) if isinstance(exc, SmokeError) else "response contract is incomplete"
        print(message[:240], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
