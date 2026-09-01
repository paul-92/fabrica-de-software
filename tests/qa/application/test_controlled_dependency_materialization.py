import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.dependency_provisioning import (
    DependencyPlan,
    DependencyPlanItem,
    DependencyProvisioningBlockedError,
    DependencyProvisioningStatus,
    ProjectDependencyProvisioningService,
    SQLiteProvisioningEvidenceRepository,
)


class Runner:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def run(self, command, *, working_directory, environment, timeout):
        self.calls.append((command, working_directory, environment, timeout))
        if not self.fail:
            root_manifest = json.loads(
                (working_directory / "package.json").read_text(encoding="utf-8")
            )
            dependencies = {}
            for field in ("dependencies", "devDependencies", "optionalDependencies"):
                dependencies.update(root_manifest.get(field, {}))
            if "--package-lock-only" in command:
                (working_directory / "package-lock.json").write_text(
                    json.dumps({"lockfileVersion": 3, "packages": {
                        "": {}, **{
                            f"node_modules/{package}": {"version": version}
                            for package, version in dependencies.items()
                        },
                    }}), encoding="utf-8"
                )
            if command[:2] == ("npm", "ci"):
                (working_directory / "node_modules").mkdir(exist_ok=True)
                for package, version in dependencies.items():
                    installed = working_directory / "node_modules" / package
                    installed.mkdir(parents=True, exist_ok=True)
                    (installed / "package.json").write_text(
                        json.dumps({"name": package, "version": version}),
                        encoding="utf-8",
                    )
        return type("Result", (), {"exit_code": 1 if self.fail else 0, "stderr": "failed"})()


