from __future__ import annotations

from asep.repair import (
    ControlledRepairExecutor,
    DeterministicRepairPlanner,
    FailureAnalysis,
    FailureAnalyzer,
    PytestFailureAnalyzer,
    RepairAttempt,
    RepairChange,
    RepairExecutor,
    RepairPlan,
    RepairPlanner,
    RepairResult,
    RepairLoopContext,
    RepairLoopPolicy,
    RepairLoopService,
    RepairStatus,
)


def test_package_exports_public_api() -> None:
    assert ControlledRepairExecutor is not None
    assert DeterministicRepairPlanner is not None
    assert FailureAnalysis is not None
    assert FailureAnalyzer is not None
    assert PytestFailureAnalyzer is not None
    assert RepairAttempt is not None
    assert RepairChange is not None
    assert RepairExecutor is not None
    assert RepairPlan is not None
    assert RepairPlanner is not None
    assert RepairResult is not None
    assert RepairLoopContext is not None
    assert RepairLoopPolicy is not None
    assert RepairLoopService is not None
    assert RepairStatus is not None


def test_package_can_instantiate_analyzer() -> None:
    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(
        "FAILED tests/test_example.py::test_sample"
    )

    assert result.summary.startswith("FAILED")


def test_package_can_instantiate_planner() -> None:
    planner = DeterministicRepairPlanner()

    plan = planner.plan(
        FailureAnalysis(
            summary="Falha funcional.",
            affected_paths=("calculator.py",),
        )
    )

    assert plan.changes[0].path == "calculator.py"
