import json

import pytest

from asep.dependency_provisioning import (
    DependencyProvisioningBlockedError,
    ProjectDependencyProvisioningService,
    DependencyProvisioningStatus,
    SQLiteDependencyRequestRepository, DependencyRequestDecision,
    SQLiteProvisioningEvidenceRepository, ProvisioningEvidence,
)
from asep.application.workspace_changes import WorkspaceSnapshotter


def _manifest(workspace, **overrides):
    payload = {"packageManager": "pnpm@9.15.0", "dependencies": {"typescript": "5.7.3"}}
    payload.update(overrides)
    (workspace / "package.json").write_text(json.dumps(payload), encoding="utf-8")


def test_node_caches_are_confined_offline_and_not_product_changes(tmp_path):
    _manifest(tmp_path)
    snapshotter = WorkspaceSnapshotter()
    before = snapshotter.capture(tmp_path)
    prepared = ProjectDependencyProvisioningService().prepare_node(tmp_path)
    assert prepared is not None
    root = (tmp_path / ".asep" / "runtime").resolve()
    for name in ("NPM_CONFIG_CACHE", "COREPACK_HOME", "PNPM_HOME", "PNPM_STORE_DIR"):
        assert prepared.environment[name].startswith(str(root))
    assert prepared.environment["NPM_CONFIG_OFFLINE"] == "true"
    assert prepared.evidence.cache_location == "runtime-managed"
    assert snapshotter.changes(before, snapshotter.capture(tmp_path)) == ()


def test_registry_allowlist_and_arbitrary_sources_are_enforced(tmp_path):
    _manifest(tmp_path)
    service = ProjectDependencyProvisioningService()
    with pytest.raises(DependencyProvisioningBlockedError, match="registry não aprovado"):
        service.prepare_node(tmp_path, registry="https://evil.example/")
    _manifest(tmp_path, dependencies={"bad": "https://evil.example/bad.tgz"})
    with pytest.raises(DependencyProvisioningBlockedError, match="fontes arbitrárias"):
        service.prepare_node(tmp_path)


def test_package_manager_requires_exact_supported_version(tmp_path):
    _manifest(tmp_path, packageManager="pnpm@latest")
    with pytest.raises(DependencyProvisioningBlockedError, match="versão exata"):
        ProjectDependencyProvisioningService().prepare_node(tmp_path)

def test_undeclared_dependency_requires_approval(tmp_path):
    _manifest(tmp_path)
    request=ProjectDependencyProvisioningService().request_undeclared(tmp_path,package="react",version="19.0.0",reason="UI")
    assert request.status is DependencyProvisioningStatus.APPROVAL_REQUIRED
    with pytest.raises(ValueError,match="already declared"):
        ProjectDependencyProvisioningService().request_undeclared(tmp_path,package="typescript",version="5.7.3",reason="build")

def test_controlled_broker_uses_deterministic_command_and_no_secrets(tmp_path):
    _manifest(tmp_path)
    class Runner:
        calls=[]
        def run(self,command,**kwargs):
            self.calls.append((command,kwargs))
            return type("Result",(),{"exit_code":0,"stderr":"","stdout":"token=secret"})()
    runner=Runner(); result=ProjectDependencyProvisioningService().provision_node(tmp_path,runner)
    assert runner.calls[0][0] == ("corepack","pnpm","fetch","--frozen-lockfile","--ignore-scripts")
    assert result.evidence.status is DependencyProvisioningStatus.PROVISIONED
    assert "secret" not in result.model_dump_json()
    assert "NPM_CONFIG_OFFLINE" not in runner.calls[0][1]["environment"]

def test_dependency_request_survives_restart_and_resolution(tmp_path):
    database=tmp_path/"requests.db"; repo=SQLiteDependencyRequestRepository(database)
    item=repo.create(project_id="p",session_id="s",execution_id="e",package="react",requested_version="19.0.0",reason="UI",registry="https://registry.npmjs.org/")
    restarted=SQLiteDependencyRequestRepository(database); assert restarted.get("p",item.request_id).status.value=="pending"
    approved=restarted.resolve("p",item.request_id,DependencyRequestDecision.APPROVED,"user",1)
    assert SQLiteDependencyRequestRepository(database).get("p",item.request_id).status is DependencyRequestDecision.APPROVED

def test_provisioning_evidence_success_and_failure_survive_restart(tmp_path):
    from datetime import UTC,datetime
    from uuid import uuid4
    database=tmp_path/"evidence.db"; repo=SQLiteProvisioningEvidenceRepository(database)
    for status in (DependencyProvisioningStatus.PROVISIONED,DependencyProvisioningStatus.REGISTRY_UNAVAILABLE):
        repo.save(ProvisioningEvidence(evidence_id=str(uuid4()),execution_id="e",project_id="p",package_manager="pnpm",registry="https://registry.npmjs.org/",status=status,created_at=datetime.now(UTC),completed_at=datetime.now(UTC),error_code=None if status is DependencyProvisioningStatus.PROVISIONED else status.value))
    found=SQLiteProvisioningEvidenceRepository(database).for_execution("p","e")
    assert {item.status for item in found}=={DependencyProvisioningStatus.PROVISIONED,DependencyProvisioningStatus.REGISTRY_UNAVAILABLE}
    assert all(item.execution_id=="e" for item in found)
