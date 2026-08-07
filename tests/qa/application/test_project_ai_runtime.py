from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.ai_runtime import (
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
    assert result.output == "analysis"
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
