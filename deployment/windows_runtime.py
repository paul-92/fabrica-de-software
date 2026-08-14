"""Bounded Windows process supervisor for one ASEP Private Beta instance."""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Callable, Protocol
from uuid import uuid4
from urllib.error import URLError
from urllib.request import urlopen

RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
SENSITIVE = re.compile(r"password|secret|token|cookie|api[_-]?key|authorization", re.I)


class RuntimeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    root: Path
    releases: Path
    pointer: Path
    environment: Path
    runtime: Path
    logs: Path

    @classmethod
    def from_root(cls, root: Path) -> "RuntimePaths":
        root = root.expanduser().resolve()
        if not root.is_absolute(): raise RuntimeError("Runtime root must be absolute.")
        return cls(root, root / "releases", root / "current" / "active-release.json",
                   root / "config" / "production.env", root / "temp" / "runtime", root / "logs")

    def release(self) -> Path:
        try: value = json.loads(self.pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise RuntimeError("Active release pointer is missing or invalid.") from exc
        release_id = value.get("release_id")
        if not isinstance(release_id, str) or RELEASE_ID.fullmatch(release_id) is None:
            raise RuntimeError("Active release id is invalid.")
        candidate = self.releases / release_id
        if not candidate.is_dir() or candidate.is_symlink() or candidate.resolve().parent != self.releases.resolve():
            raise RuntimeError("Active release escaped releases root or is unavailable.")
        return candidate.resolve()


def load_environment(path: Path, inherited: dict[str, str] | None = None) -> dict[str, str]:
    result = dict(os.environ if inherited is None else inherited)
    try: lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc: raise RuntimeError("External production environment is unavailable.") from exc
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"): continue
        if "=" not in line: raise RuntimeError(f"Environment line {number} is invalid.")
        key, value = line.split("=", 1); key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key): raise RuntimeError(f"Environment line {number} has an invalid name.")
        result[key] = os.path.expandvars(value.strip())
    return result


def _rotate_log(path: Path, limit: int = 5 * 1024 * 1024) -> None:
    if path.is_file() and path.stat().st_size >= limit:
        rotated = path.with_suffix(path.suffix + ".1")
        rotated.unlink(missing_ok=True)
        os.replace(path, rotated)


class Processes(Protocol):
    def spawn(self, command: tuple[str, ...], cwd: Path, environment: dict[str, str], stdout: Path, stderr: Path) -> int: ...
    def token(self, pid: int) -> str | None: ...
    def alive(self, pid: int, token: str | None = None) -> bool: ...
    def terminate_tree(self, pid: int, timeout: float, token: str | None = None) -> bool: ...


class WindowsProcesses:
    def spawn(self, command, cwd, environment, stdout, stderr):
        out = stdout.open("a", encoding="utf-8"); err = stderr.open("a", encoding="utf-8")
        try:
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, shell=False,
                                       creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
            return process.pid
        finally: out.close(); err.close()
    def token(self, pid):
        if os.name != "nt" or not isinstance(pid, int) or pid <= 0: return None
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle: return None
        try:
            created, exited, kernel_time, user_time = (ctypes.c_ulonglong() for _ in range(4))
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in (created, exited, kernel_time, user_time))): return None
            return str(created.value)
        finally: kernel.CloseHandle(handle)
    def alive(self, pid, token=None):
        if not isinstance(pid, int) or pid <= 0: return False
        observed = self.token(pid)
        return observed is not None and (token is None or observed == token)
    def terminate_tree(self, pid, timeout, token=None):
        if not self.alive(pid, token): return token is None and not self.alive(pid)
        subprocess.run(("taskkill.exe", "/PID", str(pid), "/T", "/F"), capture_output=True,
                       text=True, check=False, timeout=min(timeout, 15), shell=False)
        deadline = time.monotonic() + timeout
        while self.alive(pid, token) and time.monotonic() < deadline: time.sleep(.1)
        return not self.alive(pid, token)


