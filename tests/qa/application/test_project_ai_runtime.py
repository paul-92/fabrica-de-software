from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeNotFoundError,
    AIRuntimeRequest,
    AIRuntimeResult,
    InMemoryAIRuntimeRegistry,
)
from asep.application import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectService,
    ProjectSessionService,
    SessionContextBuilder,
    SessionContextPolicy,
)
from asep.errors import ProjectNotFoundError
from asep.projects import (
    InMemoryProjectExecutionRepository,
    InMemoryProjectRepository,
    InMemoryProjectSessionRepository,
    WorkspaceProject,
)


class Runtime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="model")
    requests: list[AIRuntimeRequest]

    def __init__(self) -> None:
        self.requests = []

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        return AIRuntimeResult(output="analysis", identity=self.identity)


class WritingRuntime(Runtime):
    def __init__(self, workspace: Path, error: Exception | None = None) -> None:
        super().__init__()
        self.workspace = workspace
        self.error = error

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        (self.workspace / "created.txt").write_text("created", encoding="utf-8")
        if self.error is not None:
            raise self.error
        return AIRuntimeResult(output="written", identity=self.identity)


def service(tmp_path: Path, context_policy: SessionContextPolicy | None = None):
    projects = InMemoryProjectRepository()
    project = WorkspaceProject(
        project_id="project-1", name="Project", workspace_path=tmp_path,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    projects.save(project)
    runtime = Runtime()
    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)
    project_service = ProjectService(projects)
    sessions = InMemoryProjectSessionRepository()
    executions = InMemoryProjectExecutionRepository()
    session_service = ProjectSessionService(project_service, sessions, executions, id_generator=lambda: "session-1")
    session_service.create("project-1", "Test")
    return ProjectAIRuntimeExecutionService(
        project_service,
        registry,
        session_service,
        executions,
        context_builder=SessionContextBuilder(executions, context_policy),
    ), runtime, executions


def test_execution_resolves_workspace_only_from_persisted_project(tmp_path: Path) -> None:
    execution, runtime, _ = service(tmp_path)
    result = execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", session_id="session-1", runtime_id="codex",
        instruction=" Analyze project ", metadata={"source": "ui"},
    ))
    assert result.runtime_result.output == "analysis"
    assert result.execution_mode is AIRuntimeExecutionMode.READ_ONLY
    assert result.changes == ()
    assert result.execution.status.value == "succeeded"
    assert result.execution.output == "analysis"
    assert result.execution.model == "model"
    assert len(runtime.requests) == 1
    request = runtime.requests[0]
    assert request.instruction == "Analyze project"
    assert request.workspace == tmp_path.resolve()
    assert request.metadata["source"] == "ui"
    assert request.context["project_session"]["session_id"] == "session-1"
    assert request.context["project_session"]["entries"] == ()
    assert result.execution.context_entry_count == 0
    assert result.execution.context_truncated is False
    assert result.execution.context_char_count > 0
    assert result.execution.context_omitted_execution_count == 0
    serialized_context = json.dumps(
        {"project_session": request.model_dump(mode="json")["context"]["project_session"]},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert result.execution.context_char_count == len(serialized_context)
    assert result.execution.memory_entry_count == 0
    assert result.execution.memory_char_count > 0
    assert result.execution.memory_truncated is False


def test_later_execution_receives_limited_context_from_same_session(tmp_path: Path) -> None:
    execution, runtime, _ = service(tmp_path)
    execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", session_id="session-1", runtime_id="codex",
        instruction="Create a customer API",
    ))
    execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", session_id="session-1", runtime_id="codex",
        instruction="Now add CPF validation",
    ))

    context = runtime.requests[1].context["project_session"]
    assert len(context["entries"]) == 1
    entry = context["entries"][0]
    assert entry["instruction"] == "Create a customer API"
    assert entry["summary"] == "analysis"
    assert entry["status"] == "succeeded"
    assert "runtime_id" not in entry
    assert "usage" not in entry
    assert runtime.requests[1].instruction == "Now add CPF validation"

    third = execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", session_id="session-1", runtime_id="codex",
        instruction="Explain the result",
    ))
    assert len(runtime.requests[2].context["project_session"]["entries"]) == 2
    assert third.execution.context_entry_count == 2


