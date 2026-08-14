from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3

import pytest

from asep.maintenance import MaintenanceGate
from asep.sqlite import SQLiteDatabase
from deployment import deploy as deploy_module
from deployment.deploy import DeployConfig, DeployError, Deployer, ReleaseLayout, UnsafeRollbackError


def prepared_release(root: Path, release_id: str, schema: str = "4") -> Path:
    release = root / release_id
    (release / ".venv" / "bin").mkdir(parents=True)
    (release / ".venv" / "bin" / "python").write_text("prepared", encoding="utf-8")
    (release / "frontend" / ".next").mkdir(parents=True)
    (release / "frontend" / ".next" / "BUILD_ID").write_text("build", encoding="utf-8")
    (release / "deployment").mkdir()
    (release / "deployment" / "preflight.py").write_text("prepared", encoding="utf-8")
    (release / "deployment" / "release.json").write_text(json.dumps({
        "format_version": 1, "app_version": "0.1.0",
        "expected_sqlite_schema": schema, "minimum_sqlite_schema": schema,
    }), encoding="utf-8")
    return release.resolve()


def persistence(tmp_path: Path):
    database = tmp_path / "data" / "asep.db"; SQLiteDatabase(database)
    hosted = tmp_path / "hosted"; (hosted / "org" / "project" / "workspace").mkdir(parents=True)
    (hosted / "org" / "project" / "workspace" / "file.txt").write_text("state", encoding="utf-8")
    return database, hosted


class FakeLayout:
    def __init__(self, releases: Path, active: Path): self.validator=ReleaseLayout(releases, releases.parent/"current"); self.current=active; self.activations=[]
    def release(self, release_id): return self.validator.release(release_id)
    def active(self): return self.current
    def activate(self, release): self.activations.append(release); self.current=release


class FakeServices:
    def __init__(self, failure=None): self.calls=0; self.failure=failure
    def restart(self):
        self.calls += 1
        if self.failure is not None and self.calls == 1: self.failure()


class FakeProbe:
    def __init__(self, fail_ready=False, fail_smoke=False): self.ready_calls=0; self.smoke_calls=0; self.fail_ready=fail_ready; self.fail_smoke=fail_smoke
    def wait_ready(self, timeout, interval):
        self.ready_calls += 1
        if self.fail_ready and self.ready_calls == 1: raise DeployError("Internal readiness timed out.")
    def smoke(self):
        self.smoke_calls += 1
        if self.fail_smoke and self.smoke_calls == 1: raise DeployError("Local smoke check failed.")


class FakePreflight:
    def __init__(self, fail=False): self.calls=[]; self.fail=fail
    def run(self, release):
        self.calls.append(release)
        if self.fail: raise DeployError("Candidate production preflight failed.")


def graph(tmp_path: Path, *, services=None, probe=None, preflight=None):
    releases = tmp_path / "opt" / "releases"; releases.mkdir(parents=True)
    previous = prepared_release(releases, "release-1")
    candidate = prepared_release(releases, "release-2")
    database, hosted = persistence(tmp_path)
    config = DeployConfig(
        releases, tmp_path/"opt"/"current", database, hosted,
        (tmp_path/"backups").resolve(), tmp_path/"maintenance", tmp_path/"operations",
        readiness_timeout=.1, readiness_interval=.01,
    )
    deployer = Deployer(config, services=services or FakeServices(), probe=probe or FakeProbe(), preflight=preflight or FakePreflight())
    layout = FakeLayout(releases.resolve(), previous); deployer.layout = layout
    return deployer, layout, previous, candidate


def test_successful_deploy_backs_up_activates_validates_and_releases_maintenance(tmp_path):
    deployer, layout, previous, candidate = graph(tmp_path)
    audit = deployer.deploy("release-2")
    assert layout.current == candidate and previous.is_dir()
    value = json.loads(audit.read_text(encoding="utf-8"))
    assert value["outcome"] == "succeeded" and value["backup_id"]
    assert not deployer.gate.marker.exists()
    assert tuple(deployer.config.backup_root.iterdir())


@pytest.mark.parametrize("release_id", ["../escape", "/absolute", "a/b", "..", "x"*65])
def test_invalid_release_and_traversal_are_rejected(tmp_path, release_id):
    deployer, *_ = graph(tmp_path)
    with pytest.raises(DeployError): deployer.plan(release_id)


def test_concurrent_or_abandoned_deploy_lock_is_fail_closed(tmp_path):
    deployer, *_ = graph(tmp_path)
    deployer.lock.acquire()
    try:
        with pytest.raises(DeployError, match="lock"): Deployer(deployer.config, services=FakeServices(), probe=FakeProbe(), preflight=FakePreflight()).deploy("release-2")
    finally: deployer.lock.release()


