from __future__ import annotations

from pathlib import Path

from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
    AutonomousEngineeringService,
    EngineeringReflection,
    RepairProposal,
)
from asep.repair import (
    FailureAnalysis,
    RepairChange,
    RepairPlan,
    RepairResult,
    RepairStatus,
)


class ProposalPlannerFake:
    def __init__(self, proposal: RepairProposal) -> None:
        self.proposal = proposal
        self.received = []

    def propose(self, analysis: FailureAnalysis) -> RepairProposal:
        self.received.append(analysis)
        return self.proposal


class PlanGeneratorFake:
    def __init__(self, plan: RepairPlan) -> None:
        self.plan = plan
        self.calls = []

    def generate(
        self,
        proposal,
        *,
        analysis,
        replacement_contents,
        test_paths=("tests",),
    ) -> RepairPlan:
        self.calls.append(
            (proposal, analysis, replacement_contents, test_paths)
        )
        return self.plan


class RepairExecutorFake:
    def __init__(self, result: RepairResult) -> None:
        self.result = result
        self.received = []

    def execute(self, plan: RepairPlan) -> RepairResult:
        self.received.append(plan)
        return self.result


class ReflectionEvaluatorFake:
    def __init__(self, reflection: EngineeringReflection) -> None:
        self.reflection = reflection
        self.received = []

    def evaluate(self, result: RepairResult) -> EngineeringReflection:
        self.received.append(result)
        return self.reflection


def fixtures(status: RepairStatus):
    analysis = FailureAnalysis(summary="Falha funcional.")
    proposal = RepairProposal(
        summary="Proposta.",
        reasoning="Razão verificável.",
        candidate_files=("calculator.py",),
        suggested_actions=("Corrigir a operação.",),
        confidence=0.8,
    )
    plan = RepairPlan(
        analysis=analysis,
        changes=(RepairChange(
            path="calculator.py",
            content="replacement",
            reason="Corrigir a operação.",
        ),),
        test_paths=("qa/test_calculator.py",),
    )
    repair_result = RepairResult(status=status, final_analysis=analysis)
    reflection = EngineeringReflection(
        summary="Reflexão.",
        outcome=status,
        lessons=("Lição.",),
        recommended_actions=("Ação recomendada.",),
        should_retry=status is RepairStatus.FAILED,
        confidence=0.7,
    )
    return analysis, proposal, plan, repair_result, reflection


def execute_pipeline(status: RepairStatus):
    analysis, proposal, plan, repair_result, reflection = fixtures(status)
    planner = ProposalPlannerFake(proposal)
    generator = PlanGeneratorFake(plan)
    executor = RepairExecutorFake(repair_result)
    evaluator = ReflectionEvaluatorFake(reflection)
    service = AutonomousEngineeringService(
        planner, generator, executor, evaluator
    )
    request = AutonomousEngineeringRequest(
        analysis=analysis,
        replacement_contents={"calculator.py": "explicit replacement"},
        test_paths=("qa/test_calculator.py",),
    )
    result = service.execute(request)
    return result, request, planner, generator, executor, evaluator


def test_pipeline_consolidates_successful_execution() -> None:
    result, request, planner, generator, executor, evaluator = execute_pipeline(
        RepairStatus.SUCCEEDED
    )

    assert isinstance(result, AutonomousEngineeringResult)
    assert result.proposal is planner.proposal
    assert result.plan is generator.plan
    assert result.repair_result is executor.result
    assert result.reflection is evaluator.reflection
    assert result.reflection.should_retry is False
    assert planner.received == [request.analysis]


def test_pipeline_reflects_failed_result_without_retrying() -> None:
    result, _, planner, generator, executor, evaluator = execute_pipeline(
        RepairStatus.FAILED
    )

    assert result.reflection.should_retry is True
    assert len(planner.received) == 1
    assert len(generator.calls) == 1
    assert len(executor.received) == 1
    assert len(evaluator.received) == 1


def test_pipeline_passes_each_stage_to_the_next_component() -> None:
    result, request, planner, generator, executor, evaluator = execute_pipeline(
        RepairStatus.SUCCEEDED
    )

    generated = generator.calls[0]
    assert generated[0] is planner.proposal
    assert generated[1] is request.analysis
    assert generated[2] == request.replacement_contents
    assert generated[3] == request.test_paths
    assert executor.received == [result.plan]
    assert evaluator.received == [result.repair_result]


def test_pipeline_has_no_direct_effectful_dependencies() -> None:
    source = Path("src/asep/ai_planning/pipeline.py").read_text(
        encoding="utf-8"
    )

    assert "write_text" not in source
    assert "subprocess" not in source
    assert "Tool" not in source
    assert "RepairLoop" not in source

