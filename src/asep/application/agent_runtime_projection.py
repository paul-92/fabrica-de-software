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

    @field_validator("agent_id")
    @classmethod
    def agent_id_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("agent_id must not be blank")
        return value


@runtime_checkable
class AgentRuntimeMetricsSnapshot(Protocol):
    """Narrow view of the existing agent execution metrics snapshot."""

    @property
    def by_agent(self) -> Mapping[str, int]: ...


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
        counts = self._metrics.snapshot().by_agent
        return tuple(
            AgentRuntimeProjection(
                agent_id=agent.metadata.id.value,
                registered=True,
                execution_count=counts.get(agent.metadata.id.value, 0),
            )
            for agent in self._registry.list_all()
        )


__all__ = [
    "AgentRuntimeMetricsSnapshot",
    "AgentRuntimeMetricsSource",
    "AgentRuntimeProjection",
    "AgentRuntimeProjectionService",
]
