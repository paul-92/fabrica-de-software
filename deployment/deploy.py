"""Single-VM immutable release activation and rollback orchestration."""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4

from asep.maintenance import MaintenanceGate
from deployment.backup import BackupError, create_backup, verify_backup

RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


class DeployError(RuntimeError):
    pass


class UnsafeRollbackError(DeployError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    app_version: str
    expected_sqlite_schema: str
    minimum_sqlite_schema: str


@dataclass(frozen=True, slots=True)
class DeployConfig:
    releases_root: Path
    current_link: Path
    database: Path
    hosted_root: Path
    backup_root: Path
    maintenance_root: Path
    operations_root: Path
    readiness_timeout: float = 30.0
    readiness_interval: float = 1.0
    retention_count: int = 7
    windows_mode: bool = False

    def __post_init__(self) -> None:
        paths = (
            "releases_root", "current_link", "database", "hosted_root",
            "backup_root", "maintenance_root", "operations_root",
        )
        for field in paths:
            value = getattr(self, field).expanduser()
            if not value.is_absolute():
                raise DeployError(f"{field} must be absolute.")
            object.__setattr__(self, field, value.absolute())
        expected_parent = self.releases_root.parent / "current" if self.windows_mode else self.releases_root.parent
        if self.current_link.parent != expected_parent:
            raise DeployError("Current pointer and releases root must share the ASEP installation root.")
        if self.readiness_timeout <= 0 or self.readiness_interval <= 0 or self.readiness_interval > self.readiness_timeout:
            raise DeployError("Readiness timing must be positive and bounded.")
        if self.retention_count < 1:
            raise DeployError("Retention count must be at least one.")


class ServiceController(Protocol):
    def restart(self) -> None: ...


class RuntimeProbe(Protocol):
    def wait_ready(self, timeout: float, interval: float) -> None: ...
    def smoke(self) -> None: ...


class PreflightRunner(Protocol):
    def run(self, release: Path) -> None: ...


class SystemdServiceController:
    def restart(self) -> None:
        completed = subprocess.run(
            ("systemctl", "restart", "asep-backend.service", "asep-frontend.service"),
            check=False, capture_output=True, text=True, timeout=60,
        )
        if completed.returncode != 0:
            raise DeployError("ASEP service restart failed.")


class WindowsServiceController:
    def __init__(self, root: Path) -> None:
        self.root = root

    def restart(self) -> None:
        completed = subprocess.run(
            (sys.executable, "-m", "deployment.windows_runtime", "restart", "--root", str(self.root)),
            check=False, capture_output=True, text=True, timeout=90, shell=False,
        )
        if completed.returncode != 0:
            raise DeployError("ASEP Windows runtime restart failed.")


class LocalRuntimeProbe:
    @staticmethod
    def _status(url: str, timeout: float = 5.0) -> int:
        try:
            with urlopen(url, timeout=timeout) as response:
                return response.status
        except HTTPError as exc:
            return exc.code
        except (OSError, URLError) as exc:
            raise DeployError("Local runtime request failed.") from exc

    def wait_ready(self, timeout: float, interval: float) -> None:
        deadline = time.monotonic() + timeout
        while True:
            try:
                if self._status("http://127.0.0.1:8000/api/v1/ready") == 200:
                    return
            except DeployError:
                pass
            if time.monotonic() >= deadline:
                raise DeployError("Internal readiness timed out.")
            time.sleep(min(interval, max(0.0, deadline - time.monotonic())))

    def smoke(self) -> None:
        checks = (
            ("http://127.0.0.1:8000/api/v1/health", {200}),
            ("http://127.0.0.1:3000/", {200}),
            ("http://127.0.0.1:8000/api/v1/access/session", {401}),
        )
        if any(self._status(url) not in expected for url, expected in checks):
            raise DeployError("Local smoke check failed.")


class CandidatePreflightRunner:
    def __init__(self, *, windows_mode: bool = False) -> None:
        self.windows_mode = windows_mode

    def run(self, release: Path) -> None:
        executable = release / ".venv" / ("Scripts/python.exe" if self.windows_mode else "bin/python")
        if self.windows_mode:
            from deployment.windows_runtime import load_environment

            environment = load_environment(release.parent.parent / "config" / "production.env")
        else:
            environment = dict(os.environ)
        environment["ASEP_RELEASE_ROOT"] = str(release)
        environment["ASEP_AGENT_CATALOG_DIRECTORY"] = str(release / "registry")
        completed = subprocess.run(
            (str(executable), "-m", "deployment.preflight"), cwd=release,
            env=environment, check=False, capture_output=True, text=True, timeout=60,
        )
        if completed.returncode != 0:
            raise DeployError("Candidate production preflight failed.")


class DeployLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise DeployError("Another or abandoned deploy lock is present.") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "created_at": datetime.now(UTC).isoformat()}, stream)
        self.held = True

    def release(self) -> None:
        if self.held:
            self.path.unlink(missing_ok=True)
            self.held = False


