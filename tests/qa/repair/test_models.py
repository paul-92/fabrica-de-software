from __future__ import annotations

import pytest
from pydantic import ValidationError

from asep.repair.models import (
    FailureAnalysis,
    RepairAttempt,
    RepairChange,
    RepairPlan,
    RepairResult,
    RepairStatus,
)


def test_failure_analysis_accepts_minimal_valid_data() -> None:
    analysis = FailureAnalysis(
        summary="Teste da calculadora falhou.",
        failure_output="assert -1 == 5",
        affected_paths=(
            "calculator.py",
            "tests/test_calculator.py",
        ),
        probable_cause="Operador incorreto na função add.",
    )

    assert analysis.summary == "Teste da calculadora falhou."
    assert analysis.affected_paths == (
        "calculator.py",
        "tests/test_calculator.py",
    )


def test_repair_change_requires_path_and_reason() -> None:
    with pytest.raises(ValidationError):
        RepairChange(
            path="",
            content="return a + b",
            reason="Corrigir soma.",
        )

    with pytest.raises(ValidationError):
        RepairChange(
            path="calculator.py",
            content="return a + b",
            reason="",
        )


def test_repair_plan_requires_at_least_one_change() -> None:
    analysis = FailureAnalysis(
        summary="Falha funcional.",
    )

    with pytest.raises(ValidationError):
        RepairPlan(
            analysis=analysis,
            changes=(),
        )


def test_repair_plan_preserves_explicit_changes_and_tests() -> None:
    analysis = FailureAnalysis(
        summary="Implementação incorreta.",
        probable_cause="Operador de subtração usado no lugar de soma.",
    )

    change = RepairChange(
        path="calculator.py",
        content=(
            "def add(a: int, b: int) -> int:\n"
            "    return a + b\n"
        ),
        reason="Corrigir implementação da soma.",
    )

    plan = RepairPlan(
        analysis=analysis,
        changes=(change,),
        test_paths=(
            "tests/test_calculator.py",
        ),
    )

    assert plan.changes == (change,)
    assert plan.test_paths == (
        "tests/test_calculator.py",
    )


def test_repair_attempt_tracks_plan_and_status() -> None:
    plan = RepairPlan(
        analysis=FailureAnalysis(
            summary="Falha funcional.",
        ),
        changes=(
            RepairChange(
                path="calculator.py",
                content="",
                reason="Atualizar implementação.",
            ),
        ),
    )

    attempt = RepairAttempt(
        attempt=1,
        plan=plan,
        status=RepairStatus.APPLYING,
        messages=("Aplicando alteração.",),
    )

    assert attempt.attempt == 1
    assert attempt.status is RepairStatus.APPLYING
    assert attempt.messages == (
        "Aplicando alteração.",
    )


def test_repair_attempt_rejects_invalid_attempt_number() -> None:
    plan = RepairPlan(
        analysis=FailureAnalysis(
            summary="Falha funcional.",
        ),
        changes=(
            RepairChange(
                path="calculator.py",
                content="",
                reason="Atualizar implementação.",
            ),
        ),
    )

    with pytest.raises(ValidationError):
        RepairAttempt(
            attempt=0,
            plan=plan,
        )


def test_repair_result_can_represent_success() -> None:
    analysis = FailureAnalysis(
        summary="Falha corrigida.",
    )

    plan = RepairPlan(
        analysis=analysis,
        changes=(
            RepairChange(
                path="calculator.py",
                content="",
                reason="Corrigir implementação.",
            ),
        ),
    )

    attempt = RepairAttempt(
        attempt=1,
        plan=plan,
        status=RepairStatus.SUCCEEDED,
    )

    result = RepairResult(
        status=RepairStatus.SUCCEEDED,
        attempts=(attempt,),
        final_analysis=analysis,
        messages=("Reparo concluído.",),
    )

    assert result.status is RepairStatus.SUCCEEDED
    assert result.attempts == (attempt,)
    assert result.final_analysis is analysis


def test_repair_models_are_frozen() -> None:
    analysis = FailureAnalysis(
        summary="Falha funcional.",
    )

    with pytest.raises(ValidationError):
        analysis.summary = "Alterado"