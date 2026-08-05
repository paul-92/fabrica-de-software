"""Composição determinística de contexto enriquecido."""

from __future__ import annotations

from typing import Mapping

from pydantic import JsonValue

from asep.intelligence.models import KnowledgeAwareContext
from asep.learning import LearnedKnowledgeContext


class DeterministicKnowledgeContextBuilder:
    """Combina dados sem interpretar ou executar o conhecimento."""

    def build(
        self,
        base_context: Mapping[str, JsonValue],
        learned_context: LearnedKnowledgeContext,
        *,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> KnowledgeAwareContext:
        return KnowledgeAwareContext(
            base_context=base_context,
            learned_entries=learned_context.entries,
            knowledge_count=len(learned_context.entries),
            metadata=metadata or {},
        )


__all__ = ["DeterministicKnowledgeContextBuilder"]

