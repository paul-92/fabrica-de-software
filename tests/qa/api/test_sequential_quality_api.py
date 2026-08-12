from __future__ import annotations

import ast
import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import create_app
from asep.application import (
    RunQueryService,
    SequentialExecution,
    SequentialExecutionNotFoundError,
    SequentialExecutionOwnershipError,
    SequentialProjectIdentityMismatchError,
    SequentialProjectNotFoundError,
    SequentialProjectPathError,
    SequentialQualityGateQueryService,
    SequentialStageSummary,
)
from asep.errors import StatePersistenceError
from asep.execution.models import ExecutionStatus, GateDecision, StageStatus
from asep.metrics import MetricsService
from asep.quality_results import (
    InMemoryQualityGateResultRepository,
    QualityGateResultStorageReadError,
    StoredQualityGateResult,
)
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository

PATH = "/api/v1/sequential-projects/sample/executions/execution/quality-gates"
NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


class ExecutionSource:
    def get(self, project_id: str, execution_id: str) -> SequentialExecution:
        return SequentialExecution(
            execution_id=execution_id,
            project_id=project_id,
            workflow_id="workflow",
            status=ExecutionStatus.COMPLETED,
            current_stage="analysis",
            created_at=NOW,
            updated_at=NOW,
            resumed_at=None,
            stages=(SequentialStageSummary(
                stage_id="analysis", agent_id="analyst", gate_id="QG-A",
                status=StageStatus.COMPLETED, attempts=1,
            ),),
        )


def app_client(service: object) -> TestClient:
    query = RunQueryService(
        InMemoryRunRepository(), InMemoryTimelineRepository()
    )
    return TestClient(create_app(
        query,
        MetricsService(query),
        sequential_quality_gate_service=service,  # type: ignore[arg-type]
    ), raise_server_exceptions=False)


def result(
    gate_id: str,
    stage_id: str,
    decision: GateDecision,
) -> StoredQualityGateResult:
    return StoredQualityGateResult(
        gate_id=gate_id,
        run_id="execution",
        stage_id=stage_id,
        decision=decision,
        satisfied_criteria=("kept",),
        unsatisfied_criteria=("missing",),
        evaluated_at=NOW,
    )


def test_returns_exact_canonical_fields_in_deterministic_order() -> None:
    repository = InMemoryQualityGateResultRepository()
    repository.record(result("QG-Z", "test", GateDecision.BLOCKED))
    repository.record(result("QG-A", "analysis", GateDecision.APPROVED))
    service = SequentialQualityGateQueryService(ExecutionSource(), repository)

    response = app_client(service).get(PATH)

    assert response.status_code == 200
    assert [item["gate_id"] for item in response.json()["items"]] == [
        "QG-A", "QG-Z",
    ]
    item = response.json()["items"][0]
    assert item == {
        "gate_id": "QG-A",
        "execution_id": "execution",
        "stage_id": "analysis",
        "decision": "APPROVED",
        "satisfied_criteria": ["kept"],
        "unsatisfied_criteria": ["missing"],
        "evaluated_at": "2026-08-11T12:00:00Z",
    }


def test_known_execution_with_zero_gates_returns_empty_collection() -> None:
    service = SequentialQualityGateQueryService(
        ExecutionSource(), InMemoryQualityGateResultRepository()
    )
    assert app_client(service).get(PATH).json() == {"items": []}


@pytest.mark.parametrize(
    "error",
    (
        SequentialProjectNotFoundError("secret path"),
        SequentialProjectPathError("secret path"),
        SequentialProjectIdentityMismatchError("secret path"),
        SequentialExecutionNotFoundError("secret path"),
        SequentialExecutionOwnershipError("secret path"),
    ),
)
def test_lookup_and_ownership_failures_share_safe_404(error: Exception) -> None:
    class FailingService:
        def get(self, project_id: str, execution_id: str):
            raise error

    response = app_client(FailingService()).get(PATH)
    assert response.status_code == 404
    assert response.json() == {"error": {
        "code": "SEQUENTIAL_QUALITY_RESOURCE_NOT_FOUND",
        "message": "Sequential execution quality results not found.",
    }}
    assert "secret" not in response.text


@pytest.mark.parametrize(
    "error",
    (
        StatePersistenceError("C:\\secret\\state.yaml"),
        QualityGateResultStorageReadError("sqlite secret"),
    ),
)
def test_internal_storage_failures_are_safe_500(error: Exception) -> None:
    class FailingService:
        def get(self, project_id: str, execution_id: str):
            raise error

    response = app_client(FailingService()).get(PATH)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "SEQUENTIAL_QUALITY_INTERNAL_ERROR"
    assert "secret" not in response.text.casefold()


def test_whitespace_identifiers_are_rejected_at_http_boundary() -> None:
    client = app_client(SequentialQualityGateQueryService(
        ExecutionSource(), InMemoryQualityGateResultRepository()
    ))
    assert client.get(PATH.replace("sample", "%20")).status_code == 422
    assert client.get(PATH.replace("/execution/", "/%20/")).status_code == 422


def test_orphan_gate_is_not_exposed_without_resolvable_execution() -> None:
    class MissingSource:
        def get(self, project_id: str, execution_id: str):
            raise SequentialExecutionNotFoundError("missing")

    repository = InMemoryQualityGateResultRepository()
    repository.record(result("QG-A", "analysis", GateDecision.APPROVED))
    response = app_client(
        SequentialQualityGateQueryService(MissingSource(), repository)
    ).get(PATH)
    assert response.status_code == 404


def test_openapi_contract_has_only_intended_fields_and_responses() -> None:
    service = SequentialQualityGateQueryService(
        ExecutionSource(), InMemoryQualityGateResultRepository()
    )
    schema = app_client(service).app.openapi()
    operation = schema["paths"][
        "/api/v1/sequential-projects/{project_id}/executions/"
        "{execution_id}/quality-gates"
    ]["get"]
    assert set(operation["responses"]) == {"200", "404", "422", "500"}
    properties = schema["components"]["schemas"][
        "SequentialQualityGateResponse"
    ]["properties"]
    assert set(properties) == {
        "gate_id", "execution_id", "stage_id", "decision",
        "satisfied_criteria", "unsatisfied_criteria", "evaluated_at",
    }
    serialized = str(properties).casefold()
    for forbidden in (
        "run_id", "project_id", "path", "yaml", "artifact", "metadata",
        "evidence", "health", "readiness", "executionstate",
    ):
        assert forbidden not in serialized


def test_http_adapter_imports_only_application_query_boundary() -> None:
    module = __import__("asep.api.sequential_quality_routes", fromlist=["*"])
    source = inspect.getsource(module)
    imported_modules = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported_modules <= {
        "__future__", "typing", "fastapi", "asep.api.routes",
        "asep.api.schemas", "asep.api.sequential_quality_schemas",
        "asep.application",
    }
    assert not any(module.startswith((
        "asep.execution", "asep.orchestrator", "asep.project",
        "asep.quality_results", "asep.repositories",
    )) for module in imported_modules)
