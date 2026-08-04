"""Contratos públicos para extração de conhecimento reutilizável."""

from __future__ import annotations

from typing import Protocol

from asep.ai_planning import EngineeringReflection
from asep.learning.models import (
    KnowledgeRetrievalRequest,
    LearnedKnowledge,
    LearnedKnowledgeContext,
)
from asep.repair import RepairResult


class LearningExtractor(Protocol):
    """Decide o conhecimento estruturado extraído de uma execução."""

    def extract(
        self,
        repair_result: RepairResult,
        reflection: EngineeringReflection,
        *,
        source_execution_id: str,
        source_type: str,
    ) -> LearnedKnowledge:
        ...


class KnowledgeRetriever(Protocol):
    """Recupera conhecimento aprendido pela infraestrutura de memória."""

    def retrieve(
        self,
        request: KnowledgeRetrievalRequest,
    ) -> LearnedKnowledgeContext:
        ...


__all__ = [
    "KnowledgeRetriever",
    "LearningExtractor",
]
