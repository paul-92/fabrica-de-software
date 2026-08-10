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
from asep.application import ProjectAIRuntimeExecutionService, ProjectService, ProjectSessionService, RunQueryService
from asep.metrics import MetricsService
from asep.projects import InMemoryProjectExecutionRepository, InMemoryProjectRepository, InMemoryProjectSessionRepository
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


def history(projects: ProjectService):
    sessions = InMemoryProjectSessionRepository(); executions = InMemoryProjectExecutionRepository()
    service = ProjectSessionService(projects, sessions, executions, id_generator=lambda: "s-1")
    service.create("p-1", "Session")
    return service, executions


def test_project_runtime_http_contract_excludes_workspace_and_preserves_result(tmp_path: Path) -> None:
    project_service = ProjectService(InMemoryProjectRepository(), id_generator=lambda: "p-1")
    project_service.create("Project", tmp_path)
    runtime = Runtime()
    registry = InMemoryAIRuntimeRegistry(); registry.register(runtime)
    sessions, executions = history(project_service)
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    app = create_app(
        query, MetricsService(query), project_service=project_service,
        project_ai_runtime_execution_service=ProjectAIRuntimeExecutionService(project_service, registry, sessions, executions),
        project_session_service=sessions,
    )
    client = TestClient(app)
    response = client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "session_id": "s-1", "runtime_id": "codex", "instruction": "inspect", "metadata": {"x": 1}
    })
    assert response.status_code == 200
    assert response.json() == {
        "execution_id": response.json()["execution_id"], "output": "safe result", "runtime_id": "codex", "model_id": "test-model",
        "usage": None, "metadata": {},
            "execution_mode": "read_only", "changes": [],
            "context_entry_count": 0, "context_truncated": False,
    }
    assert runtime.request.workspace == tmp_path.resolve()
    assert "prompt" not in response.json()
    assert "context" not in response.json()
    assert "history" not in response.json()
    second = client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "session_id": "s-1", "runtime_id": "codex", "instruction": "continue",
    })
    assert second.status_code == 200
    assert second.json()["context_entry_count"] == 1
    assert second.json()["context_truncated"] is False
    assert "context" not in second.json()
    execution_id = response.json()["execution_id"]
    second_execution_id = second.json()["execution_id"]
    assert client.get("/api/v1/projects/p-1/executions").json()["items"][0]["execution_id"] == second_execution_id
    assert client.get("/api/v1/projects/p-1/sessions/s-1/executions").json()["items"][0]["execution_id"] == second_execution_id
    assert client.get(f"/api/v1/projects/p-1/executions/{execution_id}").json()["status"] == "succeeded"
    assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "runtime_id": "codex", "instruction": "inspect"
    }).status_code == 422
    assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "session_id": "missing", "runtime_id": "codex", "instruction": "inspect"
    }).status_code == 404
    for forbidden in (
        "workspace_path", "cwd", "working_directory", "root", "sandbox",
        "context", "history", "previous_messages", "conversation",
    ):
        assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
            "session_id": "s-1", "runtime_id": "codex", "instruction": "inspect", forbidden: str(tmp_path)
        }).status_code == 422
    assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "session_id": "s-1", "runtime_id": "codex", "instruction": "inspect", "execution_mode": "unsafe"
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
    sessions, executions = history(projects)
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    client = TestClient(create_app(
        query, MetricsService(query), project_service=projects,
        project_ai_runtime_execution_service=ProjectAIRuntimeExecutionService(projects, registry, sessions, executions),
        project_session_service=sessions,
    ), raise_server_exceptions=False)
    response = client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "session_id": "s-1", "runtime_id": "codex", "instruction": "inspect"
    })
    assert response.status_code == status
    assert "secret" not in response.text.casefold()
    failed = sessions.list_session_executions("p-1", "s-1")[0]
    assert failed.status.value == "failed"
    assert failed.error_code is not None
    assert failed.output is None
    assert failed.model == "test-model"
    assert client.post("/api/v1/projects/p-1/ai-runtime/execute", json={
        "session_id": "s-1", "runtime_id": "codex", "instruction": "   "
    }).status_code == 422