class Supervisor:
    def __init__(self, paths: RuntimePaths, processes: Processes | None = None, *, timeout: float = 30.0,
                 readiness: Callable[[], bool] | None = None, port_free: Callable[[int], bool] | None = None) -> None:
        self.paths, self.processes, self.timeout = paths, processes or WindowsProcesses(), timeout
        self.metadata = paths.runtime / "instance.json"; self.lock = paths.runtime / "instance.lock"
        self.readiness = readiness or self._readiness
        self.port_free = port_free or self._port_free

    def _read(self) -> dict:
        try: return json.loads(self.metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return {}

    def status(self) -> str:
        value = self._read()
        if not value: return "stopped" if not self.lock.exists() else "starting"
        alive = [self.processes.alive(value.get(name, -1), value.get(name.replace("_pid", "_token"))) for name in ("backend_pid", "frontend_pid")]
        if all(alive): return "running"
        if any(alive): return "degraded"
        return "stale"

    @staticmethod
    def _port_free(port: int) -> bool:
        with socket.socket() as probe:
            probe.settimeout(.2)
            return probe.connect_ex(("127.0.0.1", port)) != 0

    @staticmethod
    def _readiness() -> bool:
        try:
            with urlopen("http://127.0.0.1:8000/api/v1/ready", timeout=1) as response: return response.status == 200
        except (OSError, URLError): return False

    def acquire(self) -> None:
        self.paths.runtime.mkdir(parents=True, exist_ok=True)
        try: descriptor = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc: raise RuntimeError("A runtime lock already exists.") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream: stream.write(str(os.getpid()))

    def run(self) -> None:
        self.acquire(); pids: list[tuple[int, str | None]] = []
        try:
            release = self.paths.release(); environment = load_environment(self.paths.environment)
            environment["ASEP_RELEASE_ROOT"] = str(release)
            environment["ASEP_AGENT_CATALOG_DIRECTORY"] = str(release / "registry")
            for directory in (self.paths.logs / "backend", self.paths.logs / "frontend", self.paths.logs / "supervisor"):
                directory.mkdir(parents=True, exist_ok=True)
            if not all(self.port_free(port) for port in (3000, 8000)): raise RuntimeError("A required loopback port is occupied.")
            python = release / ".venv" / "Scripts" / "python.exe"
            backend = (str(python), "-m", "uvicorn", "asep.api.composition:create_default_app", "--factory", "--host", "127.0.0.1", "--port", "8000")
            frontend = ("npm.cmd", "start", "--", "--hostname", "127.0.0.1", "--port", "3000")
            for log in (self.paths.logs/"backend"/"stdout.log", self.paths.logs/"backend"/"stderr.log",
                        self.paths.logs/"frontend"/"stdout.log", self.paths.logs/"frontend"/"stderr.log"):
                _rotate_log(log)
            backend_pid = self.processes.spawn(backend, release, environment, self.paths.logs/"backend"/"stdout.log", self.paths.logs/"backend"/"stderr.log")
            pids.append((backend_pid, self.processes.token(backend_pid)))
            if not self.processes.alive(*pids[0]): raise RuntimeError("Backend failed during start.")
            frontend_pid = self.processes.spawn(frontend, release/"frontend", environment, self.paths.logs/"frontend"/"stdout.log", self.paths.logs/"frontend"/"stderr.log")
            pids.append((frontend_pid, self.processes.token(frontend_pid)))
            value = {"format_version": 1, "instance_id": uuid4().hex, "state": "starting", "release_id": release.name,
                     "supervisor_pid": os.getpid(), "supervisor_token": self.processes.token(os.getpid()),
                     "backend_pid": pids[0][0], "backend_token": pids[0][1], "frontend_pid": pids[1][0], "frontend_token": pids[1][1]}
            self._write(value)
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if not all(self.processes.alive(*process) for process in pids): raise RuntimeError("A component died during start.")
                if self.readiness(): break
                time.sleep(.2)
            else: raise RuntimeError("Backend readiness timed out.")
            value["state"] = "running"; self._write(value)
            while all(self.processes.alive(*process) for process in pids): time.sleep(1)
            raise RuntimeError("A runtime component stopped unexpectedly.")
        finally:
            for pid, token in reversed(pids): self.processes.terminate_tree(pid, self.timeout, token)
            self.metadata.unlink(missing_ok=True); self.lock.unlink(missing_ok=True)

    def _write(self, value: dict) -> None:
        temporary = self.metadata.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8"); os.replace(temporary, self.metadata)

    def stop(self) -> None:
        value = self._read()
        if not value:
            if self.lock.exists(): raise RuntimeError("Runtime is starting without valid metadata.")
            return
        supervisor = value.get("supervisor_pid")
        if not isinstance(supervisor, int) or supervisor <= 0: raise RuntimeError("Runtime metadata is stale.")
        token = value.get("supervisor_token")
        components = [(value.get(name), value.get(name.replace("_pid", "_token"))) for name in ("backend_pid", "frontend_pid")]
        if not isinstance(token, str) or not self.processes.alive(supervisor, token):
            if any(isinstance(pid, int) and self.processes.alive(pid, process_token) for pid, process_token in components):
                raise RuntimeError("Runtime metadata is stale while a recorded component remains alive.")
        elif not self.processes.terminate_tree(supervisor, self.timeout, token):
            raise RuntimeError("Runtime process tree did not stop within timeout.")
        if any(isinstance(pid, int) and self.processes.alive(pid, process_token) for pid, process_token in components):
            raise RuntimeError("A recorded runtime component remains alive after stop.")
        self.metadata.unlink(missing_ok=True); self.lock.unlink(missing_ok=True)


def _parser():
    parser = argparse.ArgumentParser(description="ASEP Windows Private Beta runtime")
    parser.add_argument("command", choices=("start", "run", "stop", "status", "restart")); parser.add_argument("--root", type=Path, required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv); supervisor = Supervisor(RuntimePaths.from_root(args.root))
    try:
        if args.command == "run": supervisor.run()
        elif args.command == "status": print(supervisor.status())
        elif args.command == "stop": supervisor.stop(); print("stopped")
        elif args.command == "restart": supervisor.stop(); return main(["start", "--root", str(args.root)])
        else:
            state = supervisor.status()
            if state != "stopped": raise RuntimeError(f"Runtime cannot start from state {state}.")
            log = supervisor.paths.logs / "supervisor"; log.mkdir(parents=True, exist_ok=True)
            command = (sys.executable, "-m", "deployment.windows_runtime", "run", "--root", str(args.root))
            with (log/"stdout.log").open("a",encoding="utf-8") as out, (log/"stderr.log").open("a",encoding="utf-8") as err:
                subprocess.Popen(command, cwd=supervisor.paths.release(), stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False,
                                 creationflags=getattr(subprocess,"DETACHED_PROCESS",0)|getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                state=supervisor.status()
                if state=="running": print("running"); return 0
                if state in {"degraded","stale"}: raise RuntimeError(f"Runtime start failed with state {state}.")
                time.sleep(.2)
            raise RuntimeError("Runtime start timed out.")
        return 0
    except RuntimeError as exc:
        message=str(exc)
        if SENSITIVE.search(message): message="Runtime operation failed."
        print(message[:240],file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
