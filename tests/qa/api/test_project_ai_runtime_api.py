from pathlib import Path

from fastapi.testclient import TestClient

import pytest

from asep.ai_runtime import (
    AIRuntimeAuthenticationError,
    AIRuntimeIdentity,
    AIRuntimeInvalidResponseError,
    AIRuntimeResult,
    AIRuntimeTimeoutError,
    AIRuntimeUnavailableError,
    InMemoryAIRuntimeRegistry,
)
from asep.api.app import create_app
from asep.application import ProjectAIRuntimeExecutionService, ProjectService, RunQueryService
from asep.metrics import MetricsService
from asep.projects import InMemoryProjectRepository
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


class Runtime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="test-model")
    request = None
    def execute(self, request):
        self.request = request
        return AIRuntimeResult(output="safe result", identity=self.identity)


class FailingRuntime(Runtime):
    def __init__(self, error: Exception) -> None:
        self.error = error
    def execute(self, request):
        raise self.error


def test_project_runtime_http_contract_excludes_workspace_and_preserves_result(tmp_path: Path) -> None:
    project_service = ProjectService(InMemoryProjectRepository(), id_generator=lambda: "p-1")
    project_service.create("Project", tmp_path)
    runtime = Runtime()
    registry = InMemoryAIRuntimeRegistry(); registry.register(runtime)
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    app = create_app(
        query, MetricsService(query), project_service=project_service,
        project_ai_runtime_execution_service=ProjectAIRuntimeExecutionService(project_service, registry),
    )
    client = TestClient(app)
    response = client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "runtime_id": "codex", "instruction": "inspect", "metadata": {"x": 1}
    })
    assert response.status_code == 200
    assert response.json() == {
        "output": "safe result", "runtime_id": "codex", "model_id": "test-model",
        "usage": None, "metadata": {},
        "execution_mode": "read_only", "changes": [],
    }
    assert runtime.request.workspace == tmp_path.resolve()
    for forbidden in ("workspace_path", "cwd", "working_directory", "root", "sandbox"):
        assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
            "runtime_id": "codex", "instruction": "inspect", forbidden: str(tmp_path)
        }).status_code == 422
    assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "runtime_id": "codex", "instruction": "inspect", "execution_mode": "unsafe"
    }).status_code == 422


@pytest.mark.parametrize(("error", "status"), [
    (AIRuntimeAuthenticationError("codex"), 409),
    (AIRuntimeUnavailableError("codex"), 503),
    (AIRuntimeTimeoutError("codex"), 504),
    (AIRuntimeInvalidResponseError("codex"), 502),
])
def test_runtime_errors_are_safe(error: Exception, status: int, tmp_path: Path) -> None:
    projects = ProjectService(InMemoryProjectRepository(), id_generator=lambda: "p-1")
    projects.create("Project", tmp_path)
    registry = InMemoryAIRuntimeRegistry(); registry.register(FailingRuntime(error))
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    client = TestClient(create_app(
        query, MetricsService(query), project_service=projects,
        project_ai_runtime_execution_service=ProjectAIRuntimeExecutionService(projects, registry),
    ), raise_server_exceptions=False)
    response = client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "runtime_id": "codex", "instruction": "inspect"
    })
    assert response.status_code == status
    assert "secret" not in response.text.casefold()
    assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "runtime_id": "codex", "instruction": "   "
    }).status_code == 422
