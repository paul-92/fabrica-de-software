from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeResult,
    InMemoryAIRuntimeRegistry,
)
from asep.application import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectService,
    ProjectSessionService,
)
from asep.application.project_ai_runtime import EngineeringPhase
from asep.application.project_engineering_planning import (
    DeterministicEngineeringTaskDecomposer,
    ProjectEngineeringPlanningService,
)
from asep.dependency_provisioning import (
    DependencyRequestDecision,
    SQLiteDependencyRequestRepository,
)
from asep.project_analysis import ProjectAnalyzer
from asep.projects import (
    InMemoryProjectExecutionRepository,
    InMemoryProjectRepository,
    InMemoryProjectSessionRepository,
    ProjectEngineeringStepResult,
    WorkspaceProject,
)


class Runtime:
    identity = AIRuntimeIdentity(
        runtime_id="codex",
        model_id="model",
    )

    def __init__(self):
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        return AIRuntimeResult(
            output="runtime",
            identity=self.identity,
        )


class Executor:
    def __init__(self):
        self.calls = 0
        self.plan = None

    def execute_supported_plan(
        self,
        execution,
        plan,
        workspace,
        analysis,
    ):
        self.calls += 1
        self.plan = plan
        now = datetime.now(UTC)

        return tuple(
            ProjectEngineeringStepResult(
                execution_id=execution.execution_id,
                step_id=step.step_id,
                executor="developer_agent",
                tool_id="controlled",
                succeeded=True,
                output="done",
                started_at=now,
                completed_at=now,
            )
            for step in plan.steps
        )


def make_service(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "print('ok')",
        encoding="utf-8",
    )

    projects = InMemoryProjectRepository()

    projects.save(
        WorkspaceProject(
            project_id="p-1",
            name="Project",
            workspace_path=tmp_path,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )

    executions = InMemoryProjectExecutionRepository()
    project_service = ProjectService(projects)

    sessions = ProjectSessionService(
        project_service,
        InMemoryProjectSessionRepository(),
        executions,
        id_generator=lambda: "s-1",
    )

    sessions.create("p-1", "Work")

    runtime = Runtime()

    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)

    executor = Executor()

    dependency_requests = SQLiteDependencyRequestRepository(
        tmp_path / "dependency-requests.db"
    )

    service = ProjectAIRuntimeExecutionService(
        project_service,
        registry,
        sessions,
        executions,
        engineering_planning=ProjectEngineeringPlanningService(
            ProjectAnalyzer(),
            DeterministicEngineeringTaskDecomposer(),
        ),
        internal_execution=executor,
        dependency_requests=dependency_requests,
        defer_completion=True,
        id_generator=lambda: "e-prepare",
    )

    request = ProjectAIRuntimeExecutionRequest(
        project_id="p-1",
        session_id="s-1",
        runtime_id="codex",
        instruction="Add endpoint",
        execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
    )

    return (
        service,
        request,
        executions,
        runtime,
        executor,
        dependency_requests,
    )


def test_prepare_is_persisted_without_mutation_or_implementation(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        _,
    ) = make_service(tmp_path)

    before = (tmp_path / "app.py").read_bytes()

    prepared = service.prepare(request)

    assert (tmp_path / "app.py").read_bytes() == before
    assert runtime.calls == executor.calls == 0
    assert prepared.status.value == "pending"
    assert prepared.operational_plan is not None
    assert prepared.preparation_analysis["languages"] == ["Python"]
    assert executions.get("e-prepare") == prepared


def test_approval_executes_same_plan_and_execution_identity(
    tmp_path: Path,
):
    (
        service,
        request,
        _,
        runtime,
        executor,
        _,
    ) = make_service(tmp_path)

    prepared = service.prepare(request)

    result = service.execute_prepared(
        prepared.execution_id,
        request,
    )

    assert result.execution.execution_id == prepared.execution_id
    assert (
        result.execution.operational_plan
        == prepared.operational_plan
    )
    assert executor.plan == prepared.operational_plan
    assert executor.calls == 1
    assert runtime.calls == 0


def test_mismatch_and_stale_preparation_fail_before_mutation(
    tmp_path: Path,
):
    (
        service,
        request,
        _,
        runtime,
        executor,
        _,
    ) = make_service(tmp_path)

    prepared = service.prepare(request)

    mismatch = request.model_copy(
        update={
            "session_id": "other",
        }
    )

    with pytest.raises(
        ValueError,
        match="identity",
    ):
        service.execute_prepared(
            prepared.execution_id,
            mismatch,
        )

    assert executor.calls == runtime.calls == 0

    (tmp_path / "app.py").write_text(
        "changed externally",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="stale",
    ):
        service.execute_prepared(
            prepared.execution_id,
            request,
        )

    assert executor.calls == runtime.calls == 0


