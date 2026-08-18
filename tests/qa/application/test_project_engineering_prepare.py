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
from asep.project_analysis import ProjectAnalyzer
from asep.projects import (
    InMemoryProjectExecutionRepository,
    InMemoryProjectRepository,
    InMemoryProjectSessionRepository,
    ProjectEngineeringStepResult,
    WorkspaceProject,
)


class Runtime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="model")

    def __init__(self):
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        return AIRuntimeResult(output="runtime", identity=self.identity)


class Executor:
    def __init__(self):
        self.calls = 0
        self.plan = None

    def execute_supported_plan(self, execution, plan, workspace, analysis):
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
    (tmp_path / "app.py").write_text("print('ok')", encoding="utf-8")

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

    return service, request, executions, runtime, executor


def test_prepare_is_persisted_without_mutation_or_implementation(tmp_path: Path):
    service, request, executions, runtime, executor = make_service(tmp_path)

    before = (tmp_path / "app.py").read_bytes()

    prepared = service.prepare(request)

    assert (tmp_path / "app.py").read_bytes() == before
    assert runtime.calls == executor.calls == 0
    assert prepared.status.value == "pending"
    assert prepared.operational_plan is not None
    assert prepared.preparation_analysis["languages"] == ["Python"]
    assert executions.get("e-prepare") == prepared


def test_approval_executes_same_plan_and_execution_identity(tmp_path: Path):
    service, request, _, runtime, executor = make_service(tmp_path)

    prepared = service.prepare(request)
    result = service.execute_prepared(prepared.execution_id, request)

    assert result.execution.execution_id == prepared.execution_id
    assert result.execution.operational_plan == prepared.operational_plan
    assert executor.plan == prepared.operational_plan
    assert executor.calls == 1
    assert runtime.calls == 0


def test_mismatch_and_stale_preparation_fail_before_mutation(tmp_path: Path):
    service, request, _, runtime, executor = make_service(tmp_path)

    prepared = service.prepare(request)

    mismatch = request.model_copy(update={"session_id": "other"})

    with pytest.raises(ValueError, match="identity"):
        service.execute_prepared(prepared.execution_id, mismatch)

    assert executor.calls == runtime.calls == 0

    (tmp_path / "app.py").write_text("changed externally", encoding="utf-8")

    with pytest.raises(ValueError, match="stale"):
        service.execute_prepared(prepared.execution_id, request)

    assert executor.calls == runtime.calls == 0


def test_greenfield_dependency_plan_blocker_is_persisted_without_runtime(
    tmp_path: Path,
):
    service, request, executions, runtime, executor = make_service(tmp_path)

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
    service, request, _, runtime, executor = make_service(tmp_path)

    (tmp_path / ".asep").mkdir()

    (tmp_path / ".asep" / "dependency-baseline.json").write_text(
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
    assert runtime.calls == executor.calls == 0


def test_preparation_cannot_be_reused(tmp_path: Path):
    service, request, _, _, _ = make_service(tmp_path)

    prepared = service.prepare(request)
    service.execute_prepared(prepared.execution_id, request)

    with pytest.raises(ValueError, match="not available"):
        service.execute_prepared(prepared.execution_id, request)