"""Serviço de aplicação para aprendizado a partir de execuções."""

from __future__ import annotations

from asep.learning.adapter import LearnedKnowledgeMemoryAdapter
from asep.learning.contracts import LearningExtractor
from asep.learning.models import LearningRequest, LearningResult
from asep.memory import AgentMemory


class LearningService:
    """Extrai, adapta e persiste conhecimento pela porta de memória."""

    def __init__(
        self,
        extractor: LearningExtractor,
        memory: AgentMemory,
        *,
        adapter: LearnedKnowledgeMemoryAdapter | None = None,
    ) -> None:
        self._extractor = extractor
        self._adapter = adapter or LearnedKnowledgeMemoryAdapter()
        self._memory = memory

    def learn(self, request: LearningRequest) -> LearningResult:
        knowledge = self._extractor.extract(
            request.repair_result,
            request.reflection,
            source_execution_id=request.source_execution_id,
            source_type=request.source_type,
        )
        entry = self._adapter.adapt(
            knowledge,
            memory_id=request.memory_id,
            agent_id=request.agent_id,
            execution_id=request.execution_id,
            workflow_execution_id=request.workflow_execution_id,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        persisted = self._memory.save(entry)
        return LearningResult(
            learned_knowledge=knowledge,
            memory_entry=persisted,
        )


__all__ = ["LearningService"]

