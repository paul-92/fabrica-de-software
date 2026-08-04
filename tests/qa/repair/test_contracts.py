from __future__ import annotations

from asep.repair.contracts import (
    FailureAnalyzer,
    RepairExecutor,
    RepairPlanner,
)
from asep.repair.models import (
    FailureAnalysis,
    RepairChange,
    RepairPlan,
    RepairResult,
    RepairStatus,
)


class FakeFailureAnalyzer:
    def analyze(
        self,
        failure_output: str,
    ) -> FailureAnalysis:
        return FailureAnalysis(
            summary="Falha analisada.",
            failure_output=failure_output,
        )


class FakeRepairPlanner:
    def plan(
        self,
        analysis: FailureAnalysis,
    ) -> RepairPlan:
        return RepairPlan(
            analysis=analysis,
            changes=(
                RepairChange(
                    path="calculator.py",
                    content=(
                        "def add(a: int, b: int) -> int:\n"
                        "    return a + b\n"
                    ),
                    reason="Corrigir implementação.",
                ),
            ),
            test_paths=(
                "tests/test_calculator.py",
            ),
        )


class FakeRepairExecutor:
    def execute(
        self,
        plan: RepairPlan,
    ) -> RepairResult:
        return RepairResult(
            status=RepairStatus.SUCCEEDED,
            final_analysis=plan.analysis,
            messages=("Reparo executado.",),
        )


def test_failure_analyzer_contract_is_structural() -> None:
    analyzer: FailureAnalyzer = FakeFailureAnalyzer()

    result = analyzer.analyze(
        "assert -1 == 5"
    )

    assert isinstance(result, FailureAnalysis)
    assert result.failure_output == "assert -1 == 5"


def test_repair_planner_contract_is_structural() -> None:
    planner: RepairPlanner = FakeRepairPlanner()

    analysis = FailureAnalysis(
        summary="Falha funcional.",
    )

    plan = planner.plan(analysis)

    assert isinstance(plan, RepairPlan)
    assert plan.analysis == analysis
    assert len(plan.changes) == 1


def test_repair_executor_contract_is_structural() -> None:
    executor: RepairExecutor = FakeRepairExecutor()

    analysis = FailureAnalysis(
        summary="Falha funcional.",
    )

    plan = RepairPlan(
        analysis=analysis,
        changes=(
            RepairChange(
                path="calculator.py",
                content="",
                reason="Atualizar implementação.",
            ),
        ),
    )

    result = executor.execute(plan)

    assert isinstance(result, RepairResult)
    assert result.status is RepairStatus.SUCCEEDED