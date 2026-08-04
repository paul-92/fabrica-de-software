"""Composição linear das capacidades de AI Planning e Repair."""

from __future__ import annotations

from asep.ai_planning.contracts import (
    ReflectionEvaluator,
    RepairPlanGenerator,
    RepairProposalPlanner,
)
from asep.ai_planning.models import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
)
from asep.repair.contracts import RepairExecutor


class AutonomousEngineeringService:
    """Orquestra proposta, plano, execução e reflexão uma única vez."""

    def __init__(
        self,
        proposal_planner: RepairProposalPlanner,
        plan_generator: RepairPlanGenerator,
        repair_executor: RepairExecutor,
        reflection_evaluator: ReflectionEvaluator,
    ) -> None:
        self._proposal_planner = proposal_planner
        self._plan_generator = plan_generator
        self._repair_executor = repair_executor
        self._reflection_evaluator = reflection_evaluator

    def execute(
        self,
        request: AutonomousEngineeringRequest,
    ) -> AutonomousEngineeringResult:
        proposal = self._proposal_planner.propose(request.analysis)
        plan = self._plan_generator.generate(
            proposal,
            analysis=request.analysis,
            replacement_contents=request.replacement_contents,
            test_paths=request.test_paths,
        )
        repair_result = self._repair_executor.execute(plan)
        reflection = self._reflection_evaluator.evaluate(repair_result)

        return AutonomousEngineeringResult(
            proposal=proposal,
            plan=plan,
            repair_result=repair_result,
            reflection=reflection,
        )


__all__ = ["AutonomousEngineeringService"]

