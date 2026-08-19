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
from asep.ai_runtime.engineering_decomposer import CodexEngineeringTaskDecomposer
from asep.api import (
    ProjectEngineeringOperationalComposition,
    create_project_engineering_operational_composition,
)
from asep.application import ProjectAIRuntimeExecutionRequest
from asep.configuration import ApplicationSettings


class FixtureRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="fixture")

    def __init__(self) -> None:
        self.requests: list[AIRuntimeRequest] = []

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        workspace = request.workspace
        assert workspace is not None
        (workspace / "health.py").write_text("STATUS = 'ok'\n", encoding="utf-8")
        (workspace / "tests").mkdir(exist_ok=True)
        (workspace / "tests" / "test_health.py").write_text(
            "from health import STATUS\n\n"
            "def test_health():\n"
            "    assert STATUS == 'ok'\n",
            encoding="utf-8",
        )
        return AIRuntimeResult(output="done", identity=self.identity)


class FailingFixtureRuntime(FixtureRuntime):
    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        result = super().execute(request)
        workspace = request.workspace
        assert workspace is not None
        (workspace / "tests" / "test_health.py").write_text(
            "def test_health():\n"
            "    assert False\n",
            encoding="utf-8",
        )
        return result


class DocumentationRuntime(FixtureRuntime):
    def __init__(self, *, perform_write: bool = True) -> None:
        super().__init__()
        self.perform_write = perform_write

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        workspace = request.workspace
        assert workspace is not None
        if self.perform_write:
            (workspace / "README.md").write_text(
                "# Empty project\n", encoding="utf-8"
            )
        return AIRuntimeResult(output="documentation task completed", identity=self.identity)


class PlanningRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex-planning", model_id="fixture")

    def __init__(self, steps: list[dict]) -> None:
        self.steps = steps

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        import json

        return AIRuntimeResult(
            output=json.dumps({"steps": self.steps}),
            identity=self.identity,
        )


def planned_step(step_id: str, description: str) -> dict:
    return {
        "step_id": step_id,
        "operation": "validate" if step_id == "validate" else "inspect",
        "description": description,
        "dependencies": [] if step_id != "validate" else ["inspect"],
        "target_hints": ["src/app/main.py"] if step_id == "inspect" else [],
        "validation_hints": ["pytest"] if step_id == "validate" else [],
    }


def registry(runtime: FixtureRuntime | None = None) -> InMemoryAIRuntimeRegistry:
    result = InMemoryAIRuntimeRegistry()
    result.register(runtime or FixtureRuntime())
    return result


