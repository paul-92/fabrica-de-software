"""Composição controlada de Planning e Autonomous Engineering."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
)
from asep.intelligence.models import KnowledgeAwareContext
from asep.intelligence.planning import KnowledgePlanningAdapter
from asep.planning import Planner, PlanningRequest, PlanningResult


class AutonomousEngineeringExecutor(Protocol):
    """Porta mínima para o pipeline autônomo existente."""

    def execute(
        self,
        request: AutonomousEngineeringRequest,
    ) -> AutonomousEngineeringResult: ...


class IntelligentEngineeringRequest(BaseModel):
    """Entradas explícitas dos dois subsistemas compostos."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planning_request: PlanningRequest
    knowledge_context: KnowledgeAwareContext
    engineering_request: AutonomousEngineeringRequest


class IntelligentEngineeringResult(BaseModel):
    """Resultados preservados da composição, sem fusão de domínios."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planning_request: PlanningRequest
    planning_result: PlanningResult
    engineering_result: AutonomousEngineeringResult


class IntelligentEngineeringService:
    """Executa Planning e Autonomous Engineering uma única vez cada."""

    def __init__(
        self,
        planning_adapter: KnowledgePlanningAdapter,
        planner: Planner,
        engineering: AutonomousEngineeringExecutor,
    ) -> None:
        self._planning_adapter = planning_adapter
        self._planner = planner
        self._engineering = engineering

    def execute(
        self,
        request: IntelligentEngineeringRequest,
    ) -> IntelligentEngineeringResult:
        planning_request = self._planning_adapter.adapt(
            request.planning_request,
            request.knowledge_context,
        )
        planning_result = self._planner.plan(planning_request)
        engineering_result = self._engineering.execute(
            request.engineering_request
        )
        return IntelligentEngineeringResult(
            planning_request=planning_request,
            planning_result=planning_result,
            engineering_result=engineering_result,
        )


__all__ = [
    "AutonomousEngineeringExecutor",
    "IntelligentEngineeringRequest",
    "IntelligentEngineeringResult",
    "IntelligentEngineeringService",
]
