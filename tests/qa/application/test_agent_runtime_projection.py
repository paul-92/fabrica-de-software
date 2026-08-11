from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from asep.agents import (
    AgentCapability,
    AgentError,
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
    *,
    status: AgentExecutionStatus = AgentExecutionStatus.SUCCEEDED,
    retries: int = 0,
    duration: float = 0,
) -> None:
    observed_at = datetime(2026, 8, 11, tzinfo=UTC)
    metrics.record(
        AgentExecutionResult(
            execution_id=execution_id,
            agent_id=AgentId(value=agent_id),
            status=status,
            started_at=observed_at,
            completed_at=observed_at + timedelta(seconds=duration),
            duration_seconds=duration,
            attempts=1,
            error=(
                None
                if status is AgentExecutionStatus.SUCCEEDED
                else AgentError(code=status.value, message="Observed result.")
            ),
        ),
        AgentCapability(id="test"),
        retries=retries,
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
    assert result[0].model_dump() == {
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


def test_registered_agent_reports_observed_execution_count() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(Agent("reviewer"))
    metrics = InMemoryAgentExecutionMetrics()
    record_execution(metrics, "reviewer", "execution-1")
    record_execution(metrics, "reviewer", "execution-2")

    result = AgentRuntimeProjectionService(registry, metrics).list_agents()

    assert result[0].execution_count == 2
    assert result[0].succeeded == 2


def test_detailed_counters_and_retries_map_from_per_agent_metrics() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(Agent("reviewer"))
    registry.register(Agent("other"))
    metrics = InMemoryAgentExecutionMetrics()
    statuses = tuple(AgentExecutionStatus)
    for index, status in enumerate(statuses):
        record_execution(
            metrics,
            "reviewer",
            f"reviewer-{index}",
            status=status,
            retries=index,
            duration=float(index + 1),
        )
    record_execution(metrics, "other", "other-1")

    result = AgentRuntimeProjectionService(registry, metrics).list_agents()
    by_id = {item.agent_id: item for item in result}

    assert by_id["reviewer"].execution_count == 5
    assert by_id["reviewer"].succeeded == 1
    assert by_id["reviewer"].failed == 1
    assert by_id["reviewer"].rejected == 1
    assert by_id["reviewer"].cancelled == 1
    assert by_id["reviewer"].timed_out == 1
    assert by_id["reviewer"].retries == 10
    assert by_id["other"].execution_count == 1
    assert by_id["other"].succeeded == 1
    assert by_id["other"].retries == 0


def test_count_and_details_use_distinct_contract_fields() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(Agent("reviewer"))

    class Metrics:
        @staticmethod
        def snapshot():
            return SimpleNamespace(
                by_agent={"reviewer": 7},
                by_agent_metrics={
                    "reviewer": SimpleNamespace(
                        succeeded=1,
                        failed=2,
                        rejected=3,
                        cancelled=4,
                        timed_out=5,
                        retries=6,
                        duration_seconds=(99.0,),
                    )
                },
            )

    item = AgentRuntimeProjectionService(registry, Metrics()).list_agents()[0]

    assert item.execution_count == 7
    assert item.succeeded == 1
    assert item.failed == 2
    assert item.rejected == 3
    assert item.cancelled == 4
    assert item.timed_out == 5
    assert item.retries == 6
    assert "duration" not in item.model_dump()


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
        "succeeded",
        "failed",
        "rejected",
        "cancelled",
        "timed_out",
        "retries",
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
        "duration_seconds",
    ):
        assert unsupported not in serialized
