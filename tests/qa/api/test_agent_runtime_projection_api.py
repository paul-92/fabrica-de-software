from pathlib import Path

from fastapi.testclient import TestClient

from asep.api import create_app
from asep.application import AgentRuntimeProjection, RunQueryService
from asep.metrics import MetricsService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


class RuntimeProjectionService:
    def __init__(
        self,
        projection: AgentRuntimeProjection | None = None,
    ) -> None:
        self.calls = 0
        self.projection = projection or AgentRuntimeProjection(
            agent_id="reviewer",
            registered=True,
            execution_count=3,
            succeeded=2,
            failed=1,
            retries=1,
        )

    def list_agents(self) -> tuple[AgentRuntimeProjection, ...]:
        self.calls += 1
        return (self.projection,)


def client(service: RuntimeProjectionService) -> TestClient:
    query = RunQueryService(
        InMemoryRunRepository(), InMemoryTimelineRepository()
    )
    return TestClient(
        create_app(
            query,
            MetricsService(query),
            agent_runtime_projection_service=service,
        )
    )


def test_http_maps_application_runtime_projection() -> None:
    service = RuntimeProjectionService()

    response = client(service).get("/api/v1/agents/runtime")

    assert response.status_code == 200
    assert service.calls == 1
    assert response.json() == {
        "items": [
            {
                "agent_id": "reviewer",
                "registered": True,
                "execution_count": 3,
                "succeeded": 2,
                "failed": 1,
                "rejected": 0,
                "cancelled": 0,
                "timed_out": 0,
                "retries": 1,
            }
        ]
    }


def test_http_contract_contains_no_health_or_readiness_semantics() -> None:
    app = client(RuntimeProjectionService()).app
    schema = app.openapi()
    properties = schema["components"]["schemas"][
        "AgentRuntimeProjectionItemResponse"
    ]["properties"]

    assert set(properties) == {
        "agent_id",
        "registered",
        "execution_count",
        "succeeded",
        "failed",
        "rejected",
        "cancelled",
        "timed_out",
        "retries",
    }
    assert "/api/v1/agents/runtime" in schema["paths"]
    serialized = str(properties).casefold()
    for unsupported in (
        "healthy",
        "unhealthy",
        "online",
        "offline",
        "ready",
        "unready",
        "lifecycle_status",
        "duration_seconds",
    ):
        assert unsupported not in serialized


def test_http_serializes_zero_metrics_for_unobserved_agent() -> None:
    service = RuntimeProjectionService(
        AgentRuntimeProjection(
            agent_id="reviewer",
            registered=True,
            execution_count=0,
        )
    )

    item = client(service).get("/api/v1/agents/runtime").json()["items"][0]

    assert item == {
        "agent_id": "reviewer",
        "registered": True,
        "execution_count": 0,
        "succeeded": 0,
        "failed": 0,
        "rejected": 0,
        "cancelled": 0,
        "timed_out": 0,
        "retries": 0,
    }


def test_http_adapter_depends_only_on_application_projection() -> None:
    source = Path("src/asep/api/agent_routes.py").read_text(encoding="utf-8")

    assert "AgentRegistry" not in source
    assert "AgentExecutionMetrics" not in source
    assert "_results" not in source
    assert "_in_progress" not in source
