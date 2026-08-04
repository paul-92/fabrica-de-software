"""Recuperação determinística de conhecimento aprendido."""

from __future__ import annotations

from collections.abc import Mapping

from asep.learning.models import (
    KnowledgeRetrievalRequest,
    LearnedKnowledgeContext,
)
from asep.memory import AgentMemory, MemoryCategory, MemoryEntry, MemoryQuery


class DeterministicKnowledgeRetriever:
    """Consulta AgentMemory e preserva apenas conhecimento aprendido válido."""

    def __init__(self, memory: AgentMemory) -> None:
        self._memory = memory

    def retrieve(
        self,
        request: KnowledgeRetrievalRequest,
    ) -> LearnedKnowledgeContext:
        expected_metadata = {"kind": "learned_knowledge"}
        if request.source_type is not None:
            expected_metadata["source_type"] = request.source_type

        candidates = self._memory.search(
            MemoryQuery(
                agent_id=request.agent_id,
                category=MemoryCategory.CUSTOM,
                text=request.text,
                metadata=expected_metadata,
            )
        )
        matches = tuple(
            entry
            for entry in candidates
            if self._is_match(entry, request)
        )
        return LearnedKnowledgeContext(
            entries=matches[: request.max_results],
            total_matches=len(matches),
        )

    @staticmethod
    def _is_match(
        entry: MemoryEntry,
        request: KnowledgeRetrievalRequest,
    ) -> bool:
        metadata: Mapping[str, object] = entry.metadata
        if entry.category is not MemoryCategory.CUSTOM:
            return False
        if metadata.get("kind") != "learned_knowledge":
            return False
        if (
            request.source_type is not None
            and metadata.get("source_type") != request.source_type
        ):
            return False
        if request.minimum_confidence is None:
            return True
        confidence = metadata.get("confidence")
        return (
            isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and float(confidence) >= request.minimum_confidence
        )


__all__ = ["DeterministicKnowledgeRetriever"]