def failing_registry() -> InMemoryAIRuntimeRegistry:
    result = InMemoryAIRuntimeRegistry()
    result.register(FailingFixtureRuntime())
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
    stored_gate = composition.quality_gate_results.list_by_run(
        result.execution.execution_id
    )
    assert stored_gate == (result.execution.quality_gate,)
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

    completed = first.project_engineering_execution.execute(
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
    assert first.quality_gate_results.list_by_run(
        completed.execution.execution_id
    )
    assert second.quality_gate_results.list_by_run(
        completed.execution.execution_id
    ) == ()


def test_http_acceptance_task_to_public_result_uses_one_execution(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="fixture"\ndependencies=["fastapi", "pytest"]\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )
    implementation_runtime = FixtureRuntime()
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry(implementation_runtime)
    )
    client = TestClient(composition.app)
    project_id, session_id = create_project_and_session(client, tmp_path)

    request_body = {
                "session_id": session_id,
                "runtime_id": "codex",
                "instruction": (
                    "Add GET /health returning {'status': 'ok'} and create a test."
                ),
                "execution_mode": "workspace_write",
            }
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())
    prepared_response = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare",
        json=request_body,
    )
    assert prepared_response.status_code == 201
    prepared = prepared_response.json()
    assert prepared["status"] == "pending"
    assert prepared["analysis"]["frameworks"] == ["FastAPI"]
    assert prepared["operational_plan"]["execution_id"] == prepared["execution_id"]
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()) == before
    assert implementation_runtime.requests == []

    response = client.post(
        f"/api/v1/projects/{project_id}/engineering/{prepared['execution_id']}/approve",
        json=request_body,
    )

    assert response.status_code == 200
    body = response.json()
    execution_id = body["execution_id"]
    assert execution_id == prepared["execution_id"]
    assert body["status"] == "succeeded"
    assert body["instruction"].startswith("Add GET /health")
    assert body["operational_plan"]["execution_id"] == execution_id
    assert len(body["operational_plan"]["steps"]) == 6
    assert body["operational_plan"]["steps"][0]["target_hints"] == [
        "src/app/main.py", "src"
    ]
    assert body["operational_plan"]["steps"][-1]["validation_hints"] == [
        "pytest"
    ]
    assert body["validations"][0]["execution_id"] == execution_id
    assert body["validations"][0]["status"] == "passed"
    assert body["validations"][0]["exit_code"] == 0
    assert [item["validator"] for item in body["validations"]] == [
        "compileall", "pytest"
    ]
    assert "pytest" in body["validations"][1]["command"]
    assert body["repair"] is None
    assert body["quality_gate"]["execution_id"] == execution_id
    assert body["quality_gate"]["decision"] == "APPROVED"
    engineering_context = implementation_runtime.requests[0].context[
        "project_engineering"
    ]
    assert engineering_context["task"] == body["instruction"]
    assert [step["step_id"] for step in engineering_context["ordered_steps"]] == [
        step["step_id"] for step in body["operational_plan"]["steps"]
    ]
    assert engineering_context["project_analysis"]["frameworks"] == (
        "FastAPI",
    )
    assert "root_path" not in str(engineering_context)
    assert body["operational_plan"]["source"] == "deterministic"
    assert {item["path"] for item in body["changes"]} == {
        "health.py",
        "tests/test_health.py",
    }
    history = client.get(
        f"/api/v1/projects/{project_id}/sessions/{session_id}/executions"
    ).json()["items"]
    memory = client.get(
        f"/api/v1/projects/{project_id}/sessions/{session_id}/memory"
    ).json()["items"]
    assert [item["execution_id"] for item in history] == [execution_id]
    assert history[0]["quality_gate"]["execution_id"] == execution_id
    assert all(item["source_execution_id"] == execution_id for item in memory)
    assert composition.quality_gate_results.list_by_run(execution_id)
    assert client.get("/api/v1/runs").json()["items"] == []
    assert "workspace_path" not in body
    assert "failure_output" not in str(body)
    assert "reason" not in str(body)

    operation = composition.app.openapi()["paths"][
        "/api/v1/projects/{project_id}/ai-runtime/execute"
    ]["post"]
    schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"].endswith("ProjectAIRuntimeExecutionResponse")


def test_document_only_workspace_write_succeeds_with_change_evidence(
    tmp_path: Path,
) -> None:
    implementation = DocumentationRuntime()
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry(implementation)
    )
    client = TestClient(composition.app)
    project_id, session_id = create_project_and_session(client, tmp_path)
    body = {
        "session_id": session_id,
        "runtime_id": "codex",
        "instruction": "Create README.md.",
        "execution_mode": "workspace_write",
    }
    prepared = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare", json=body,
    ).json()

    response = client.post(
        f"/api/v1/projects/{project_id}/engineering/{prepared['execution_id']}/approve",
        json=body,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "succeeded"
    assert result["error_code"] is None
    assert len(result["changes"]) == 1
    assert result["changes"][0]["path"] == "README.md"
    assert result["changes"][0]["change_type"] == "created"
    assert result["changes"][0]["size_before"] is None
    assert result["changes"][0]["size_after"] > 0
    assert [item["validator"] for item in result["validations"]] == [
        "workspace_changes"
    ]
    assert result["quality_gate"]["decision"] == "APPROVED"
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# Empty project\n"

    implementation.perform_write = False
    second_prepared = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare", json=body,
    ).json()
    second = client.post(
        f"/api/v1/projects/{project_id}/engineering/{second_prepared['execution_id']}/approve",
        json=body,
    )

    assert second.status_code == 200, second.text
    repeated = second.json()
    assert repeated["status"] == "succeeded"
    assert repeated["error_code"] is None
    assert repeated["changes"] == []
    assert repeated["repair"] is None
    assert repeated["quality_gate"]["decision"] == "APPROVED"
    assert [item["validator"] for item in repeated["validations"]] == [
        "idempotent_state"
    ]
    assert repeated["idempotent_noop_evidence"]["prior_execution_id"] == result[
        "execution_id"
    ]
    assert repeated["idempotent_noop_evidence"]["artifact_paths"] == [
        "README.md"
    ]