class ReleaseLayout:
    def __init__(self, releases_root: Path, current_link: Path) -> None:
        self.releases_root = releases_root.expanduser().resolve()
        self.current_link = current_link.expanduser().absolute()

    def release(self, release_id: str) -> Path:
        if release_id in {".", ".."} or RELEASE_ID.fullmatch(release_id) is None:
            raise DeployError("Release id is invalid.")
        expected = self.releases_root / release_id
        if not expected.is_dir() or expected.is_symlink():
            raise DeployError("Release does not exist as an immutable directory.")
        resolved = expected.resolve()
        if resolved.parent != self.releases_root:
            raise DeployError("Release escaped releases root.")
        return resolved

    def active(self) -> Path:
        if not self.current_link.is_symlink():
            raise DeployError("Current release must be a symbolic link.")
        target = self.current_link.resolve(strict=True)
        if target.parent != self.releases_root or not target.is_dir():
            raise DeployError("Current release escaped releases root.")
        return target

    def activate(self, release: Path) -> None:
        if release.parent != self.releases_root:
            raise DeployError("Activation target escaped releases root.")
        temporary = self.current_link.parent / f".{self.current_link.name}.{uuid4().hex}.tmp"
        try:
            os.symlink(release, temporary, target_is_directory=True)
            os.replace(temporary, self.current_link)
        finally:
            temporary.unlink(missing_ok=True)


def _is_reparse(path: Path) -> bool:
    info = path.stat(follow_symlinks=False)
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


