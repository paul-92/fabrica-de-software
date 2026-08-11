from datetime import UTC, datetime

from asep.agents import (
    AgentCapability,
    AgentExecutionResult,
    AgentExecutionStatus,
    AgentId,
    AgentMetadata,
    InMemoryAgentExecutionMetrics,
    InMemoryAgentRegistry,
)
from asep.application import (
    AgentRuntimeMetricsSource,
    AgentRuntimeProjection,
    AgentRuntimeProjectionService,
)


class Agent:
    def __init__(self, agent_id: str) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value=agent_id),
            name=agent_id.title(),
            description="Projection test agent.",
            version="1.0",
            capabilities=(AgentCapability(id="test"),),
        )

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(self, request, context):  # pragma: no cover - never invoked
        raise AssertionError("projection must not execute agents")


def record_execution(
    metrics: InMemoryAgentExecutionMetrics,
    agent_id: str,
    execution_id: str,
) -> None:
    observed_at = datetime(2026, 8, 11, tzinfo=UTC)
    metrics.record(
        AgentExecutionResult(
            execution_id=execution_id,
            agent_id=AgentId(value=agent_id),
            status=AgentExecutionStatus.SUCCEEDED,
            started_at=observed_at,
            completed_at=observed_at,
            duration_seconds=0,
            attempts=1,
        ),
        AgentCapability(id="test"),
        retries=0,
    )


def test_registered_agent_without_observed_executions_reports_zero() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(Agent("reviewer"))
    metrics = InMemoryAgentExecutionMetrics()

    result = AgentRuntimeProjectionService(registry, metrics).list_agents()

    assert isinstance(metrics, AgentRuntimeMetricsSource)
    assert result == (
        AgentRuntimeProjection(
            agent_id="reviewer",
            registered=True,
            execution_count=0,
        ),
    )


def test_registered_agent_reports_observed_execution_count() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(Agent("reviewer"))
    metrics = InMemoryAgentExecutionMetrics()
    record_execution(metrics, "reviewer", "execution-1")
    record_execution(metrics, "reviewer", "execution-2")

    result = AgentRuntimeProjectionService(registry, metrics).list_agents()

    assert result[0].execution_count == 2


def test_projection_is_deterministic_and_contains_only_supported_facts() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(Agent("zeta"))
    registry.register(Agent("alpha"))
    metrics = InMemoryAgentExecutionMetrics()
    service = AgentRuntimeProjectionService(registry, metrics)

    first = service.list_agents()
    second = service.list_agents()

    assert first == second
    assert [item.agent_id for item in first] == ["alpha", "zeta"]
    assert set(AgentRuntimeProjection.model_fields) == {
        "agent_id",
        "registered",
        "execution_count",
    }
    serialized = str([item.model_dump() for item in first]).casefold()
    for unsupported in (
        "healthy",
        "unhealthy",
        "online",
        "offline",
        "ready",
        "unready",
        "lifecycle_status",
    ):
        assert unsupported not in serialized

