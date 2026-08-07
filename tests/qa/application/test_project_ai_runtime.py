from datetime import UTC, datetime
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
)
from asep.errors import ProjectNotFoundError
from asep.projects import InMemoryProjectRepository, WorkspaceProject


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


def service(tmp_path: Path):
    projects = InMemoryProjectRepository()
    project = WorkspaceProject(
        project_id="project-1", name="Project", workspace_path=tmp_path,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    projects.save(project)
    runtime = Runtime()
    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)
    return ProjectAIRuntimeExecutionService(ProjectService(projects), registry), runtime


def test_execution_resolves_workspace_only_from_persisted_project(tmp_path: Path) -> None:
    execution, runtime = service(tmp_path)
    result = execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", runtime_id="codex",
        instruction=" Analyze project ", metadata={"source": "ui"},
    ))
    assert result.runtime_result.output == "analysis"
    assert result.execution_mode is AIRuntimeExecutionMode.READ_ONLY
    assert result.changes == ()
    assert len(runtime.requests) == 1
    request = runtime.requests[0]
    assert request.instruction == "Analyze project"
    assert request.workspace == tmp_path.resolve()
    assert request.metadata["source"] == "ui"


def test_missing_project_and_runtime_are_rejected(tmp_path: Path) -> None:
    execution, _ = service(tmp_path)
    with pytest.raises(ProjectNotFoundError):
        execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="missing", runtime_id="codex", instruction="test"
        ))
    with pytest.raises(AIRuntimeNotFoundError):
        execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="project-1", runtime_id="missing", instruction="test"
        ))


def test_workspace_write_reports_changes_and_propagates_mode(tmp_path: Path) -> None:
    projects = InMemoryProjectRepository()
    projects.save(WorkspaceProject(
        project_id="project-1", name="Project", workspace_path=tmp_path,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    ))
    runtime = WritingRuntime(tmp_path)
    registry = InMemoryAIRuntimeRegistry(); registry.register(runtime)
    execution = ProjectAIRuntimeExecutionService(ProjectService(projects), registry)
    result = execution.execute(ProjectAIRuntimeExecutionRequest(
        project_id="project-1", runtime_id="codex", instruction="write",
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
    execution = ProjectAIRuntimeExecutionService(ProjectService(projects), registry)
    with pytest.raises(ValueError) as caught:
        execution.execute(ProjectAIRuntimeExecutionRequest(
            project_id="project-1", runtime_id="codex", instruction="write",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        ))
    assert caught.value is failure
    assert caught.value.workspace_changes[0].path == "created.txt"  # type: ignore[attr-defined]
