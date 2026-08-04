"""Extração determinística de conhecimento a partir de reparos."""

from __future__ import annotations

from asep.ai_planning import EngineeringReflection
from asep.learning.models import LearnedKnowledge
from asep.repair import RepairResult


class DeterministicLearningExtractor:
    """Preserva fatos estruturados do resultado e da reflexão recebidos."""

    def extract(
        self,
        repair_result: RepairResult,
        reflection: EngineeringReflection,
        *,
        source_execution_id: str,
        source_type: str,
    ) -> LearnedKnowledge:
        return LearnedKnowledge(
            summary=reflection.summary,
            lessons=reflection.lessons,
            recommended_actions=reflection.recommended_actions,
            source_execution_id=source_execution_id,
            source_type=source_type,
            confidence=reflection.confidence,
            metadata={
                "repair_status": repair_result.status.value,
                "attempt_count": len(repair_result.attempts),
                "should_retry": reflection.should_retry,
            },
        )


__all__ = ["DeterministicLearningExtractor"]

