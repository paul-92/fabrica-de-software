"""Contratos públicos para composição de contexto com conhecimento."""

from __future__ import annotations

from typing import Mapping, Protocol

from pydantic import JsonValue

from asep.intelligence.models import KnowledgeAwareContext
from asep.learning import LearnedKnowledgeContext


class KnowledgeContextBuilder(Protocol):
    """Combina contexto explícito e conhecimento previamente recuperado."""

    def build(
        self,
        base_context: Mapping[str, JsonValue],
        learned_context: LearnedKnowledgeContext,
        *,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> KnowledgeAwareContext:
        ...


__all__ = ["KnowledgeContextBuilder"]

