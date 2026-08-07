from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from asep.api import create_default_app
from asep.configuration import ApplicationSettings


ENDPOINT = "/api/v1/intelligent-engineering/execute"


def configured_client(workspace: Path) -> TestClient:
    return TestClient(
        create_default_app(
            ApplicationSettings(
                repair_workspace=workspace,
                cors_origins=("http://localhost:3000",),
            )
        )
    )


def payload() -> dict:
    return {
        "planning_request": {
            "goal": "Corrigir soma",
            "context": {
                "objective": "Restaurar comportamento",
            },
            "workflow_execution_id": "run-composition",
        },
        "knowledge_context": {
            "learned_entries": [],
            "knowledge_count": 0,
        },
        "engineering_request": {
            "analysis": {
                "summary": "A soma está incorreta.",
                "affected_paths": ["calculator.py"],
                "probable_cause": "Operador de subtração.",
            },
            "replacement_contents": {
                "calculator.py": "def add(a, b):\n    return a + b\n"
            },
            "test_paths": ["tests/test_calculator.py"],
        },
    }


def prepare_workspace(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "calculator.py").write_text(
        "def add(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (tmp_path / "tests/test_calculator.py").write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    return tmp_path


def test_configured_default_app_exposes_endpoint_without_startup_execution(
    tmp_path: Path,
) -> None:
    workspace = prepare_workspace(tmp_path)
    original = (workspace / "calculator.py").read_text(encoding="utf-8")
    client = configured_client(workspace)

    assert ENDPOINT in client.get("/openapi.json").json()["paths"]
    assert (workspace / "calculator.py").read_text(encoding="utf-8") == original
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/runs").status_code == 200
    assert client.get("/api/v1/metrics/summary").status_code == 200


def test_default_app_preserves_cors_for_intelligent_engineering(
    tmp_path: Path,
) -> None:
    response = configured_client(prepare_workspace(tmp_path)).options(
        ENDPOINT,
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )


def test_unconfigured_default_app_does_not_expose_repair_endpoint() -> None:
    client = TestClient(create_default_app(ApplicationSettings()))
    assert ENDPOINT not in client.get("/openapi.json").json()["paths"]


def test_post_crosses_real_composition_and_repairs_workspace(
    tmp_path: Path,
) -> None:
    workspace = prepare_workspace(tmp_path)
    body = payload()
    original = deepcopy(body)

    response = configured_client(workspace).post(ENDPOINT, json=body)

    assert response.status_code == 200, response.text
    assert body == original
    result = response.json()["engineering_result"]
    planning = response.json()["planning_result"]
    assert [step["tool_id"] for step in planning["plan"]["steps"]] == [
        "write-file",
        "run-tests",
    ]
    assert [
        step["required_capability"]
        for step in planning["plan"]["steps"]
    ] == ["write_file", "test"]
    assert result["proposal"]["candidate_files"] == ["calculator.py"]
    assert result["repair_result"]["status"] == "succeeded"
    assert result["reflection"]["should_retry"] is False
    assert "return a + b" in (workspace / "calculator.py").read_text(
        encoding="utf-8"
    )


def test_explicit_empty_workflow_is_a_safe_http_client_error(
    tmp_path: Path,
) -> None:
    body = payload()
    body["planning_request"]["context"]["workflow"] = {"steps": []}

    response = configured_client(prepare_workspace(tmp_path)).post(
        ENDPOINT,
        json=body,
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "PLANNING_INVALID",
            "message": "Planning request could not produce a valid plan.",
        }
    }


def test_gui_sample_path_runs_real_tests_without_validation_error(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "sample.txt").write_text("before\n", encoding="utf-8")
    (tmp_path / "tests/test_sample.py").write_text(
        "from pathlib import Path\n\n"
        "def test_sample():\n"
        "    assert Path('sample.txt').read_text(encoding='utf-8') "
        "== 'after\\n'\n",
        encoding="utf-8",
    )
    body = payload()
    body["engineering_request"] = {
        "analysis": {
            "summary": "Atualizar sample.",
            "affected_paths": ["sample.txt"],
        },
        "replacement_contents": {"sample.txt": "after\n"},
        "test_paths": ["tests"],
    }

    response = configured_client(tmp_path).post(ENDPOINT, json=body)

    assert response.status_code == 200
    result = response.json()["engineering_result"]
    assert result["repair_result"]["status"] == "succeeded"
    assert result["reflection"]["outcome"] == "succeeded"


def test_empty_test_directory_is_reported_as_pytest_failure(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    body = payload()
    body["engineering_request"] = {
        "analysis": {
            "summary": "Criar sample.",
            "affected_paths": ["sample.txt"],
        },
        "replacement_contents": {"sample.txt": "content\n"},
        "test_paths": ["tests"],
    }

    response = configured_client(tmp_path).post(ENDPOINT, json=body)

    assert response.status_code == 200
    result = response.json()["engineering_result"]
    assert result["repair_result"]["status"] == "failed"
    assert result["reflection"]["outcome"] == "failed"
    assert "no tests ran" in result["repair_result"]["attempts"][0][
        "validation_output"
    ]
