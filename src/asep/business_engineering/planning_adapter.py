"""Adaptador entre Business Engineering e Planning."""

from __future__ import annotations

from asep.business_engineering.contracts import PlanningAdapter
from asep.business_engineering.models import ProjectBlueprint
from asep.planning import (
    PlanningContext,
    PlanningEngine,
    PlanningRequest,
    PlanningResult,
)


class PlanningEngineAdapter(PlanningAdapter):
    """Converte ProjectBlueprint em PlanningRequest e aciona o Planning."""

    def __init__(self, planning_engine: PlanningEngine) -> None:
        self._planning_engine = planning_engine

    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> PlanningResult:
        """Cria um plano de execução a partir de um ProjectBlueprint."""

        workflow_steps = [
            {
                "id": requirement.id,
                "description": requirement.description,
                "required_capability": "implement_requirement",
            }
            for requirement in blueprint.requirements
        ]

        request = PlanningRequest(
            goal=blueprint.description,
            context=PlanningContext(
                objective=blueprint.project_name,
                workflow={
                    "steps": workflow_steps,
                },
                constraints=tuple(
                    constraint.description
                    for constraint in blueprint.constraints
                ),
                metadata={
                    "project_name": blueprint.project_name,
                },
            ),
            metadata={
                "project_name": blueprint.project_name,
                "requirement_count": len(blueprint.requirements),
            },
        )

        return self._planning_engine.plan(request)


__all__ = [
    "PlanningEngineAdapter",
]