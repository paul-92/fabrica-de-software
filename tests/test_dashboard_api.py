from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asep.api import create_app, create_default_app
from asep.application import RunQueryService
from asep.metrics import MetricsService
from asep.runs import (
    InMemoryRunRepository,
    Run,
    RunError,
    RunStatus,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEvent,
    TimelineEventType,
)

START = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def make_run(
    run_id: str,
    *,
    status: RunStatus = RunStatus.PENDING,
    started_at: datetime = START,
    finished_at: datetime | None = None,
    **values,
) -> Run:
    return Run(
        id=run_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        **values,
    )


def make_event(
    event_id: str,
    run_id: str,
    *,
    timestamp: datetime = START,
    event_type: TimelineEventType = TimelineEventType.RUN_STARTED,
    **values,
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        type=event_type,
        **values,
    )


@pytest.fixture
def api():
    runs = InMemoryRunRepository()
    timeline = InMemoryTimelineRepository()
    query = RunQueryService(runs, timeline)
    metrics = MetricsService(query)
    app = create_app(query, metrics)
    return TestClient(app), runs, timeline, query, metrics, app


def test_factory_creates_fastapi_with_injected_services(api) -> None:
    _, _, _, query, metrics, app = api

    assert isinstance(app, FastAPI)
    assert app.state.run_query_service is query
    assert app.state.metrics_service is metrics


def test_default_factory_creates_isolated_applications() -> None:
    first = create_default_app()
    second = create_default_app()

    assert first is not second
    assert (
        first.state.run_query_service
        is not second.state.run_query_service
    )
    assert first.state.metrics_service is not second.state.metrics_service


def test_health_is_small_json_response(api) -> None:
    client, *_ = api

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok", "api_version": "v1"}


def test_empty_run_list(api) -> None:
    client, *_ = api

    response = client.get("/api/v1/runs")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_run_list_preserves_service_order_and_serializes_fields(api) -> None:
    client, runs, *_ = api
    old = make_run("old", metadata={"nested": {"value": 1}})
    new = make_run(
        "new",
        status=RunStatus.RUNNING,
        started_at=START + timedelta(seconds=1),
        project_id="project",
        workflow_id="workflow",
        stage_id="analysis",
        provider_name="codex",
        summary="Running.",
    )
    runs.save(old)
    runs.save(new)

    response = client.get("/api/v1/runs")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == ["new", "old"]
    assert body["items"][0] == {
        "id": "new",
        "status": "running",
        "started_at": "2026-07-29T12:00:01Z",
        "finished_at": None,
        "project_id": "project",
        "workflow_id": "workflow",
        "stage_id": "analysis",
        "provider_name": "codex",
        "summary": "Running.",
        "error": None,
        "metadata": {},
    }
    assert body["items"][1]["metadata"] == {
        "nested": {"value": 1}
    }


def test_run_list_delegates_typed_status_filter(api) -> None:
    client, runs, *_ = api
    runs.save(make_run("failed", status=RunStatus.FAILED))
    runs.save(make_run("running", status=RunStatus.RUNNING))

    response = client.get("/api/v1/runs", params={"status": "failed"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [
        "failed"
    ]


def test_invalid_status_is_structured_422(api) -> None:
    client, *_ = api

    response = client.get(
        "/api/v1/runs",
        params={"status": "unknown"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "Request validation failed.",
        }
    }
    assert "traceback" not in response.text.lower()


def test_run_detail_serializes_structured_error(api) -> None:
    client, runs, *_ = api
    runs.save(
        make_run(
            "failed",
            status=RunStatus.FAILED,
            finished_at=START + timedelta(seconds=1),
            error=RunError(
                type="ProviderError",
                message="Provider unavailable.",
                details={"retryable": False},
            ),
        )
    )

    response = client.get("/api/v1/runs/failed")

    assert response.status_code == 200
    assert response.json()["error"] == {
        "type": "ProviderError",
        "message": "Provider unavailable.",
        "details": {"retryable": False},
    }
    assert response.json()["finished_at"] == "2026-07-29T12:00:01Z"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/runs/missing",
        "/api/v1/runs/missing/timeline",
    ],
)
def test_missing_run_is_safe_404(api, path: str) -> None:
    client, *_ = api

    response = client.get(path)

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RUN_NOT_FOUND",
            "message": "Run not found.",
        }
    }
    assert "traceback" not in response.text.lower()
    assert ".py" not in response.text


