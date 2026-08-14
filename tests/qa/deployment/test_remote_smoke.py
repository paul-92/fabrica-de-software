from __future__ import annotations

import json

import pytest

from deployment import smoke
from deployment.smoke import RemoteSmoke, Response, SmokeError


def response(status=200, value=None, **headers):
    body = b"" if value is None else json.dumps(value).encode()
    return Response(status, {"Content-Type": "application/json", **headers}, body)


class FakeTransport:
    def __init__(self, failure=None, leak=None): self.failure, self.leak, self.calls, self.logged_out = failure, leak, [], False
    def request(self, method, url, *, json_body=None):
        path = url.split("beta.example.com", 1)[-1]
        self.calls.append((method, path))
        stage = {
            "/": "frontend", "/api/v1/health": "health", "/api/v1/access/login": "login",
        }.get(path)
        if stage is not None and self.failure == stage: return response(503)
        if url.startswith("http://"): return response(308, Location="https://beta.example.com/")
        if path == "/": return response(200, "frontend")
        if path == "/api/v1/health": return response(200, {"status": "ok"})
        if path == "/api/v1/ready": return response(404, {"detail": "Not Found"})
        if path == "/api/v1/projects" and method == "GET": return response(401, {"detail": "Authentication required."})
        if path == "/api/v1/access/login":
            return response(200, {"user_id": "u1"}, **{"Set-Cookie": "asep_session=x; Path=/; Secure; HttpOnly; SameSite=Lax"})
        if path == "/api/v1/access/session": return response(401, {"detail": "Authentication required."}) if self.logged_out else response(200, {"user_id": "u1"})
        if path == "/api/v1/ai-quotas/me":
            count = sum(1 for call in self.calls if "/approve" in call[1])
            return response(500 if self.failure == "quota" and count else 200, {"usage": {"calls": count}})
        if path == "/api/v1/projects" and method == "POST":
            return response(201, {"project_id": "p1", **({"workspace_path": "/var/lib/asep/workspaces/x"} if self.leak else {})})
        if path == "/api/v1/projects/p1/sessions": return response(201, {"session_id": "s1"})
        if path.endswith("/engineering/prepare"):
            return response(500 if self.failure == "prepare" else 201, {"execution_id": "e1", "status": "prepared", "operational_plan": {"steps": [{}]}})
        if path.endswith("/engineering/e1/approve"):
            if self.failure == "approve": return response(500)
            status = "blocked" if self.failure == "validation" else "passed"
            return response(200, {"execution_id": "e1", "status": "completed", "validations": [{"status": status}], "quality_gate": {"decision": status}})
        if path.endswith("/executions/e1/ai-usage"):
            return response(200, {"items": [] if self.failure == "usage" else [{"execution_id": "e1", "total_tokens": None}]})
        if path.endswith("/sessions/s1/executions"):
            return response(500 if self.failure == "history" else 200, {"items": [{"execution_id": "e1"}]})
        if path.endswith("/executions/e1"):
            return response(200, {"execution_id": "e1", "session_id": "s1"})
        if path == "/api/v1/access/logout":
            if self.failure == "logout": return response(500)
            self.logged_out = True
            return response(200, {"logged_out": True})
        raise AssertionError((method, url))


class TenantTransport:
    def request(self, method, url, *, json_body=None):
        return response(200, {}) if url.endswith("/login") else response(404, {"detail": "Resource not found."})


class ClosedPorts:
    def is_reachable(self, host, port): return False


class OpenPort:
    def is_reachable(self, host, port): return port == 8000


def runner(**kwargs):
    transport = kwargs.pop("transport", FakeTransport())
    port_probe = kwargs.pop("port_probe", ClosedPorts())
    return RemoteSmoke("https://beta.example.com", "a@example.com", "secret", "runtime",
                       transport=transport, tenant_b=("b@example.com", "secret"),
                       tenant_transport=TenantTransport(), port_probe=port_probe, **kwargs)


def test_complete_remote_smoke():
    result = runner(release_id="r1").run()
    assert result["status"] == "passed" and result["execution_id"] == "e1" and result["release_id"] == "r1"


@pytest.mark.parametrize("failure,stage", [("health","health"),("frontend","https"),("login","login"),("prepare","prepare"),("approve","approve"),("validation","validation"),("usage","usage"),("quota","quota_after"),("history","history"),("logout","logout")])
def test_critical_failure_is_bounded_and_identifies_stage(failure, stage):
    with pytest.raises(SmokeError, match=f"^{stage}:") as caught: runner(transport=FakeTransport(failure)).run()
    assert "secret" not in str(caught.value).lower() and len(str(caught.value)) < 240


def test_http_redirect_and_https_origin_contract():
    with pytest.raises(SmokeError, match="configuration"):
        RemoteSmoke("http://beta.example.com", "a", "b", "r")


def test_public_upstream_port_fails_closed():
    with pytest.raises(SmokeError, match="private_ports"):
        runner(port_probe=OpenPort()).run()


def test_sensitive_path_is_rejected_and_redacted():
    with pytest.raises(SmokeError, match="sensitive field") as caught:
        runner(transport=FakeTransport(leak=True)).run()
    assert "/var/lib" not in str(caught.value)


def test_cli_failure_has_nonzero_exit_and_no_credentials(monkeypatch, capsys):
    monkeypatch.delenv("ASEP_SMOKE_PASSWORD", raising=False)
    assert smoke.main(["--base-url", "https://beta.example.com"]) == 1
    assert "password" not in capsys.readouterr().err.lower()


def test_timeout_is_positive_and_bounded():
    with pytest.raises(SmokeError, match="configuration"):
        RemoteSmoke("https://beta.example.com", "a", "b", "r", timeout=31)
