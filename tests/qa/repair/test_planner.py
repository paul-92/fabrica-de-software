from __future__ import annotations

from asep.repair.models import FailureAnalysis
from asep.repair.planner import DeterministicRepairPlanner


def test_planner_creates_change_for_each_affected_path() -> None:
    planner = DeterministicRepairPlanner()

    analysis = FailureAnalysis(
        summary="Falha funcional.",
        affected_paths=(
            "src/calculator.py",
            "tests/test_calculator.py",
        ),
    )

    plan = planner.plan(analysis)

    assert plan.analysis == analysis
    assert len(plan.changes) == 2

    assert plan.changes[0].path == "src/calculator.py"
    assert plan.changes[1].path == "tests/test_calculator.py"


def test_planner_creates_placeholder_when_no_path_exists() -> None:
    planner = DeterministicRepairPlanner()

    analysis = FailureAnalysis(
        summary="Falha sem arquivos.",
    )

    plan = planner.plan(analysis)

    assert len(plan.changes) == 1
    assert plan.changes[0].path == "<unknown>"


def test_planner_preserves_default_test_path() -> None:
    planner = DeterministicRepairPlanner()

    analysis = FailureAnalysis(
        summary="Falha.",
        affected_paths=("src/example.py",),
    )

    plan = planner.plan(analysis)

    assert plan.test_paths == ("tests",)


def test_planner_preserves_analysis_reference() -> None:
    planner = DeterministicRepairPlanner()

    analysis = FailureAnalysis(
        summary="Resumo",
        probable_cause="AssertionError",
    )

    plan = planner.plan(analysis)

    assert plan.analysis is analysis