def manifest(root: Path, dependencies=None, *, name="root", version="1.0.0"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(json.dumps({
        "name": name, "version": version,
        "workspaces": ["apps/*", "packages/*"] if name == "root" else None,
        "dependencies": dependencies or {},
    }), encoding="utf-8")


def plan(*items, project_id="p"):
    return DependencyPlan(
        project_id=project_id, preparation_id="e", created_at=datetime.now(UTC),
        items=tuple(DependencyPlanItem(
            package=item[0], requested_version=item[1], reason="approved",
            source="baseline", status=item[2],
            manifest_group=item[3] if len(item) > 3 else None,
        ) for item in items),
    )


def materialize(tmp_path, dependency_plan, runner=None, evidence=None, execution_id="e"):
    runner = runner or Runner()
    evidence = evidence or SQLiteProvisioningEvidenceRepository(tmp_path / "evidence.db")
    result = ProjectDependencyProvisioningService().materialize_approved(
        tmp_path, runner, dependency_plan=dependency_plan,
        execution_id=execution_id, project_id="p", evidence_repository=evidence,
    )
    return result, runner, evidence


def test_approved_dependency_plan_allows_deterministic_materialization(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    result, runner, _ = materialize(
        tmp_path, plan(("typescript", "5.9.3", "approved"))
    )
    assert result.status is DependencyProvisioningStatus.PROVISIONED
    assert [call[0] for call in runner.calls] == [
        ("npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", "--save-exact"),
        ("npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"),
    ]


def test_unapproved_package_is_blocked(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3", "evil": "1.0.0"})
    with pytest.raises(DependencyProvisioningBlockedError, match="dependency_not_approved"):
        materialize(tmp_path, plan(("typescript", "5.9.3", "approved")))


def test_approved_version_replaces_stale_manifest_version_before_install(tmp_path):
    manifest(tmp_path, {"bullmq": "7.10.0"})

    result, runner, _ = materialize(
        tmp_path, plan(("bullmq", "6.3.1", "approved"))
    )

    updated = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert updated["dependencies"]["bullmq"] == "6.3.1"
    assert result.status is DependencyProvisioningStatus.PROVISIONED
    assert runner.calls


def test_stale_versions_are_reconciled_across_monorepo_manifests(tmp_path):
    manifest(tmp_path, {"bullmq": "7.10.0"})
    manifest(
        tmp_path / "apps" / "worker",
        {"bullmq": "7.10.0"},
        name="@taskflow/worker",
    )

    materialize(tmp_path, plan(("bullmq", "6.3.1", "approved")))

    for path in (tmp_path / "package.json", tmp_path / "apps" / "worker" / "package.json"):
        updated = json.loads(path.read_text(encoding="utf-8"))
        assert updated["dependencies"]["bullmq"] == "6.3.1"


def test_approved_missing_dev_dependency_is_materialized_exactly(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})

    result, _, _ = materialize(tmp_path, plan(
        ("typescript", "5.9.3", "approved"),
        ("@types/node", "24.13.3", "approved", "devDependencies"),
    ))

    updated = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((tmp_path / "package-lock.json").read_text(encoding="utf-8"))
    installed = json.loads(
        (tmp_path / "node_modules" / "@types/node" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    assert updated["devDependencies"]["@types/node"] == "24.13.3"
    assert lock["packages"]["node_modules/@types/node"]["version"] == "24.13.3"
    assert installed["version"] == "24.13.3"
    assert result.status is DependencyProvisioningStatus.PROVISIONED


def test_missing_dependency_without_manifest_group_is_blocked(tmp_path):
    manifest(tmp_path)
    with pytest.raises(
        DependencyProvisioningBlockedError,
        match="dependency_manifest_target_required",
    ):
        materialize(tmp_path, plan(("@types/node", "24.13.3", "approved")))


@pytest.mark.parametrize("version", ["latest", "^24.13.3", "~24.13.3"])
def test_non_exact_approved_version_is_blocked(tmp_path, version):
    manifest(tmp_path, {"@types/node": version})
    with pytest.raises(
        DependencyProvisioningBlockedError,
        match="dependency_exact_version_required",
    ):
        materialize(tmp_path, plan(("@types/node", version, "approved")))


@pytest.mark.parametrize("missing", ["manifest", "lockfile", "installed"])
def test_success_is_blocked_when_materialization_evidence_is_missing(
    tmp_path, missing,
):
    class IncompleteRunner(Runner):
        def run(self, command, **kwargs):
            result = super().run(command, **kwargs)
            if command[:2] == ("npm", "ci"):
                root = kwargs["working_directory"]
                if missing == "manifest":
                    payload = json.loads(
                        (root / "package.json").read_text(encoding="utf-8")
                    )
                    del payload["dependencies"]["typescript"]
                    (root / "package.json").write_text(
                        json.dumps(payload), encoding="utf-8"
                    )
                elif missing == "lockfile":
                    lock = json.loads(
                        (root / "package-lock.json").read_text(encoding="utf-8")
                    )
                    del lock["packages"]["node_modules/typescript"]
                    (root / "package-lock.json").write_text(
                        json.dumps(lock), encoding="utf-8"
                    )
                else:
                    installed = root / "node_modules" / "typescript"
                    (installed / "package.json").unlink()
            return result

    manifest(tmp_path, {"typescript": "5.9.3"})
    evidence = SQLiteProvisioningEvidenceRepository(tmp_path / "evidence.db")
    with pytest.raises(
        DependencyProvisioningBlockedError,
        match="dependency_materialization_unverified",
    ):
        materialize(
            tmp_path, plan(("typescript", "5.9.3", "approved")),
            IncompleteRunner(), evidence,
        )
    assert evidence.for_execution("p", "e") == ()


def test_missing_or_unapproved_plan_blocks(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    with pytest.raises(DependencyProvisioningBlockedError, match="dependency_plan_missing"):
        materialize(tmp_path, plan())
    with pytest.raises(DependencyProvisioningBlockedError, match="dependency_approval_required"):
        materialize(tmp_path, plan(("typescript", "5.9.3", "pending")))


def test_success_evidence_is_persisted_with_safe_fingerprints(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    result, _, evidence = materialize(tmp_path, plan(("typescript", "5.9.3", "approved")))
    persisted = evidence.for_execution("p", "e")
    assert persisted == (result,)
    assert len(result.dependency_plan_fingerprint) == 64
    assert len(result.manifest_fingerprint) == 64
    assert result.materialized_roots == (".",)


def test_incompatible_evidence_forces_new_provisioning(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    _, _, evidence = materialize(tmp_path, plan(("typescript", "5.9.3", "approved")))
    manifest(tmp_path, {"typescript": "5.9.3", "react": "19.2.8"})
    runner = Runner()
    materialize(tmp_path, plan(("typescript", "5.9.3", "approved"), ("react", "19.2.8", "approved")), runner, evidence, "e2")
    assert runner.calls


def test_package_manager_failure_persists_failure_and_blocks(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    evidence = SQLiteProvisioningEvidenceRepository(tmp_path / "evidence.db")
    with pytest.raises(DependencyProvisioningBlockedError, match="dependency_provisioning_failed"):
        materialize(tmp_path, plan(("typescript", "5.9.3", "approved")), Runner(fail=True), evidence)
    assert evidence.for_execution("p", "e")[0].status is DependencyProvisioningStatus.FAILED


def test_compatible_materialization_is_reused_without_reinstall(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    dependency_plan = plan(("typescript", "5.9.3", "approved"))
    _, _, evidence = materialize(tmp_path, dependency_plan)
    runner = Runner()
    result, _, _ = materialize(tmp_path, dependency_plan, runner, evidence, "e2")
    assert result.reused is True
    assert runner.calls == []


def test_monorepo_internal_packages_are_deterministic_and_external_only_are_approved(tmp_path):
    manifest(tmp_path, {"typescript": "5.9.3"})
    manifest(tmp_path / "apps" / "api", {"@taskflow/config": "0.1.0", "typescript": "5.9.3"}, name="@taskflow/api")
    manifest(tmp_path / "packages" / "config", {}, name="@taskflow/config", version="0.1.0")
    result, runner, _ = materialize(tmp_path, plan(("typescript", "5.9.3", "approved")))
    assert result.materialized_roots == (".",)
    assert all(call[1] == tmp_path.resolve() for call in runner.calls)


def test_provisioning_precedes_validation_in_execution_boundary():
    source = Path("src/asep/application/project_engineering_execution.py").read_text(encoding="utf-8")
    complete = source[source.index("def _complete_execution"):source.index("def _verified_noop_evidence")]
    assert complete.index("provision_approved_dependencies") < complete.index("strategy_builder")
