from __future__ import annotations

import json
from pathlib import Path

import pytest

from asep.sqlite import SQLiteDatabase
from deployment import deploy as deploy_module
from deployment.deploy import (
    DeployConfig, DeployError, Deployer, WindowsReleaseLayout,
)


def prepared(root: Path, release_id: str) -> Path:
    release = root / release_id
    (release / ".venv" / "Scripts").mkdir(parents=True)
    (release / ".venv" / "Scripts" / "python.exe").write_text("prepared", encoding="utf-8")
    (release / "frontend" / ".next").mkdir(parents=True)
    (release / "frontend" / ".next" / "BUILD_ID").write_text("build", encoding="utf-8")
    (release / "deployment").mkdir()
    (release / "deployment" / "preflight.py").write_text("prepared", encoding="utf-8")
    (release / "deployment" / "release.json").write_text(json.dumps({
        "format_version": 1, "app_version": "0.1.0",
        "expected_sqlite_schema": "4", "minimum_sqlite_schema": "4",
    }), encoding="utf-8")
    return release.resolve()


def layout(tmp_path: Path):
    root = tmp_path / "ASEP-Beta"
    releases = root / "releases"; releases.mkdir(parents=True)
    first = prepared(releases, "release-A"); second = prepared(releases, "release-B")
    pointer = root / "current" / "active-release.json"; pointer.parent.mkdir()
    pointer.write_text('{"release_id":"release-A"}', encoding="utf-8")
    return WindowsReleaseLayout(releases, pointer), first, second, pointer


class Services:
    def __init__(self, fail_calls=()): self.calls = 0; self.fail_calls = set(fail_calls)
    def restart(self):
        self.calls += 1
        if self.calls in self.fail_calls: raise DeployError("restart failed")


class Probe:
    def __init__(self, fail_first=False): self.ready = 0; self.smokes = 0; self.fail_first = fail_first
    def wait_ready(self, timeout, interval):
        self.ready += 1
        if self.fail_first and self.ready == 1: raise DeployError("ready failed")
    def smoke(self): self.smokes += 1


class Preflight:
    def __init__(self, fail=False): self.fail = fail; self.calls = []
    def run(self, release):
        self.calls.append(release)
        if self.fail: raise DeployError("preflight failed")


def deployer_graph(tmp_path: Path, *, services=None, probe=None, preflight=None):
    pointer_layout, first, second, pointer = layout(tmp_path)
    root = pointer.parent.parent
    database = root / "data" / "asep.db"; SQLiteDatabase(database)
    workspace = root / "workspaces" / "org" / "project" / "workspace"
    workspace.mkdir(parents=True); (workspace / "state.txt").write_text("preserved", encoding="utf-8")
    config = DeployConfig(
        root / "releases", pointer, database, root / "workspaces", root / "backups",
        root / "temp" / "maintenance", root / "operations", readiness_timeout=.1,
        readiness_interval=.01, windows_mode=True,
    )
    instance = Deployer(config, services=services or Services(), probe=probe or Probe(),
                        preflight=preflight or Preflight())
    return instance, first, second, pointer


@pytest.mark.parametrize("release_id", ("../x", "C:\\absolute", "/absolute", "a/b", "..", "x" * 65))
def test_windows_pointer_rejects_invalid_release_ids(tmp_path, release_id):
    pointer_layout, *_ = layout(tmp_path)
    with pytest.raises(DeployError): pointer_layout.release(release_id)


def test_windows_pointer_activation_is_atomic_and_preserves_previous(tmp_path, monkeypatch):
    pointer_layout, first, second, pointer = layout(tmp_path)
    calls = []; real_replace = deploy_module.os.replace
    monkeypatch.setattr(deploy_module.os, "replace", lambda source, target: (calls.append((Path(source), Path(target))), real_replace(source, target))[1])
    pointer_layout.activate(second)
    assert calls[-1][1] == pointer
    assert json.loads(pointer.read_text(encoding="utf-8")) == {"release_id": "release-B"}
    assert first.is_dir() and second.is_dir()


def test_interrupted_windows_activation_keeps_complete_previous_pointer(tmp_path, monkeypatch):
    pointer_layout, first, second, pointer = layout(tmp_path)
    monkeypatch.setattr(deploy_module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("interrupted")))
    with pytest.raises(OSError): pointer_layout.activate(second)
    assert json.loads(pointer.read_text(encoding="utf-8")) == {"release_id": first.name}
    assert not tuple(pointer.parent.glob(".*.tmp"))


@pytest.mark.parametrize("payload", ('{"release_id":null}', '{"release_id":"release-A","extra":1}', '{partial'))
def test_windows_active_pointer_rejects_malformed_or_partial_json(tmp_path, payload):
    pointer_layout, _, _, pointer = layout(tmp_path)
    pointer.write_text(payload, encoding="utf-8")
    with pytest.raises(DeployError, match="pointer|Release id"):
        pointer_layout.active()


def test_windows_deploy_success_and_manual_rollback_preserve_data(tmp_path):
    instance, first, second, pointer = deployer_graph(tmp_path)
    audit = instance.deploy(second.name)
    assert json.loads(pointer.read_text())["release_id"] == second.name
    assert instance.config.database.is_file() and (instance.config.hosted_root / "org/project/workspace/state.txt").is_file()
    assert json.loads(audit.read_text())["backup_id"]
    instance.rollback(first.name)
    assert json.loads(pointer.read_text())["release_id"] == first.name
    assert second.is_dir() and tuple(instance.config.backup_root.iterdir())


def test_failure_before_activation_does_not_restart_or_change_pointer(tmp_path):
    services = Services(); instance, first, second, pointer = deployer_graph(tmp_path, services=services, preflight=Preflight(True))
    with pytest.raises(DeployError, match="preflight"): instance.deploy(second.name)
    assert json.loads(pointer.read_text())["release_id"] == first.name
    assert services.calls == 0 and not instance.gate.marker.exists()


def test_post_activation_failure_rolls_back_and_records_bounded_audit(tmp_path):
    probe = Probe(fail_first=True); instance, first, second, pointer = deployer_graph(tmp_path, probe=probe)
    with pytest.raises(DeployError, match="ready"): instance.deploy(second.name)
    assert json.loads(pointer.read_text())["release_id"] == first.name
    audit = json.loads(next((instance.config.operations_root / "deploys").glob("*.json")).read_text())
    assert audit["rollback_performed"] is True and audit["outcome"] == "rolled_back"
    assert not instance.gate.marker.exists()


def test_rollback_failure_keeps_maintenance_fail_closed(tmp_path):
    services = Services(fail_calls={1, 2}); instance, _, second, pointer = deployer_graph(tmp_path, services=services)
    with pytest.raises(DeployError, match="maintenance remains active"): instance.deploy(second.name)
    assert instance.gate.marker.exists()
    audit_text = next((instance.config.operations_root / "deploys").glob("*.json")).read_text().casefold()
    assert '"outcome": "unsafe"' in audit_text
    assert all(secret not in audit_text for secret in ("password", "cookie", "api_key", "token"))


def test_windows_deploy_source_contains_no_install_build_or_shell_true():
    source = Path(deploy_module.__file__).read_text(encoding="utf-8").casefold()
    assert all(item not in source for item in ("pip install", "npm install", "npm ci", "next build", "shell=true"))
    launcher = Path("deployment/windows/asep-deploy.ps1").read_text(encoding="utf-8")
    assert "ValidateSet('plan','deploy','rollback')" in launcher
    assert "--windows" in launcher and "active-release.json" in launcher
    assert "Invoke-Expression" not in launcher and "0.0.0.0" not in launcher