def test_greenfield_dependency_plan_blocker_is_persisted_without_runtime(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        _,
    ) = make_service(tmp_path)

    (tmp_path / "app.py").unlink()

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
            "sprint_id": "1",
            "sprint_name": "Foundation",
        }
    )

    prepared = service.prepare(request)

    assert prepared.status.value == "blocked"
    assert prepared.error_code == "dependency_plan_missing_source"
    assert (
        prepared.next_action
        == "Defina ou aprove a stack técnica na preparação da sprint."
    )
    assert prepared.dependency_plan["items"] == []
    assert executions.get(prepared.execution_id) == prepared
    assert runtime.calls == executor.calls == 0


def test_version_selection_required_is_a_structured_prepare_blocker(
    tmp_path: Path,
):
    (
        service,
        request,
        _,
        runtime,
        executor,
        _,
    ) = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (
        tmp_path
        / ".asep"
        / "dependency-baseline.json"
    ).write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
        }
    )

    prepared = service.prepare(request)

    assert prepared.status.value == "blocked"
    assert prepared.error_code == "version_selection_required"

    item = prepared.dependency_plan["items"][0]

    assert item["package"] == "typescript"
    assert item["requested_version"] is None
    assert item["status"] == "version_selection_required"
    assert item["dependency_request_id"] is None

    assert runtime.calls == executor.calls == 0


def test_select_dependency_version_transitions_to_pending(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        dependency_requests,
    ) = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (
        tmp_path
        / ".asep"
        / "dependency-baseline.json"
    ).write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
            "sprint_id": "1",
            "sprint_name": "Foundation",
        }
    )

    before = (tmp_path / "app.py").read_bytes()

    prepared = service.prepare(request)

    assert prepared.error_code == "version_selection_required"

    updated = service.select_dependency_version(
        project_id="p-1",
        preparation_id=prepared.execution_id,
        package="typescript",
        version="5.9.2",
    )

    assert updated.status.value == "blocked"
    assert updated.error_code == "dependency_approval_required"
    assert (
        updated.next_action
        == "Revise e aprove as dependências necessárias."
    )

    assert len(updated.dependency_plan["items"]) == 1

    item = updated.dependency_plan["items"][0]

    assert item["package"] == "typescript"
    assert item["requested_version"] == "5.9.2"
    assert item["status"] == "pending"
    assert item["dependency_request_id"]

    assert len(updated.dependency_requests) == 1

    request_item = updated.dependency_requests[0]

    assert request_item["package"] == "typescript"
    assert request_item["requested_version"] == "5.9.2"
    assert request_item["reason"] == "compiler"
    assert request_item["ecosystem"] == "node"

    stored = dependency_requests.list("p-1")

    assert len(stored) == 1
    assert stored[0].request_id == item["dependency_request_id"]
    assert stored[0].execution_id == prepared.execution_id
    assert stored[0].package == "typescript"
    assert stored[0].requested_version == "5.9.2"
    assert stored[0].status.value == "pending"

    persisted = executions.get(prepared.execution_id)

    assert persisted == updated

    assert (tmp_path / "app.py").read_bytes() == before

    assert runtime.calls == 0
    assert executor.calls == 0



def test_select_dependency_version_creates_new_pending_after_rejected_same_version(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        dependency_requests,
    ) = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (
        tmp_path
        / ".asep"
        / "dependency-baseline.json"
    ).write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    rejected = dependency_requests.create(
        project_id="p-1",
        session_id="old-session",
        execution_id="old-prep",
        package="typescript",
        requested_version="5.9.2",
        reason="compiler",
        registry="https://registry.npmjs.org/",
    )

    rejected = dependency_requests.resolve(
        "p-1",
        rejected.request_id,
        DependencyRequestDecision.REJECTED,
        "approver",
        1,
    )

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
            "sprint_id": "1",
            "sprint_name": "Foundation",
        }
    )

    prepared = service.prepare(request)

    assert prepared.error_code == "version_selection_required"

    updated = service.select_dependency_version(
        project_id="p-1",
        preparation_id=prepared.execution_id,
        package="typescript",
        version="5.9.2",
    )

    item = updated.dependency_plan["items"][0]

    assert item["requested_version"] == "5.9.2"
    assert item["status"] == "pending"
    assert item["dependency_request_id"] != rejected.request_id

    history = [
        stored
        for stored in dependency_requests.list("p-1")
        if stored.package == "typescript"
        and stored.requested_version == "5.9.2"
    ]

    assert len(history) == 2

    by_id = {
        stored.request_id: stored
        for stored in history
    }

    assert (
        by_id[rejected.request_id].status
        is DependencyRequestDecision.REJECTED
    )

    new_request = by_id[item["dependency_request_id"]]

    assert (
        new_request.status
        is DependencyRequestDecision.PENDING
    )

    assert (
        new_request.execution_id
        == prepared.execution_id
    )

    assert runtime.calls == 0
    assert executor.calls == 0