def test_unproven_noop_is_blocked_and_not_silently_approved(tmp_path: Path) -> None:
    implementation = DocumentationRuntime(perform_write=False)
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry(implementation)
    )
    client = TestClient(composition.app)
    project_id, session_id = create_project_and_session(client, tmp_path)
    body = {
        "session_id": session_id,
        "runtime_id": "codex",
        "instruction": "Create README.md.",
        "execution_mode": "workspace_write",
    }
    prepared = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare", json=body,
    ).json()

    response = client.post(
        f"/api/v1/projects/{project_id}/engineering/{prepared['execution_id']}/approve",
        json=body,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed"
    assert result["changes"] == []
    assert result["idempotent_noop_evidence"] is None
    assert result["quality_gate"]["decision"] == "BLOCKED"


def test_existing_incorrect_content_is_not_idempotent(tmp_path: Path) -> None:
    implementation = DocumentationRuntime()
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=registry(implementation)
    )
    client = TestClient(composition.app)
    project_id, session_id = create_project_and_session(client, tmp_path)
    body = {
        "session_id": session_id,
        "runtime_id": "codex",
        "instruction": "Create README.md.",
        "execution_mode": "workspace_write",
    }
    first = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare", json=body,
    ).json()
    assert client.post(
        f"/api/v1/projects/{project_id}/engineering/{first['execution_id']}/approve",
        json=body,
    ).json()["status"] == "succeeded"
    executed_workspace = implementation.requests[-1].workspace
    assert executed_workspace is not None
    (executed_workspace / "README.md").write_text("incorrect\n", encoding="utf-8")
    implementation.perform_write = False
    second = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare", json=body,
    ).json()

    response = client.post(
        f"/api/v1/projects/{project_id}/engineering/{second['execution_id']}/approve",
        json=body,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed"
    assert result["idempotent_noop_evidence"] is None
    assert result["quality_gate"]["decision"] == "BLOCKED"


def test_project_route_depends_only_on_application_boundary() -> None:
    source = Path("src/asep/api/project_routes.py").read_text(encoding="utf-8")
    for forbidden in (
        "CodexAIRuntime",
        "QualityGateEngine",
        "QualityGateResultRepository",
        "RunTestsTool",
        "ControlledRepairExecutor",
        "RepositoryFactory",
    ):
        assert forbidden not in source


def test_ai_plan_changes_the_context_used_by_execution(tmp_path: Path) -> None:
    observed = []
    for suffix, description in (("a", "Inspect route conventions."), ("b", "Inspect API modules.")):
        workspace = tmp_path / suffix
        workspace.mkdir()
        (workspace / "pyproject.toml").write_text(
            '[project]\nname="fixture"\ndependencies=["pytest"]\n',
            encoding="utf-8",
        )
        (workspace / "src" / "app").mkdir(parents=True)
        (workspace / "src" / "app" / "main.py").write_text(
            "from fastapi import FastAPI\n", encoding="utf-8"
        )
        implementation = FixtureRuntime()
        decomposer = CodexEngineeringTaskDecomposer(PlanningRuntime([
            planned_step("inspect", description),
            planned_step("validate", "Run tests."),
        ]))
        composition = create_project_engineering_operational_composition(
            ApplicationSettings(),
            runtime_registry=registry(implementation),
            engineering_decomposer=decomposer,
        )
        client = TestClient(composition.app)
        project_id, session_id = create_project_and_session(client, workspace)
        response = client.post(
            f"/api/v1/projects/{project_id}/ai-runtime/execute",
            json={
                "session_id": session_id,
                "runtime_id": "codex",
                "instruction": "Add GET /health and tests.",
                "execution_mode": "workspace_write",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "succeeded"
        assert response.json()["operational_plan"]["source"] == "ai"
        assert [
            item["validator"] for item in response.json()["validations"]
        ] == ["compileall", "pytest"]
        assert response.json()["quality_gate"]["decision"] == "APPROVED"
        observed.append(implementation.requests[0].context["project_engineering"])

    assert observed[0]["task"] == observed[1]["task"]
    assert observed[0]["ordered_steps"] != observed[1]["ordered_steps"]
    assert observed[0]["ordered_steps"][0]["description"] == (
        "Inspect route conventions."
    )
    assert observed[1]["ordered_steps"][0]["description"] == (
        "Inspect API modules."
    )


def test_http_validation_failure_preserves_bounded_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="fixture"\ndependencies=["pytest"]\n',
        encoding="utf-8",
    )
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(), runtime_registry=failing_registry()
    )
    client = TestClient(composition.app)
    project_id, session_id = create_project_and_session(client, tmp_path)

    response = client.post(
        f"/api/v1/projects/{project_id}/ai-runtime/execute",
        json={
            "session_id": session_id,
            "runtime_id": "codex",
            "instruction": "Add a health endpoint.",
            "execution_mode": "workspace_write",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "REPAIR_EXHAUSTED"
    assert [item["validator"] for item in body["validations"]] == [
        "compileall", "pytest", "pytest"
    ]
    assert body["repair"]["attempt_count"] == 1
    assert body["repair"]["outcome"] == "exhausted"
    assert body["quality_gate"]["decision"] == "BLOCKED"
    assert body["changes"]
    assert all(len(item["output"]) <= 20_019 for item in body["validations"])
    serialized = str(body)
    assert "failure_output" not in serialized
    assert "probable_cause" not in serialized
    assert "workspace_path" not in serialized
def test_http_dependency_version_selection_creates_pending_request_without_runtime(
    tmp_path: Path,
) -> None:
    (tmp_path / ".asep").mkdir()

    (tmp_path / ".asep" / "dependency-baseline.json").write_text(
        (
            '{"status":"approved","dependencies":['
            '{"package":"typescript","reason":"compiler"}'
            "]}"
        ),
        encoding="utf-8",
    )

    implementation_runtime = FixtureRuntime()

    composition = create_project_engineering_operational_composition(
        ApplicationSettings(),
        runtime_registry=registry(implementation_runtime),
    )

    client = TestClient(composition.app)

    project_id, session_id = create_project_and_session(
        client,
        tmp_path,
    )

    request_body = {
        "session_id": session_id,
        "runtime_id": "codex",
        "instruction": "Prepare Sprint 1 foundation.",
        "execution_mode": "workspace_write",
        "engineering_phase": "development",
        "sprint_id": "1",
        "sprint_name": "Foundation",
    }

    before = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    )

    prepared_response = client.post(
        f"/api/v1/projects/{project_id}/engineering/prepare",
        json=request_body,
    )

    assert prepared_response.status_code == 201, prepared_response.text

    prepared = prepared_response.json()

    assert prepared["status"] == "blocked"
    assert prepared["error_code"] == "version_selection_required"

    assert len(prepared["dependency_plan"]["items"]) == 1

    original_item = prepared["dependency_plan"]["items"][0]

    assert original_item["package"] == "typescript"
    assert original_item["requested_version"] is None
    assert original_item["status"] == "version_selection_required"
    assert original_item["dependency_request_id"] is None

    assert implementation_runtime.requests == []

    response = client.post(
        (
            f"/api/v1/projects/{project_id}/engineering/"
            f"{prepared['execution_id']}/dependencies/typescript/version"
        ),
        json={
            "version": "5.9.2",
        },
    )

    assert response.status_code == 200, response.text

    updated = response.json()

    assert updated["execution_id"] == prepared["execution_id"]
    assert updated["project_id"] == project_id
    assert updated["status"] == "blocked"
    assert updated["error_code"] == "dependency_approval_required"

    assert (
        updated["next_action"]
        == "Revise e aprove as dependências necessárias."
    )

    assert len(updated["dependency_plan"]["items"]) == 1

    item = updated["dependency_plan"]["items"][0]

    assert item["package"] == "typescript"
    assert item["requested_version"] == "5.9.2"
    assert item["status"] == "pending"
    assert item["dependency_request_id"]

    dependency_request_id = item["dependency_request_id"]

    requests_response = client.get(
        f"/api/v1/projects/{project_id}/dependency-requests"
    )

    assert requests_response.status_code == 200

    dependency_requests = requests_response.json()

    assert len(dependency_requests) == 1

    stored = dependency_requests[0]

    assert stored["request_id"] == dependency_request_id
    assert stored["project_id"] == project_id
    assert stored["execution_id"] == prepared["execution_id"]
    assert stored["package"] == "typescript"
    assert stored["requested_version"] == "5.9.2"
    assert stored["reason"] == "compiler"
    assert stored["status"] == "pending"

    single_request_response = client.get(
        (
            f"/api/v1/projects/{project_id}/dependency-requests/"
            f"{dependency_request_id}"
        )
    )

    assert single_request_response.status_code == 200
    assert single_request_response.json() == stored

    after = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    )

    assert after == before
    assert implementation_runtime.requests == []