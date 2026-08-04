"""Avaliação determinística de resultados de reparo."""

from __future__ import annotations

from asep.ai_planning.models import EngineeringReflection
from asep.repair.models import RepairResult, RepairStatus


class DeterministicReflectionEvaluator:
    """Produz reflexão estruturada a partir de estados terminais conhecidos."""

    def evaluate(self, result: RepairResult) -> EngineeringReflection:
        lessons = result.messages or self._default_lessons(result.status)

        if result.status is RepairStatus.SUCCEEDED:
            return EngineeringReflection(
                summary="O reparo foi concluído e validado com sucesso.",
                outcome=result.status,
                lessons=lessons,
                recommended_actions=(
                    "Preservar a validação que comprovou o reparo.",
                ),
                should_retry=False,
                confidence=0.95,
            )

        if result.status is RepairStatus.FAILED:
            return EngineeringReflection(
                summary="A tentativa de reparo falhou antes da conclusão.",
                outcome=result.status,
                lessons=lessons,
                recommended_actions=(
                    "Reavaliar a análise e produzir um plano diferente.",
                ),
                should_retry=True,
                confidence=0.7,
            )

        if result.status is RepairStatus.EXHAUSTED:
            return EngineeringReflection(
                summary="O limite de tentativas de reparo foi esgotado.",
                outcome=result.status,
                lessons=lessons,
                recommended_actions=(
                    "Encaminhar o diagnóstico para revisão humana.",
                ),
                should_retry=False,
                confidence=0.9,
            )

        raise ValueError(
            f"RepairStatus não suportado para reflexão: {result.status.value}"
        )

    @staticmethod
    def _default_lessons(status: RepairStatus) -> tuple[str, ...]:
        return (f"O processo terminou com status {status.value}.",)


__all__ = ["DeterministicReflectionEvaluator"]

