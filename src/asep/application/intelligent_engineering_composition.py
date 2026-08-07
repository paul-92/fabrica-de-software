"""Composition root do caso de uso Intelligent Engineering."""

from __future__ import annotations

from asep.application.intelligent_engineering import (
    IntelligentEngineeringApplicationService,
)
from asep.intelligence import (
    AutonomousEngineeringExecutor,
    IntelligentEngineeringService,
    KnowledgeAwarePlanningAdapter,
    KnowledgePlanningAdapter,
)
from asep.planning import Planner


def create_intelligent_engineering_application_service(
    planner: Planner,
    engineering: AutonomousEngineeringExecutor,
    planning_adapter: KnowledgePlanningAdapter | None = None,
) -> IntelligentEngineeringApplicationService:
    """Monta somente as dependências do caso de uso inteligente."""
    capability = IntelligentEngineeringService(
        planning_adapter or KnowledgeAwarePlanningAdapter(),
        planner,
        engineering,
    )
    return IntelligentEngineeringApplicationService(capability)


__all__ = ["create_intelligent_engineering_application_service"]
