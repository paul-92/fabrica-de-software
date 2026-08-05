"""Fronteira pública do caso de uso Intelligent Engineering."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
)
from asep.application.contracts import IntelligentEngineeringCapability
from asep.intelligence import (
    IntelligentEngineeringRequest,
    KnowledgeAwareContext,
)
from asep.planning import PlanningRequest, PlanningResult


class ApplicationIntelligentEngineeringRequest(BaseModel):
    """Entrada estável do caso de uso na Application Layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planning_request: PlanningRequest
    knowledge_context: KnowledgeAwareContext
    engineering_request: AutonomousEngineeringRequest


class ApplicationIntelligentEngineeringResult(BaseModel):
    """Saída consolidada oferecida aos consumidores da aplicação."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planning_request: PlanningRequest
    planning_result: PlanningResult
    engineering_result: AutonomousEngineeringResult


class IntelligentEngineeringApplicationService:
    """Delega o caso de uso sem construir ou reimplementar infraestrutura."""

    def __init__(
        self,
        capability: IntelligentEngineeringCapability,
    ) -> None:
        self._capability = capability

    def execute(
        self,
        request: ApplicationIntelligentEngineeringRequest,
    ) -> ApplicationIntelligentEngineeringResult:
        internal_result = self._capability.execute(
            IntelligentEngineeringRequest(
                planning_request=request.planning_request,
                knowledge_context=request.knowledge_context,
                engineering_request=request.engineering_request,
            )
        )
        return ApplicationIntelligentEngineeringResult(
            planning_request=internal_result.planning_request,
            planning_result=internal_result.planning_result,
            engineering_result=internal_result.engineering_result,
        )


__all__ = [
    "ApplicationIntelligentEngineeringRequest",
    "ApplicationIntelligentEngineeringResult",
    "IntelligentEngineeringApplicationService",
]
