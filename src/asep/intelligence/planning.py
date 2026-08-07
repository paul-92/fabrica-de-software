"""Adapta conhecimento aprendido para a fronteira de memória do Planning."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from asep.intelligence.models import KnowledgeAwareContext
from asep.planning import PlanningRequest
from asep.tools.contracts import Tool


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


class ToolAwarePlanningAdapter:
    """Fornece workflow operacional derivado de Tools reais registradas."""

    def __init__(
        self,
        delegate: KnowledgePlanningAdapter,
        tools: Iterable[Tool],
    ) -> None:
        self._delegate = delegate
        self._tools = tuple(tools)

    def adapt(
        self,
        request: PlanningRequest,
        knowledge_context: KnowledgeAwareContext,
    ) -> PlanningRequest:
        adapted = self._delegate.adapt(request, knowledge_context)
        if "steps" in adapted.context.workflow:
            return adapted

        steps = [
            {
                "id": f"{tool.metadata.id.value}-{capability.id}",
                "description": tool.metadata.description,
                "required_capability": capability.id,
                "tool": tool.metadata.id.value,
            }
            for tool in self._tools
            for capability in tool.metadata.capabilities
        ]
        workflow = {
            **dict(adapted.context.workflow),
            "steps": steps,
        }
        context = adapted.context.model_copy(update={"workflow": workflow})
        return adapted.model_copy(update={"context": context})


__all__ = [
    "KnowledgeAwarePlanningAdapter",
    "KnowledgePlanningAdapter",
    "ToolAwarePlanningAdapter",
]