def test_long_session_persists_budget_metrics_and_omits_old_history(tmp_path: Path) -> None:
    execution, runtime, repository = service(
        tmp_path, SessionContextPolicy(max_entries=2)
    )
    for index in range(4):
        result = execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="project-1", session_id="session-1", runtime_id="codex",
            instruction=f"step {index}",
        ))
    persisted = repository.get(result.execution.execution_id)
    assert persisted.context_entry_count == 2
    assert persisted.context_omitted_execution_count == 1
    assert persisted.context_truncated is True
    assert 0 < persisted.context_char_count <= 20_000
    entries = runtime.requests[-1].context["project_session"]["entries"]
    assert [entry["instruction"] for entry in entries] == ["step 1", "step 2"]


def test_missing_project_and_runtime_are_rejected(tmp_path: Path) -> None:
    execution, _, _ = service(tmp_path)
    with pytest.raises(ProjectNotFoundError):
        execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="missing", session_id="session-1", runtime_id="codex", instruction="test"
        ))
    with pytest.raises(AIRuntimeNotFoundError):
        execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="project-1", session_id="session-1", runtime_id="missing", instruction="test"
        ))


def test_workspace_write_reports_changes_and_propagates_mode(tmp_path: Path) -> None:
    projects = InMemoryProjectRepository()
    projects.save(WorkspaceProject(
        project_id="project-1", name="Project", workspace_path=tmp_path,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    runtime = WritingRuntime(tmp_path)
    registry = InMemoryAIRuntimeRegistry(); registry.register(runtime)
    project_service = ProjectService(projects); sessions = InMemoryProjectSessionRepository(); executions = InMemoryProjectExecutionRepository()
    session_service = ProjectSessionService(project_service, sessions, executions, id_generator=lambda: "session-1"); session_service.create("project-1", "Test")
    execution = ProjectAIRuntimeExecutionService(project_service, registry, session_service, executions)
    result = execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", session_id="session-1", runtime_id="codex", instruction="write",
        execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
    ))
    assert runtime.requests[0].execution_mode is AIRuntimeExecutionMode.WORKSPACE_WRITE
    assert [(change.path, change.change_type.value) for change in result.changes] == [
        ("created.txt", "created")
    ]


def test_failed_workspace_write_preserves_change_evidence(tmp_path: Path) -> None:
    projects = InMemoryProjectRepository()
    projects.save(WorkspaceProject(
        project_id="project-1", name="Project", workspace_path=tmp_path,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    failure = ValueError("runtime failed")
    runtime = WritingRuntime(tmp_path, failure)
    registry = InMemoryAIRuntimeRegistry(); registry.register(runtime)
    project_service = ProjectService(projects); sessions = InMemoryProjectSessionRepository(); executions = InMemoryProjectExecutionRepository()
    session_service = ProjectSessionService(project_service, sessions, executions, id_generator=lambda: "session-1"); session_service.create("project-1", "Test")
    execution = ProjectAIRuntimeExecutionService(project_service, registry, session_service, executions)
    with pytest.raises(ValueError) as caught:
        execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="project-1", session_id="session-1", runtime_id="codex", instruction="write",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        ))
    assert caught.value is failure
    assert caught.value.workspace_changes[0].path == "created.txt"  # type: ignore[attr-defined]
    persisted = executions.list_by_project("project-1")[0]
    assert persisted.status.value == "failed"
    assert persisted.error_code == "VALUE_ERROR"
    assert persisted.error_detail == "runtime failed"
    assert persisted.changes[0].path == "created.txt"
    runtime.error = None
    follow_up = execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", session_id="session-1", runtime_id="codex",
        instruction="Explain the partial failure",
    ))
    historical = runtime.requests[1].context["project_session"]["entries"]
    assert len(historical) == 1
    assert historical[0]["status"] == "failed"
    assert historical[0]["error_code"] == "VALUE_ERROR"
    assert historical[0]["summary"] is None
    assert historical[0]["changes"] == (
        {"path": "created.txt", "change_type": "created"},
    )
    assert follow_up.execution.context_entry_count == 1
