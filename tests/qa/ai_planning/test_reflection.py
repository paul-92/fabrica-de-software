from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.ai_planning import (
    DeterministicReflectionEvaluator,
    EngineeringReflection,
    ReflectionEvaluator,
)
from asep.repair import RepairResult, RepairStatus


def result(status: RepairStatus, *messages: str) -> RepairResult:
    return RepairResult(status=status, messages=messages)


@pytest.mark.parametrize(
    ("status", "should_retry"),
    [
        (RepairStatus.SUCCEEDED, False),
        (RepairStatus.FAILED, True),
        (RepairStatus.EXHAUSTED, False),
    ],
)
def test_reflection_distinguishes_terminal_outcomes(
    status: RepairStatus,
    should_retry: bool,
) -> None:
    reflection = DeterministicReflectionEvaluator().evaluate(
        result(status, "Mensagem relevante do reparo.")
    )

    assert reflection.outcome is status
    assert reflection.should_retry is should_retry
    assert 0.0 <= reflection.confidence <= 1.0
    assert reflection.lessons == ("Mensagem relevante do reparo.",)


def test_success_reflection_recommends_preserving_validation() -> None:
    reflection = DeterministicReflectionEvaluator().evaluate(
        result(RepairStatus.SUCCEEDED)
    )

    assert "sucesso" in reflection.summary
    assert "validação" in reflection.recommended_actions[0]


def test_failed_reflection_recommends_a_different_plan() -> None:
    reflection = DeterministicReflectionEvaluator().evaluate(
        result(RepairStatus.FAILED)
    )

    assert reflection.should_retry is True
    assert "plano diferente" in reflection.recommended_actions[0]


def test_exhausted_reflection_recommends_human_review() -> None:
    reflection = DeterministicReflectionEvaluator().evaluate(
        result(RepairStatus.EXHAUSTED)
    )

    assert reflection.should_retry is False
    assert "revisão humana" in reflection.recommended_actions[0]


def test_engineering_reflection_is_immutable() -> None:
    reflection = DeterministicReflectionEvaluator().evaluate(
        result(RepairStatus.SUCCEEDED)
    )

    with pytest.raises(ValidationError):
        reflection.should_retry = True


def test_engineering_reflection_validates_confidence() -> None:
    with pytest.raises(ValidationError):
        EngineeringReflection(
            summary="Resultado.",
            outcome=RepairStatus.FAILED,
            lessons=("Lição.",),
            recommended_actions=("Ação.",),
            should_retry=True,
            confidence=1.1,
        )


def test_reflection_evaluator_satisfies_public_protocol() -> None:
    evaluator: ReflectionEvaluator = DeterministicReflectionEvaluator()

    reflection = evaluator.evaluate(result(RepairStatus.SUCCEEDED))

    assert isinstance(reflection, EngineeringReflection)


def test_reflection_rejects_non_terminal_repair_status() -> None:
    with pytest.raises(ValueError, match="não suportado"):
        DeterministicReflectionEvaluator().evaluate(
            result(RepairStatus.APPLYING)
        )


def test_reflection_has_no_effectful_dependencies() -> None:
    source = Path("src/asep/ai_planning/reflection.py").read_text(
        encoding="utf-8"
    )

    assert "write_text" not in source
    assert "subprocess" not in source
    assert "Tool" not in source

