"""Métricas locais e injetáveis do runtime de agentes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from asep.agents.contracts import AgentCapability
from asep.agents.runtime_models import (
    AgentExecutionResult,
    AgentExecutionStatus,
)


@dataclass(frozen=True, slots=True)
class AgentExecutionMetricsSnapshot:
    total: int
    succeeded: int
    failed: int
    rejected: int
    cancelled: int
    timed_out: int
    retries: int
    duration_seconds: tuple[float, ...]
    by_agent: dict[str, int]
    by_capability: dict[str, int]


@runtime_checkable
class AgentExecutionMetricsRecorder(Protocol):
    def record(
        self,
        result: AgentExecutionResult,
        capability: AgentCapability,
        *,
        retries: int,
    ) -> None: ...


class InMemoryAgentExecutionMetrics:
    """Coletor simples; não substitui o MetricsService analítico de Runs."""

    def __init__(self) -> None:
        self._counts = {status: 0 for status in AgentExecutionStatus}
        self._total = 0
        self._retries = 0
        self._durations: list[float] = []
        self._by_agent: dict[str, int] = {}
        self._by_capability: dict[str, int] = {}

    def record(
        self,
        result: AgentExecutionResult,
        capability: AgentCapability,
        *,
        retries: int,
    ) -> None:
        self._total += 1
        self._counts[result.status] += 1
        self._retries += retries
        self._durations.append(result.duration_seconds)
        agent_id = result.agent_id.value
        self._by_agent[agent_id] = self._by_agent.get(agent_id, 0) + 1
        self._by_capability[capability.id] = (
            self._by_capability.get(capability.id, 0) + 1
        )

    def snapshot(self) -> AgentExecutionMetricsSnapshot:
        return AgentExecutionMetricsSnapshot(
            total=self._total,
            succeeded=self._counts[AgentExecutionStatus.SUCCEEDED],
            failed=self._counts[AgentExecutionStatus.FAILED],
            rejected=self._counts[AgentExecutionStatus.REJECTED],
            cancelled=self._counts[AgentExecutionStatus.CANCELLED],
            timed_out=self._counts[AgentExecutionStatus.TIMED_OUT],
            retries=self._retries,
            duration_seconds=tuple(self._durations),
            by_agent=dict(sorted(self._by_agent.items())),
            by_capability=dict(sorted(self._by_capability.items())),
        )


__all__ = [
    "AgentExecutionMetricsRecorder",
    "AgentExecutionMetricsSnapshot",
    "InMemoryAgentExecutionMetrics",
]
