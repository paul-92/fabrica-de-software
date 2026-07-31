"""Adaptador entre Planning e Agent Coordination."""

from __future__ import annotations

from asep.agents.coordination.coordinator import AgentCoordinator
from asep.agents.coordination.models import (
    CoordinationContext,
    CoordinationResult,
)
from asep.planning import PlanningResult


class AgentCoordinatorAdapter:
    """Converte um PlanningResult em CoordinationContext."""

    def __init__(
        self,
        coordinator: AgentCoordinator,
    ) -> None:
        self._coordinator = coordinator

    def coordinate(
        self,
        planning_result: PlanningResult,
    ) -> CoordinationResult:
        """Coordena um PlanningResult."""

        context = CoordinationContext(
            execution_plan=planning_result.plan,
            metadata={
                **dict(planning_result.plan.metadata),
                "plan_id": planning_result.plan.plan_id,
                "planning_warnings": list(planning_result.warnings),
                "planning_validation_messages": list(
                    planning_result.validation_messages
                ),
            },
        )

        return self._coordinator.coordinate(context)


__all__ = [
    "AgentCoordinatorAdapter",
]