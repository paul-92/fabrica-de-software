"""Read-only public projection of provable agent runtime facts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.agents import AgentRegistry


class AgentRuntimeProjection(BaseModel):
    """Minimal public facts; no health or availability is inferred."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    registered: bool
    execution_count: int = Field(ge=0)
    succeeded: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    cancelled: int = Field(default=0, ge=0)
    timed_out: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)

    @field_validator("agent_id")
    @classmethod
    def agent_id_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("agent_id must not be blank")
        return value


@runtime_checkable
class PerAgentRuntimeMetricsSnapshot(Protocol):
    """Counters approved for the public per-agent projection."""

    @property
    def succeeded(self) -> int: ...

    @property
    def failed(self) -> int: ...

    @property
    def rejected(self) -> int: ...

    @property
    def cancelled(self) -> int: ...

    @property
    def timed_out(self) -> int: ...

    @property
    def retries(self) -> int: ...


@runtime_checkable
class AgentRuntimeMetricsSnapshot(Protocol):
    """Narrow view of the existing agent execution metrics snapshot."""

    @property
    def by_agent(self) -> Mapping[str, int]: ...

    @property
    def by_agent_metrics(
        self,
    ) -> Mapping[str, PerAgentRuntimeMetricsSnapshot]: ...


@runtime_checkable
class AgentRuntimeMetricsSource(Protocol):
    """Read-only metrics source used by the Application boundary."""

    def snapshot(self) -> AgentRuntimeMetricsSnapshot: ...


class AgentRuntimeProjectionService:
    def __init__(
        self,
        registry: AgentRegistry,
        metrics: AgentRuntimeMetricsSource,
    ) -> None:
        self._registry = registry
        self._metrics = metrics

    def list_agents(self) -> tuple[AgentRuntimeProjection, ...]:
        snapshot = self._metrics.snapshot()
        counts = snapshot.by_agent
        details = snapshot.by_agent_metrics
        return tuple(
            self._project(agent.metadata.id.value, counts, details)
            for agent in self._registry.list_all()
        )

    @staticmethod
    def _project(
        agent_id: str,
        counts: Mapping[str, int],
        details: Mapping[str, PerAgentRuntimeMetricsSnapshot],
    ) -> AgentRuntimeProjection:
        detail = details.get(agent_id)
        return AgentRuntimeProjection(
            agent_id=agent_id,
            registered=True,
            execution_count=counts.get(agent_id, 0),
            succeeded=detail.succeeded if detail is not None else 0,
            failed=detail.failed if detail is not None else 0,
            rejected=detail.rejected if detail is not None else 0,
            cancelled=detail.cancelled if detail is not None else 0,
            timed_out=detail.timed_out if detail is not None else 0,
            retries=detail.retries if detail is not None else 0,
        )


__all__ = [
    "AgentRuntimeMetricsSnapshot",
    "AgentRuntimeMetricsSource",
    "AgentRuntimeProjection",
    "AgentRuntimeProjectionService",
    "PerAgentRuntimeMetricsSnapshot",
]
