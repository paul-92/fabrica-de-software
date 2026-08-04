"""Contratos públicos para extração de conhecimento reutilizável."""

from __future__ import annotations

from typing import Protocol

from asep.ai_planning import EngineeringReflection
from asep.learning.models import LearnedKnowledge
from asep.repair import RepairResult

LearningSource = EngineeringReflection | RepairResult


class LearningExtractor(Protocol):
    """Decide o conhecimento estruturado extraído de uma execução."""

    def extract(
        self,
        source: LearningSource,
        *,
        source_execution_id: str,
        source_type: str,
    ) -> LearnedKnowledge:
        ...


__all__ = [
    "LearningExtractor",
    "LearningSource",
]

