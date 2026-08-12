from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeRequest,
    AIRuntimeResult,
    InMemoryAIRuntimeRegistry,
)
from asep.application import (
    DeterministicProjectOperationalPlanBuilder,
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectEngineeringExecutionService,
    ProjectService,
    ProjectSessionMemoryService,
    ProjectSessionService,
)
from asep.errors import ProjectNotFoundError, ProjectSessionNotFoundError
from asep.projects import (
    InMemoryProjectExecutionRepository,
    InMemoryProjectRepository,
    InMemoryProjectSessionRepository,
    InMemorySessionMemoryRepository,
    SessionMemoryKind,
    ProjectOperationalPlan,
    WorkspaceProject,
)


class ObservingRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="fake-codex")

    def __init__(
        self,
        workspace: Path,
        executions: InMemoryProjectExecutionRepository,
        *,
        failure: Exception | None = None,
    ) -> None:
        self.workspace = workspace
        self.executions = executions
        self.failure = failure
        self.requests: list[AIRuntimeRequest] = []
        self.execution_seen_before_mutation = None

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        current = self.executions.list_by_project("project-1")
        assert len(current) == 1
        self.execution_seen_before_mutation = current[0]
        assert current[0].operational_plan is not None
        assert not (self.workspace / "app.py").exists()
        (self.workspace / "app.py").write_text(
            "HEALTH = {'status': 'ok'}\n", encoding="utf-8"
        )
        (self.workspace / "test_app.py").write_text(
            "def test_health(): assert True\n", encoding="utf-8"
        )
        if self.failure is not None:
            raise self.failure
        return AIRuntimeResult(output="health endpoint added", identity=self.identity)


def graph(tmp_path: Path, *, failure: Exception | None = None):
    projects = InMemoryProjectRepository()
    projects.save(WorkspaceProject(
        project_id="project-1",
        name="Fixture",
        workspace_path=tmp_path,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))
    executions = InMemoryProjectExecutionRepository()
    project_service = ProjectService(projects)
    sessions_repository = InMemoryProjectSessionRepository()
    sessions = ProjectSessionService(
        project_service,
        sessions_repository,
        executions,
        id_generator=lambda: "session-1",
    )
    sessions.create("project-1", "Health task")
    memory_identifiers = iter(("memory-1", "memory-2", "memory-3"))
    memory = ProjectSessionMemoryService(
        project_service,
        sessions,
        InMemorySessionMemoryRepository(),
        id_generator=lambda: next(memory_identifiers),
    )
    memory.add("project-1", "session-1", SessionMemoryKind.FACT, "Uses FastAPI")
    runtime = ObservingRuntime(tmp_path, executions, failure=failure)
    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)
    runtime_execution = ProjectAIRuntimeExecutionService(
        project_service,
        registry,
        sessions,
        executions,
        memory_service=memory,
        operational_plan_builder=DeterministicProjectOperationalPlanBuilder(),
        id_generator=lambda: "execution-1",
    )
    return (
        ProjectEngineeringExecutionService(runtime_execution),
        runtime,
        executions,
        memory,
    )


def request(**changes) -> ProjectAIRuntimeExecutionRequest:
    values = {
        "project_id": "project-1",
        "session_id": "session-1",
        "runtime_id": "codex",
        "instruction": (
            "Add GET /health returning {'status': 'ok'} and create a test."
        ),
        "execution_mode": AIRuntimeExecutionMode.WORKSPACE_WRITE,
    }
    values.update(changes)
    return ProjectAIRuntimeExecutionRequest(**values)


def test_proof_task_plan_runtime_mutation_diff_and_single_execution(
    tmp_path: Path,
) -> None:
    service, runtime, executions, memory = graph(tmp_path)

    result = service.execute(request())

    assert result.execution.execution_id == "execution-1"
    assert result.execution.operational_plan is not None
    assert result.execution.operational_plan.execution_id == "execution-1"
    assert [step.operation.value for step in result.execution.operational_plan.steps] == [
        "analyze_context",
        "execute_workspace_task",
        "capture_workspace_changes",
    ]
    assert len(executions.list_by_project("project-1")) == 1
    assert runtime.execution_seen_before_mutation.execution_id == "execution-1"
    assert runtime.requests[0].execution_mode is AIRuntimeExecutionMode.WORKSPACE_WRITE
    assert runtime.requests[0].context["project_session"]["session_id"] == "session-1"
    assert runtime.requests[0].context["session_memory"]["entries"][0]["content"] == "Uses FastAPI"
    assert {change.path for change in result.changes} == {"app.py", "test_app.py"}
    assert all(
        item.source_execution_id == "execution-1"
        for item in memory.list("project-1", "session-1")
        if item.kind is SessionMemoryKind.ARTIFACT
    )


def test_project_and_session_are_validated_before_runtime(tmp_path: Path) -> None:
    service, runtime, executions, _ = graph(tmp_path)

    with pytest.raises(ProjectNotFoundError):
        service.execute(request(project_id="missing"))
    with pytest.raises(ProjectSessionNotFoundError):
        service.execute(request(session_id="missing"))

    assert runtime.requests == []
    assert executions.list_by_project("project-1") == ()


def test_read_only_mode_cannot_start_engineering_execution(tmp_path: Path) -> None:
    service, runtime, executions, _ = graph(tmp_path)

    with pytest.raises(ValueError, match="workspace_write"):
        service.execute(request(execution_mode=AIRuntimeExecutionMode.READ_ONLY))

    assert runtime.requests == []
    assert executions.list_by_project("project-1") == ()


def test_runtime_failure_keeps_one_failed_execution_and_change_evidence(
    tmp_path: Path,
) -> None:
    failure = RuntimeError("runtime failed")
    service, _, executions, _ = graph(tmp_path, failure=failure)

    with pytest.raises(RuntimeError) as caught:
        service.execute(request())

    assert caught.value is failure
    persisted = executions.get("execution-1")
    assert persisted.status.value == "failed"
    assert persisted.error_code == "RUNTIME_ERROR"
    assert persisted.operational_plan.execution_id == persisted.execution_id
    assert {change.path for change in persisted.changes} == {"app.py", "test_app.py"}
    assert len(executions.list_by_project("project-1")) == 1


def test_operational_plan_is_strict_frozen_and_owned_by_execution(
    tmp_path: Path,
) -> None:
    service, _, _, _ = graph(tmp_path)
    plan = service.execute(request()).execution.operational_plan
    assert plan is not None
    with pytest.raises((FrozenInstanceError, TypeError, ValueError)):
        plan.execution_id = "other"  # type: ignore[misc]
    with pytest.raises(ValueError):
        ProjectOperationalPlan.model_validate({
            **plan.model_dump(mode="python"),
            "unsupported": True,
        })
