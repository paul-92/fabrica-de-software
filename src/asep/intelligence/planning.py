"""Adapta conhecimento aprendido para a fronteira de memória do Planning."""

from __future__ import annotations

from typing import Protocol

from asep.intelligence.models import KnowledgeAwareContext
from asep.planning import PlanningRequest


class KnowledgePlanningAdapter(Protocol):
    """Contrato para enriquecer uma requisição de planejamento."""

    def adapt(
        self,
        request: PlanningRequest,
        knowledge_context: KnowledgeAwareContext,
    ) -> PlanningRequest: ...


class KnowledgeAwarePlanningAdapter:
    """Combina memórias existentes e aprendidas sem interpretá-las."""

    def adapt(
        self,
        request: PlanningRequest,
        knowledge_context: KnowledgeAwareContext,
    ) -> PlanningRequest:
        memories = list(request.context.memory)
        known_ids = {entry.memory_id for entry in memories}

        for entry in knowledge_context.learned_entries:
            if entry.memory_id not in known_ids:
                memories.append(entry)
                known_ids.add(entry.memory_id)

        context = request.context.model_copy(
            update={"memory": tuple(memories)}
        )
        return request.model_copy(update={"context": context})


__all__ = [
    "KnowledgeAwarePlanningAdapter",
    "KnowledgePlanningAdapter",
]