class WindowsReleaseLayout:
    """Atomic JSON pointer activation without symlinks or junctions."""

    def __init__(self, releases_root: Path, current_pointer: Path) -> None:
        raw_releases = releases_root.expanduser().absolute()
        if not raw_releases.is_dir() or _is_reparse(raw_releases):
            raise DeployError("Windows releases root is unavailable or unsafe.")
        self.releases_root = raw_releases.resolve()
        self.current_pointer = current_pointer.expanduser().absolute()

    def release(self, release_id: str) -> Path:
        if not isinstance(release_id, str) or release_id in {".", ".."} or RELEASE_ID.fullmatch(release_id) is None:
            raise DeployError("Release id is invalid.")
        expected = self.releases_root / release_id
        if not expected.is_dir() or _is_reparse(expected):
            raise DeployError("Release does not exist as an immutable safe directory.")
        resolved = expected.resolve()
        if resolved.parent != self.releases_root:
            raise DeployError("Release escaped releases root.")
        return resolved

    def active(self) -> Path:
        if (_is_reparse(self.current_pointer.parent) or not self.current_pointer.is_file()
                or _is_reparse(self.current_pointer)):
            raise DeployError("Current release pointer is unavailable or unsafe.")
        try:
            value = json.loads(self.current_pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeployError("Current release pointer is invalid.") from exc
        if set(value) != {"release_id"}:
            raise DeployError("Current release pointer format is invalid.")
        return self.release(value["release_id"])

    def activate(self, release: Path) -> None:
        release = release.resolve()
        if release.parent != self.releases_root or _is_reparse(release):
            raise DeployError("Activation target escaped releases root or is unsafe.")
        self.current_pointer.parent.mkdir(parents=True, exist_ok=True)
        if _is_reparse(self.current_pointer.parent):
            raise DeployError("Current pointer directory is unsafe.")
        temporary = self.current_pointer.parent / f".{self.current_pointer.name}.{uuid4().hex}.tmp"
        try:
            temporary.write_text(json.dumps({"release_id": release.name}, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, self.current_pointer)
        finally:
            temporary.unlink(missing_ok=True)


def read_manifest(release: Path) -> ReleaseManifest:
    try:
        payload = json.loads((release / "deployment" / "release.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeployError("Release manifest is missing or invalid.") from exc
    if payload.get("format_version") != 1:
        raise DeployError("Release manifest format is unsupported.")
    values = [payload.get(name) for name in ("app_version", "expected_sqlite_schema", "minimum_sqlite_schema")]
    if any(not isinstance(value, str) or not value.strip() or len(value) > 64 for value in values):
        raise DeployError("Release manifest fields are invalid.")
    return ReleaseManifest(*values)


def current_schema(database: Path) -> str:
    try:
        uri = database.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            row = connection.execute("SELECT value FROM schema_metadata WHERE key='schema_version'").fetchone()
    except sqlite3.Error as exc:
        raise DeployError("Unable to inspect SQLite schema without migration.") from exc
    if row is None:
        raise DeployError("SQLite schema metadata is missing.")
    return str(row[0])


def assert_schema_compatible(database: Path, manifest: ReleaseManifest) -> str:
    observed = current_schema(database)
    if observed != manifest.expected_sqlite_schema:
        raise UnsafeRollbackError("Persistent schema is incompatible with the release binary.")
    return observed


class AuditRecord:
    def __init__(self, root: Path, candidate: str, previous: str | None) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8] + ".json")
        self.value: dict[str, object] = {
            "candidate_release": candidate, "previous_release": previous,
            "timestamp_utc": datetime.now(UTC).isoformat(), "stage": "created",
            "outcome": "running", "backup_id": None,
            "rollback_performed": False,
        }
        self.update("created", "running")

    def update(self, stage: str, outcome: str, *, backup_id: str | None = None) -> None:
        self.value.update({"stage": stage, "outcome": outcome})
        if backup_id is not None:
            self.value["backup_id"] = backup_id
        if stage == "rollback":
            self.value["rollback_performed"] = outcome == "rolled_back"
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)


class Deployer:
    def __init__(
        self, config: DeployConfig, *, services: ServiceController | None = None,
        probe: RuntimeProbe | None = None, preflight: PreflightRunner | None = None,
    ) -> None:
        self.config = config
        self.layout = (WindowsReleaseLayout(config.releases_root, config.current_link)
                       if config.windows_mode else ReleaseLayout(config.releases_root, config.current_link))
        self.services = services or (WindowsServiceController(config.releases_root.parent)
                                     if config.windows_mode else SystemdServiceController())
        self.probe = probe or LocalRuntimeProbe()
        self.preflight = preflight or CandidatePreflightRunner(windows_mode=config.windows_mode)
        self.gate = MaintenanceGate(config.maintenance_root)
        self.lock = DeployLock(config.operations_root / "deploy.lock")

    def plan(self, release_id: str) -> dict[str, object]:
        candidate = self.layout.release(release_id)
        previous = self.layout.active()
        manifest = read_manifest(candidate)
        assert_schema_compatible(self.config.database, manifest)
        self._structural_candidate(candidate)
        return {
            "candidate_release": candidate.name, "previous_release": previous.name,
            "schema": manifest.expected_sqlite_schema,
            "actions": ["preflight", "maintenance", "backup", "activate", "restart", "readiness", "smoke", "release-maintenance"],
            "runtime_checks_executed": False,
            "service_restart": (["deployment.windows_runtime restart"] if self.config.windows_mode
                                else ["asep-backend.service", "asep-frontend.service"]),
            "readiness_url": "http://127.0.0.1:8000/api/v1/ready",
            "smoke_urls": ["http://127.0.0.1:8000/api/v1/health", "http://127.0.0.1:3000/", "http://127.0.0.1:8000/api/v1/access/session"],
        }

    def deploy(self, release_id: str) -> Path:
        self.lock.acquire()
        maintenance_active = False
        activated = False
        audit = None
        previous = None
        try:
            candidate = self.layout.release(release_id)
            previous = self.layout.active()
            audit = AuditRecord(self.config.operations_root / "deploys", candidate.name, previous.name)
            manifest = read_manifest(candidate)
            assert_schema_compatible(self.config.database, manifest)
            self._structural_candidate(candidate)
            self.preflight.run(candidate)
            audit.update("preflight", "passed")
            self.gate.enter(30.0); maintenance_active = True
            audit.update("maintenance", "active")
            backup = create_backup(
                self.config.database, self.config.hosted_root, self.config.backup_root,
                self.config.maintenance_root, retention_count=self.config.retention_count,
                maintenance_already_active=True, release_root=self.config.current_link,
            )
            verify_backup(backup)
            audit.update("backup", "passed", backup_id=backup.name)
            self.layout.activate(candidate); activated = True
            audit.update("activation", "passed")
            self._restart_validate()
            self.gate.release(); maintenance_active = False
            audit.update("open", "succeeded")
            return audit.path
        except Exception as exc:
            if activated and previous is not None:
                try:
                    self._rollback_to(previous)
                    if maintenance_active:
                        self.gate.release(); maintenance_active = False
                    if audit is not None:
                        audit.update("rollback", "rolled_back")
                except Exception as rollback_exc:
                    if audit is not None:
                        audit.update("rollback", "unsafe")
                    raise DeployError("Deploy failed and safe automatic rollback did not complete; maintenance remains active.") from rollback_exc
            elif maintenance_active:
                self.gate.release(); maintenance_active = False
                if audit is not None:
                    audit.update("failed-before-activation", "failed")
            elif audit is not None:
                audit.update("failed-before-activation", "failed")
            if isinstance(exc, DeployError | BackupError):
                raise
            raise DeployError("Deploy failed.") from exc
        finally:
            self.lock.release()

    def rollback(self, release_id: str) -> Path:
        self.lock.acquire()
        maintenance_active = False
        audit = None
        try:
            target = self.layout.release(release_id)
            current = self.layout.active()
            audit = AuditRecord(self.config.operations_root / "deploys", target.name, current.name)
            manifest = read_manifest(target)
            assert_schema_compatible(self.config.database, manifest)
            self._structural_candidate(target)
            self.preflight.run(target)
            self.gate.enter(30.0); maintenance_active = True
            self.layout.activate(target)
            self._restart_validate()
            self.gate.release(); maintenance_active = False
            audit.update("manual-rollback", "succeeded")
            return audit.path
        except Exception:
            if audit is not None:
                audit.update("manual-rollback", "unsafe" if maintenance_active else "failed-before-activation")
            if maintenance_active:
                # Target may already be active; keep access closed for operator review.
                pass
            raise
        finally:
            self.lock.release()

    def _rollback_to(self, previous: Path) -> None:
        assert_schema_compatible(self.config.database, read_manifest(previous))
        self.layout.activate(previous)
        self._restart_validate()

    def _restart_validate(self) -> None:
        self.services.restart()
        self.probe.wait_ready(self.config.readiness_timeout, self.config.readiness_interval)
        self.probe.smoke()

    def _structural_candidate(self, candidate: Path) -> None:
        python = (candidate / ".venv" / "Scripts" / "python.exe"
                  if self.config.windows_mode else candidate / ".venv" / "bin" / "python")
        required = (
            python,
            candidate / "frontend" / ".next" / "BUILD_ID",
            candidate / "deployment" / "preflight.py",
        )
        if not all(path.is_file() for path in required):
            raise DeployError("Candidate release is not prepared for activation.")


def _config(args) -> DeployConfig:
    return DeployConfig(
        releases_root=args.releases_root, current_link=args.current_link,
        database=args.database, hosted_root=args.hosted_root, backup_root=args.backup_root,
        maintenance_root=args.maintenance_root, operations_root=args.operations_root,
        windows_mode=args.windows,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ASEP single-VM release operations")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--releases-root", type=Path, default=Path("/opt/asep/releases"))
    common.add_argument("--current-link", type=Path, default=Path("/opt/asep/current"))
    common.add_argument("--database", type=Path, default=Path("/var/lib/asep/asep.db"))
    common.add_argument("--hosted-root", type=Path, default=Path("/var/lib/asep/workspaces"))
    common.add_argument("--backup-root", type=Path, default=Path("/var/backups/asep"))
    common.add_argument("--maintenance-root", type=Path, default=Path("/var/tmp/asep/maintenance"))
    common.add_argument("--operations-root", type=Path, default=Path("/var/lib/asep/deployment"))
    common.add_argument("--windows", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    deploy = commands.add_parser("deploy", parents=[common]); deploy.add_argument("release_id"); deploy.add_argument("--dry-run", action="store_true")
    rollback = commands.add_parser("rollback", parents=[common]); rollback.add_argument("release_id")
    unlock = commands.add_parser("unlock", parents=[common]); unlock.add_argument("--confirm-abandoned", action="store_true", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "unlock":
            lock = args.operations_root / "deploy.lock"
            if not lock.is_file():
                raise DeployError("No deploy lock is present.")
            lock.unlink()
            print("abandoned deploy lock removed")
            return 0
        deployer = Deployer(_config(args))
        result = deployer.plan(args.release_id) if getattr(args, "dry_run", False) else (
            deployer.deploy(args.release_id) if args.command == "deploy" else deployer.rollback(args.release_id)
        )
        print(json.dumps(result, sort_keys=True) if isinstance(result, dict) else result.name)
        return 0
    except (DeployError, BackupError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
