from __future__ import annotations

import pytest

from asep.repair import (
    FailureAnalysis,
    RepairAttempt,
    RepairChange,
    RepairLoopContext,
    RepairLoopPolicy,
    RepairLoopService,
    RepairPlan,
    RepairResult,
    RepairStatus,
)


class CountingPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def plan(self, analysis: FailureAnalysis) -> RepairPlan:
        self.calls += 1
        return RepairPlan(
            analysis=analysis,
            changes=(RepairChange(path="app.py", content="fixed", reason="repair"),),
        )


class SequenceExecutor:
    def __init__(self, statuses, *, raises=False) -> None:
        self.statuses = iter(statuses)
        self.calls = 0
        self.raises = raises

    def execute(self, plan: RepairPlan) -> RepairResult:
        self.calls += 1
        if self.raises:
            raise RuntimeError("operational failure")
        status = next(self.statuses)
        return RepairResult(
            status=status,
            attempts=(RepairAttempt(attempt=1, plan=plan, status=status),),
            final_analysis=plan.analysis,
            messages=(f"attempt {self.calls}",),
        )


def context(max_attempts: int = 3) -> RepairLoopContext:
    return RepairLoopContext(
        initial_analysis=FailureAnalysis(summary="Falha."),
        policy=RepairLoopPolicy(max_attempts=max_attempts),
    )


def test_loop_succeeds_on_first_attempt() -> None:
    planner, executor = CountingPlanner(), SequenceExecutor([RepairStatus.SUCCEEDED])
    result = RepairLoopService(planner, executor).execute(context())
    assert result.status is RepairStatus.SUCCEEDED
    assert planner.calls == executor.calls == 1
    assert [item.attempt for item in result.attempts] == [1]


def test_loop_succeeds_after_failure_and_preserves_history() -> None:
    planner = CountingPlanner()
    executor = SequenceExecutor([RepairStatus.FAILED, RepairStatus.SUCCEEDED])
    result = RepairLoopService(planner, executor).execute(context())
    assert result.status is RepairStatus.SUCCEEDED
    assert planner.calls == executor.calls == 2
    assert [item.status for item in result.attempts] == [
        RepairStatus.FAILED, RepairStatus.SUCCEEDED
    ]
    assert [item.attempt for item in result.attempts] == [1, 2]


def test_loop_returns_exhausted_at_exact_limit() -> None:
    planner = CountingPlanner()
    executor = SequenceExecutor([RepairStatus.FAILED] * 3)
    result = RepairLoopService(planner, executor).execute(context(3))
    assert result.status is RepairStatus.EXHAUSTED
    assert planner.calls == executor.calls == 3
    assert len(result.attempts) == 3


def test_loop_propagates_operational_exception() -> None:
    with pytest.raises(RuntimeError, match="operational failure"):
        RepairLoopService(CountingPlanner(), SequenceExecutor([], raises=True)).execute(
            context()
        )


def test_loop_policy_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError):
        RepairLoopPolicy(max_attempts=0)