def test_blank_run_id_is_safe_client_error(api) -> None:
    client, *_ = api

    response = client.get("/api/v1/runs/%20")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_timeline_preserves_chronological_order_and_schema(api) -> None:
    client, runs, timeline, *_ = api
    runs.save(make_run("run"))
    timeline.append(
        make_event(
            "last",
            "run",
            timestamp=START + timedelta(seconds=1),
            event_type=TimelineEventType.STAGE_FINISHED,
            stage_id="analysis",
            message="Finished.",
            metadata={"attempt": 1},
        )
    )
    timeline.append(make_event("first", "run"))

    response = client.get("/api/v1/runs/run/timeline")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == ["first", "last"]
    assert items[0]["timestamp"] == "2026-07-29T12:00:00Z"
    assert items[0]["type"] == "run.started"
    assert items[1]["stage_id"] == "analysis"
    assert items[1]["metadata"] == {"attempt": 1}


def test_existing_run_can_have_empty_timeline(api) -> None:
    client, runs, *_ = api
    runs.save(make_run("run"))

    response = client.get("/api/v1/runs/run/timeline")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_empty_metrics_summary_uses_domain_semantics(api) -> None:
    client, *_ = api

    response = client.get("/api/v1/metrics/summary")

    assert response.status_code == 200
    assert response.json()["total_runs"] == 0
    assert response.json()["success_rate"] == 0
    assert response.json()["failure_rate"] == 0
    assert response.json()["duration"] == {
        "count": 0,
        "ignored_count": 0,
        "minimum_seconds": None,
        "maximum_seconds": None,
        "average_seconds": None,
        "median_seconds": None,
    }


def test_metrics_summary_preserves_rates_and_duration_seconds(api) -> None:
    client, runs, *_ = api
    runs.save(
        make_run(
            "success",
            status=RunStatus.SUCCEEDED,
            finished_at=START + timedelta(seconds=2.5),
        )
    )
    runs.save(make_run("failed", status=RunStatus.FAILED))

    response = client.get("/api/v1/metrics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_runs"] == 2
    assert body["success_rate"] == 0.5
    assert body["failure_rate"] == 0.5
    assert body["duration"]["average_seconds"] == 2.5
    assert body["duration"]["ignored_count"] == 1


def test_status_metrics_include_all_statuses_in_enum_order(api) -> None:
    client, runs, *_ = api
    runs.save(make_run("failed", status=RunStatus.FAILED))

    response = client.get("/api/v1/metrics/status")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"status": "pending", "count": 0},
        {"status": "running", "count": 0},
        {"status": "succeeded", "count": 0},
        {"status": "failed", "count": 1},
        {"status": "cancelled", "count": 0},
    ]


def test_provider_metrics_preserve_missing_provider_and_order(api) -> None:
    client, runs, *_ = api
    runs.save(make_run("none", status=RunStatus.RUNNING))
    runs.save(
        make_run(
            "z",
            status=RunStatus.SUCCEEDED,
            provider_name="zeta",
            finished_at=START + timedelta(seconds=4),
        )
    )
    runs.save(
        make_run(
            "a",
            status=RunStatus.FAILED,
            provider_name="Alpha",
        )
    )

    response = client.get("/api/v1/metrics/providers")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["provider_name"] for item in items] == [
        None,
        "Alpha",
        "zeta",
    ]
    assert items[2]["success_rate"] == 1
    assert items[2]["duration"]["average_seconds"] == 4


