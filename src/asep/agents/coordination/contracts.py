"""Portas da coordenação multiagente."""

from typing import Protocol, runtime_checkable

from asep.agents.contracts import AgentId
from asep.agents.coordination.models import (
    AgentAssignment,
    CoordinationContext,
    CoordinationResult,
)
from asep.planning.models import PlanStep


@runtime_checkable
class AgentCapabilityResolver(Protocol):
    def resolve(self, step: PlanStep) -> AgentId: ...


@runtime_checkable
class AgentExecutionResultAggregator(Protocol):
    def aggregate(
        self,
        context: CoordinationContext,
        assignments: tuple[AgentAssignment, ...],
    ) -> CoordinationResult: ...


@runtime_checkable
class Coordinator(Protocol):
    def coordinate(self, context: CoordinationContext) -> CoordinationResult:
        ...


__all__ = [
    "AgentCapabilityResolver",
    "AgentExecutionResultAggregator",
    "Coordinator",
]