def test_preflight_failure_is_before_maintenance_activation_and_restart(tmp_path):
    services=FakeServices(); deployer, layout, previous, _ = graph(tmp_path, services=services, preflight=FakePreflight(True))
    with pytest.raises(DeployError, match="preflight"): deployer.deploy("release-2")
    assert layout.current == previous and services.calls == 0 and not deployer.gate.marker.exists()


def test_backup_failure_is_before_activation_and_releases_maintenance(tmp_path, monkeypatch):
    deployer, layout, previous, _ = graph(tmp_path)
    monkeypatch.setattr(deploy_module, "create_backup", lambda *args, **kwargs: (_ for _ in ()).throw(deploy_module.BackupError("backup failed")))
    with pytest.raises(deploy_module.BackupError): deployer.deploy("release-2")
    assert layout.current == previous and not deployer.gate.marker.exists()


def test_filesystem_activation_uses_atomic_replace(tmp_path, monkeypatch):
    releases=tmp_path/"releases"; releases.mkdir(); candidate=prepared_release(releases,"r1")
    current=tmp_path/"current"; current.write_text("old",encoding="utf-8")
    calls=[]; real_replace=deploy_module.os.replace
    monkeypatch.setattr(deploy_module.os,"symlink",lambda target,link,target_is_directory: Path(link).write_text(str(target),encoding="utf-8"))
    monkeypatch.setattr(deploy_module.os,"replace",lambda source,target:(calls.append((Path(source),Path(target))),real_replace(source,target))[1])
    ReleaseLayout(releases,current).activate(candidate)
    assert calls and calls[-1][1] == current
    assert current.read_text(encoding="utf-8") == str(candidate)


@pytest.mark.parametrize("failure", ["restart", "readiness", "smoke"])
def test_post_activation_failure_rolls_back_to_previous(tmp_path, failure):
    services=FakeServices(failure=(lambda: (_ for _ in ()).throw(DeployError("restart failed"))) if failure=="restart" else None)
    probe=FakeProbe(fail_ready=failure=="readiness",fail_smoke=failure=="smoke")
    deployer, layout, previous, candidate = graph(tmp_path, services=services, probe=probe)
    with pytest.raises(DeployError): deployer.deploy("release-2")
    assert layout.activations[:2] == [candidate, previous]
    assert layout.current == previous and not deployer.gate.marker.exists()


def test_manual_rollback_validates_and_reopens(tmp_path):
    deployer, layout, previous, candidate = graph(tmp_path); layout.current=candidate
    audit=deployer.rollback("release-1")
    assert layout.current == previous and not deployer.gate.marker.exists()
    assert json.loads(audit.read_text(encoding="utf-8"))["outcome"] == "succeeded"


def test_schema_change_makes_automatic_rollback_unsafe_and_keeps_maintenance(tmp_path):
    deployer, layout, previous, candidate = graph(tmp_path)
    def migrate_then_fail():
        with closing(sqlite3.connect(deployer.config.database)) as connection:
            connection.execute("UPDATE schema_metadata SET value='5' WHERE key='schema_version'"); connection.commit()
        raise DeployError("restart failed")
    deployer.services=FakeServices(migrate_then_fail)
    with pytest.raises(DeployError, match="maintenance remains active"):
        deployer.deploy("release-2")
    assert layout.current == candidate
    assert deployer.gate.marker.exists()


def test_dry_run_is_read_only_and_reports_unexecuted_runtime_checks(tmp_path):
    deployer, layout, previous, _ = graph(tmp_path)
    before=set(tmp_path.rglob("*")); result=deployer.plan("release-2"); after=set(tmp_path.rglob("*"))
    assert before == after and layout.current == previous
    assert result["runtime_checks_executed"] is False
    assert not deployer.gate.marker.exists() and not deployer.config.backup_root.exists()


def test_activation_contains_no_package_install_or_build_commands():
    source=Path(deploy_module.__file__).read_text(encoding="utf-8").casefold()
    for forbidden in ("pip install", "npm install", "npm ci", "next build"):
        assert forbidden not in source


def test_audit_metadata_is_bounded_and_contains_no_secrets(tmp_path):
    deployer, *_ = graph(tmp_path); audit=deployer.deploy("release-2")
    text=audit.read_text(encoding="utf-8").casefold()
    assert len(text) < 4096
    for forbidden in ("password", "api_key", "cookie", "token"):
        assert forbidden not in text