def test_openapi_documents_only_supported_read_routes(api) -> None:
    client, *_ = api

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "ASEP Dashboard API"
    assert schema["info"]["version"] == "0.1.0"
    assert set(schema["paths"]) == {
        "/api/v1/health",
        "/api/v1/runs",
        "/api/v1/runs/{run_id}",
        "/api/v1/runs/{run_id}/timeline",
        "/api/v1/metrics/summary",
        "/api/v1/metrics/status",
        "/api/v1/metrics/providers",
    }
    assert all(
        set(operations) <= {"get", "parameters"}
        for operations in schema["paths"].values()
    )
    assert "/api/v1/metrics/stages" not in schema["paths"]


def test_swagger_docs_are_available(api) -> None:
    client, *_ = api

    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ASEP Dashboard API" in response.text


def test_unexpected_error_is_generic_500() -> None:
    class FailingQuery:
        def list_runs(self):
            raise RuntimeError(
                "secret at C:\\private\\source.py line 99"
            )

    query = FailingQuery()
    app = create_app(
        query,  # type: ignore[arg-type]
        MetricsService(query),  # type: ignore[arg-type]
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/runs")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error.",
        }
    }
    assert "secret" not in response.text
    assert "source.py" not in response.text
    assert "traceback" not in response.text.lower()


def test_unexpected_value_error_is_not_misclassified_as_client_error() -> None:
    class FailingQuery:
        def list_runs(self):
            raise ValueError("sensitive internal invariant")

    query = FailingQuery()
    app = create_app(
        query,  # type: ignore[arg-type]
        MetricsService(query),  # type: ignore[arg-type]
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/runs")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "sensitive" not in response.text


def test_routes_do_not_import_storage_or_recalculate_metrics() -> None:
    import asep.api.routes as routes

    source = inspect.getsource(routes)
    assert "RunRepository" not in source
    assert "TimelineRepository" not in source
    assert "InMemoryRunRepository" not in source
    assert "InMemoryTimelineRepository" not in source
    assert "success_rate =" not in source
    assert "average_seconds =" not in source


def test_api_composition_uses_repository_factory() -> None:
    import asep.api.app as app_module
    import asep.api.composition as composition
    import asep.api.errors as errors
    import asep.api.routes as routes
    import asep.api.schemas as schemas

    for module in (app_module, errors, routes, schemas):
        source = inspect.getsource(module)
        assert "InMemoryRunRepository" not in source
        assert "InMemoryTimelineRepository" not in source
    composition_source = inspect.getsource(composition)
    assert "RepositoryFactory" in composition_source
    assert "InMemoryRunRepository" not in composition_source
    assert "InMemoryTimelineRepository" not in composition_source


def test_domain_and_services_do_not_import_fastapi() -> None:
    import asep.application.run_query as query_module
    import asep.metrics.service as metrics_module
    import asep.runs.models as run_models
    import asep.timeline.models as timeline_models

    for module in (
        query_module,
        metrics_module,
        run_models,
        timeline_models,
    ):
        assert "fastapi" not in inspect.getsource(module).lower()


def test_requests_do_not_mutate_domain_snapshots(api) -> None:
    client, runs, timeline, *_ = api
    run = make_run("run", metadata={"nested": {"value": 1}})
    event = make_event("event", "run", metadata={"items": [1, 2]})
    runs.save(run)
    timeline.append(event)
    run_before = run.model_dump(mode="json")
    event_before = event.model_dump(mode="json")

    client.get("/api/v1/runs")
    client.get("/api/v1/runs/run")
    client.get("/api/v1/runs/run/timeline")
    client.get("/api/v1/metrics/summary")

    assert run.model_dump(mode="json") == run_before
    assert event.model_dump(mode="json") == event_before


def test_public_api_exports_are_intentional() -> None:
    import asep.api as api_module

    assert set(api_module.__all__) == {
        "create_app",
        "create_default_app",
    }
