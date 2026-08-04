"""Adaptação de conhecimento aprendido para a memória operacional."""

from __future__ import annotations

from datetime import datetime

from asep.agents import AgentId
from asep.learning.models import LearnedKnowledge
from asep.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
)


class LearnedKnowledgeMemoryAdapter:
    """Constrói MemoryEntry sem persistir ou consultar stores."""

    def adapt(
        self,
        knowledge: LearnedKnowledge,
        *,
        memory_id: MemoryId,
        agent_id: AgentId,
        execution_id: str,
        created_at: datetime,
        updated_at: datetime,
        workflow_execution_id: str | None = None,
    ) -> MemoryEntry:
        content = self._content(knowledge)
        metadata = {
            **dict(knowledge.metadata),
            "kind": "learned_knowledge",
            "source_type": knowledge.source_type,
            "confidence": knowledge.confidence,
        }

        return MemoryEntry(
            memory_id=memory_id,
            agent_id=agent_id,
            execution_id=execution_id,
            workflow_execution_id=workflow_execution_id,
            category=MemoryCategory.CUSTOM,
            importance=MemoryImportance.NORMAL,
            content=content,
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _content(knowledge: LearnedKnowledge) -> str:
        lessons = "\n".join(f"- {item}" for item in knowledge.lessons)
        actions = "\n".join(
            f"- {item}" for item in knowledge.recommended_actions
        )
        return (
            f"Resumo: {knowledge.summary}\n"
            f"Lições:\n{lessons}\n"
            f"Ações recomendadas:\n{actions}"
        )


__all__ = ["LearnedKnowledgeMemoryAdapter"]