def test_select_dependency_version_rejects_invalid_version(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        dependency_requests,
    ) = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (
        tmp_path
        / ".asep"
        / "dependency-baseline.json"
    ).write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
        }
    )

    prepared = service.prepare(request)

    with pytest.raises(
        ValueError,
        match="invalid node version",
    ):
        service.select_dependency_version(
            project_id="p-1",
            preparation_id=prepared.execution_id,
            package="typescript",
            version="latest",
        )

    persisted = executions.get(prepared.execution_id)

    assert persisted == prepared
    assert dependency_requests.list("p-1") == ()
    assert runtime.calls == executor.calls == 0


def test_select_dependency_version_rejects_unknown_package(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        dependency_requests,
    ) = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (
        tmp_path
        / ".asep"
        / "dependency-baseline.json"
    ).write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
        }
    )

    prepared = service.prepare(request)

    with pytest.raises(
        ValueError,
        match="not found or ambiguous",
    ):
        service.select_dependency_version(
            project_id="p-1",
            preparation_id=prepared.execution_id,
            package="react",
            version="19.1.1",
        )

    assert executions.get(prepared.execution_id) == prepared
    assert dependency_requests.list("p-1") == ()
    assert runtime.calls == executor.calls == 0


def test_select_dependency_version_cannot_be_selected_twice(
    tmp_path: Path,
):
    (
        service,
        request,
        executions,
        runtime,
        executor,
        dependency_requests,
    ) = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (
        tmp_path
        / ".asep"
        / "dependency-baseline.json"
    ).write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    request = request.model_copy(
        update={
            "engineering_phase": EngineeringPhase.DEVELOPMENT,
        }
    )

    prepared = service.prepare(request)

    first = service.select_dependency_version(
        project_id="p-1",
        preparation_id=prepared.execution_id,
        package="typescript",
        version="5.9.2",
    )

    with pytest.raises(
        ValueError,
        match="already been selected",
    ):
        service.select_dependency_version(
            project_id="p-1",
            preparation_id=prepared.execution_id,
            package="typescript",
            version="5.9.2",
        )

    assert executions.get(prepared.execution_id) == first
    assert len(dependency_requests.list("p-1")) == 1
    assert runtime.calls == executor.calls == 0


def test_newer_approved_decision_overrides_workspace_analysis_version(tmp_path: Path):
    service, request, _, runtime, executor, dependency_requests = make_service(tmp_path)
    (tmp_path / ".asep").mkdir()
    (tmp_path / ".asep" / "dependency-baseline.json").write_text(
        '{"status":"approved","dependencies":['
        '{"package":"bullmq","requested_version":null,"reason":"queues"}'
        "]}",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"name":"sample","version":"0.1.0",'
        '"dependencies":{"bullmq":"7.10.0"}}',
        encoding="utf-8",
    )
    decision = dependency_requests.create(
        project_id="p-1",
        session_id=request.session_id,
        execution_id="human-decision",
        package="bullmq",
        requested_version="6.3.1",
        reason="approved replacement for nonexistent version",
        registry="https://registry.npmjs.org/",
    )
    approved = dependency_requests.resolve(
        "p-1",
        decision.request_id,
        DependencyRequestDecision.APPROVED,
        "authorized-human",
        decision.version,
    )
    prepared = service.prepare(
        request.model_copy(
            update={"engineering_phase": EngineeringPhase.DEVELOPMENT}
        )
    )
    items = [
        item for item in prepared.dependency_plan["items"]
        if item["package"] == "bullmq"
    ]
    assert items
    assert {item["requested_version"] for item in items} == {"6.3.1"}
    assert {item["status"] for item in items} == {"approved"}
    assert {item["dependency_request_id"] for item in items} == {
        approved.request_id
    }
    assert runtime.calls == executor.calls == 0


def test_preparation_cannot_be_reused(tmp_path: Path):
    (
        service,
        request,
        _,
        _,
        _,
        _,
    ) = make_service(tmp_path)

    prepared = service.prepare(request)

    service.execute_prepared(
        prepared.execution_id,
        request,
    )

    with pytest.raises(
        ValueError,
        match="not available",
    ):
        service.execute_prepared(
            prepared.execution_id,
            request,
        )
