from __future__ import annotations

from datetime import UTC, datetime

from asep.agents import AgentId
from asep.learning import LearnedKnowledge, LearnedKnowledgeMemoryAdapter
from asep.memory import MemoryCategory, MemoryId, MemoryImportance


def test_adapter_converts_learned_knowledge_to_custom_memory() -> None:
    knowledge = LearnedKnowledge(
        summary="Testes devem acompanhar reparos.",
        lessons=("O teste vermelho identificou a regressão.",),
        recommended_actions=("Manter o teste de regressão.",),
        source_execution_id="repair-7",
        source_type="repair_result",
        confidence=0.8,
        metadata={"kind": "cannot_override", "scope": "calculator"},
    )
    timestamp = datetime(2026, 8, 4, 12, tzinfo=UTC)

    entry = LearnedKnowledgeMemoryAdapter().adapt(
        knowledge,
        memory_id=MemoryId(value="memory-1"),
        agent_id=AgentId(value="learning-agent"),
        execution_id="memory-execution-1",
        workflow_execution_id="workflow-1",
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert entry.category is MemoryCategory.CUSTOM
    assert entry.importance is MemoryImportance.NORMAL
    assert entry.metadata["kind"] == "learned_knowledge"
    assert entry.metadata["source_type"] == "repair_result"
    assert entry.metadata["confidence"] == 0.8
    assert entry.metadata["scope"] == "calculator"
    assert entry.execution_id == "memory-execution-1"
    assert entry.created_at == timestamp
    assert "Testes devem acompanhar reparos." in entry.content
    assert "Manter o teste de regressão." in entry.content

