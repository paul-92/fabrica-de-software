from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeRequest,
    AIRuntimeResult,
    InMemoryAIRuntimeRegistry,
)
from asep.api import (
    ProjectEngineeringOperationalComposition,
    create_project_engineering_operational_composition,
)
from asep.application import ProjectAIRuntimeExecutionRequest
from asep.configuration import ApplicationSettings


class FixtureRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="fixture")

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        workspace = request.workspace
        assert workspace is not None
        (workspace / "health.py").write_text("STATUS = 'ok'\n", encoding="utf-8")
        return AIRuntimeResult(output="done", identity=self.identity)


def registry() -> InMemoryAIRuntimeRegistry:
    result = InMemoryAIRuntimeRegistry()
    result.register(FixtureRuntime())
    return result


def create_project_and_session(client: TestClient, workspace: Path) -> tuple[str, str]:
    project = client.post(
        "/api/v1/projects",
        json={"name": "Fixture", "workspace_path": str(workspace)},
    )
    assert project.status_code == 201
    project_id = project.json()["project_id"]
    session = client.post(
        f"/api/v1/projects/{project_id}/sessions",
        json={"title": "Health"},
    )
    assert session.status_code == 201
    return project_id, session.json()["session_id"]


def test_composition_is_frozen_and_shares_http_project_history_and_memory(
    tmp_path: Path,
) -> None:
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry()
    )
    assert isinstance(composition, ProjectEngineeringOperationalComposition)
    assert isinstance(composition.app, FastAPI)
    with pytest.raises(FrozenInstanceError):
        composition.app = composition.app  # type: ignore[misc]

    client = TestClient(composition.app)
    project_id, session_id = create_project_and_session(client, tmp_path)
    memory = client.post(
        f"/api/v1/projects/{project_id}/sessions/{session_id}/memory",
        json={"kind": "fact", "content": "Small FastAPI project"},
    )
    assert memory.status_code == 201

    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project_id,
            session_id=session_id,
            runtime_id="codex",
            instruction="Add GET /health and a test.",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )

    history = client.get(
        f"/api/v1/projects/{project_id}/sessions/{session_id}/executions"
    )
    memories = client.get(
        f"/api/v1/projects/{project_id}/sessions/{session_id}/memory"
    )
    runs = client.get("/api/v1/runs")
    assert history.status_code == 200
    assert [item["execution_id"] for item in history.json()["items"]] == [
        result.execution.execution_id
    ]
    assert any(
        item["source_execution_id"] == result.execution.execution_id
        for item in memories.json()["items"]
    )
    assert runs.status_code == 200
    assert runs.json()["items"] == []
    assert not any(
        path.startswith("/api/v1/sequential-projects")
        for path in composition.app.openapi()["paths"]
    )


def test_operational_compositions_are_isolated(tmp_path: Path) -> None:
    first = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry()
    )
    second = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry()
    )
    first_client = TestClient(first.app)
    second_client = TestClient(second.app)
    project_id, session_id = create_project_and_session(first_client, tmp_path)

    first.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project_id,
            session_id=session_id,
            runtime_id="codex",
            instruction="Add health endpoint.",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )

    assert first_client.get("/api/v1/projects").json()["items"]
    assert second_client.get("/api/v1/projects").json()["items"] == []

