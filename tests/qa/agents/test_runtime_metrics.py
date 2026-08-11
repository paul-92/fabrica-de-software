from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from asep.agents import (
    AgentCapability,
    AgentError,
    AgentExecutionResult,
    AgentExecutionMetricsSnapshot,
    AgentExecutionStatus,
    AgentId,
    InMemoryAgentExecutionMetrics,
    PerAgentExecutionMetricsSnapshot,
)


STARTED_AT = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def test_existing_global_snapshot_constructor_remains_compatible() -> None:
    snapshot = AgentExecutionMetricsSnapshot(
        0, 0, 0, 0, 0, 0, 0, (), {}, {}
    )

    assert snapshot.by_agent == {}
    assert snapshot.by_capability == {}
    assert snapshot.by_agent_metrics == {}


def result(
    agent_id: str,
    status: AgentExecutionStatus,
    *,
    execution_id: str,
    duration: float,
) -> AgentExecutionResult:
    return AgentExecutionResult(
        execution_id=execution_id,
        agent_id=AgentId(value=agent_id),
        status=status,
        started_at=STARTED_AT,
        completed_at=STARTED_AT + timedelta(seconds=duration),
        duration_seconds=duration,
        attempts=1,
        error=(
            None
            if status is AgentExecutionStatus.SUCCEEDED
            else AgentError(code=status.value, message="Observed result.")
        ),
    )


def record(
    metrics: InMemoryAgentExecutionMetrics,
    agent_id: str,
    status: AgentExecutionStatus,
    *,
    execution_id: str,
    duration: float,
    retries: int = 0,
) -> None:
    metrics.record(
        result(
            agent_id,
            status,
            execution_id=execution_id,
            duration=duration,
        ),
        AgentCapability(id="review"),
        retries=retries,
    )


def test_success_creates_frozen_per_agent_snapshot() -> None:
    metrics = InMemoryAgentExecutionMetrics()
    record(
        metrics,
        "reviewer",
        AgentExecutionStatus.SUCCEEDED,
        execution_id="execution-1",
        duration=1.25,
    )

    item = metrics.snapshot().by_agent_metrics["reviewer"]

    assert item == PerAgentExecutionMetricsSnapshot(
        total=1,
        succeeded=1,
        failed=0,
        rejected=0,
        cancelled=0,
        timed_out=0,
        retries=0,
        duration_seconds=(1.25,),
    )
    with pytest.raises(FrozenInstanceError):
        item.total = 2  # type: ignore[misc]


def test_mixed_statuses_are_attributed_to_one_agent() -> None:
    metrics = InMemoryAgentExecutionMetrics()
    statuses = tuple(AgentExecutionStatus)
    for index, status in enumerate(statuses):
        record(
            metrics,
            "reviewer",
            status,
            execution_id=f"execution-{index}",
            duration=float(index),
        )

    item = metrics.snapshot().by_agent_metrics["reviewer"]

    assert item.total == 5
    assert item.succeeded == 1
    assert item.failed == 1
    assert item.rejected == 1
    assert item.cancelled == 1
    assert item.timed_out == 1


def test_agents_keep_status_retries_and_durations_isolated() -> None:
    metrics = InMemoryAgentExecutionMetrics()
    record(
        metrics,
        "zeta",
        AgentExecutionStatus.FAILED,
        execution_id="zeta-1",
        duration=3.5,
        retries=2,
    )
    record(
        metrics,
        "alpha",
        AgentExecutionStatus.SUCCEEDED,
        execution_id="alpha-1",
        duration=0.5,
    )

    snapshot = metrics.snapshot()

    assert list(snapshot.by_agent_metrics) == ["alpha", "zeta"]
    assert snapshot.by_agent_metrics["alpha"] == (
        PerAgentExecutionMetricsSnapshot(
            total=1,
            succeeded=1,
            failed=0,
            rejected=0,
            cancelled=0,
            timed_out=0,
            retries=0,
            duration_seconds=(0.5,),
        )
    )
    assert snapshot.by_agent_metrics["zeta"].failed == 1
    assert snapshot.by_agent_metrics["zeta"].retries == 2
    assert snapshot.by_agent_metrics["zeta"].duration_seconds == (3.5,)


def test_global_metrics_and_existing_counts_remain_compatible() -> None:
    metrics = InMemoryAgentExecutionMetrics()
    record(
        metrics,
        "alpha",
        AgentExecutionStatus.SUCCEEDED,
        execution_id="alpha-1",
        duration=0.25,
        retries=1,
    )
    record(
        metrics,
        "alpha",
        AgentExecutionStatus.REJECTED,
        execution_id="alpha-2",
        duration=0.75,
    )
    record(
        metrics,
        "zeta",
        AgentExecutionStatus.TIMED_OUT,
        execution_id="zeta-1",
        duration=2.0,
        retries=3,
    )

    snapshot = metrics.snapshot()

    assert snapshot.total == 3
    assert snapshot.succeeded == 1
    assert snapshot.failed == 0
    assert snapshot.rejected == 1
    assert snapshot.cancelled == 0
    assert snapshot.timed_out == 1
    assert snapshot.retries == 4
    assert snapshot.duration_seconds == (0.25, 0.75, 2.0)
    assert snapshot.by_agent == {"alpha": 2, "zeta": 1}
    assert snapshot.by_capability == {"review": 3}


def test_repeated_snapshots_are_deterministic_and_detached() -> None:
    metrics = InMemoryAgentExecutionMetrics()
    record(
        metrics,
        "zeta",
        AgentExecutionStatus.SUCCEEDED,
        execution_id="zeta-1",
        duration=1.0,
    )
    record(
        metrics,
        "alpha",
        AgentExecutionStatus.SUCCEEDED,
        execution_id="alpha-1",
        duration=2.0,
    )

    first = metrics.snapshot()
    second = metrics.snapshot()

    assert first == second
    assert list(first.by_agent) == ["alpha", "zeta"]
    assert list(first.by_agent_metrics) == ["alpha", "zeta"]
    first.by_agent_metrics.clear()
    assert list(metrics.snapshot().by_agent_metrics) == ["alpha", "zeta"]
