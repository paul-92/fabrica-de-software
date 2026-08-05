from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from asep.agents import AgentId
from asep.ai_planning import DeterministicReflectionEvaluator
from asep.learning import (
    DeterministicKnowledgeRetriever,
    DeterministicLearningExtractor,
    KnowledgeRetrievalRequest,
    LearningRequest,
    LearningService,
)
from asep.memory import (
    InMemoryMemoryStore,
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
    MemoryService,
    SQLiteMemoryStore,
)
from asep.repair import RepairResult, RepairStatus
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
AGENT = AgentId(value="learning-agent")
OTHER_AGENT = AgentId(value="other-agent")


def memory_service(store) -> MemoryService:
    return MemoryService(
        store,
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
    )


def learning_request() -> LearningRequest:
    repair_result = RepairResult(
        status=RepairStatus.SUCCEEDED,
        messages=("A validação confirmou o reparo.",),
    )
    reflection = DeterministicReflectionEvaluator().evaluate(repair_result)
    return LearningRequest(
        repair_result=repair_result,
        reflection=reflection,
        source_execution_id="execution-a",
        source_type="autonomous_engineering",
        memory_id=MemoryId(value="knowledge-from-execution-a"),
        agent_id=AGENT,
        execution_id="learning-execution-a",
        workflow_execution_id="workflow-a",
        created_at=NOW,
        updated_at=NOW,
    )


def ordinary_memory() -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(value="ordinary-custom-memory"),
        agent_id=AGENT,
        execution_id="ordinary-execution",
        category=MemoryCategory.CUSTOM,
        importance=MemoryImportance.NORMAL,
        content="Memória customizada comum.",
        metadata={"kind": "ordinary_custom"},
        created_at=NOW,
        updated_at=NOW,
    )


def test_execution_knowledge_is_available_to_later_in_memory_context() -> None:
    store = InMemoryMemoryStore()
    execution_a_memory = memory_service(store)
    learning = LearningService(
        DeterministicLearningExtractor(),
        execution_a_memory,
    )

    learned = learning.learn(learning_request())
    execution_a_memory.save(ordinary_memory())

    later_memory = memory_service(store)
    retriever = DeterministicKnowledgeRetriever(later_memory)
    context = retriever.retrieve(KnowledgeRetrievalRequest(
        agent_id=AGENT,
        text="reparo",
        source_type="autonomous_engineering",
        minimum_confidence=0.9,
        max_results=1,
    ))

    assert context.entries == (learned.memory_entry,)
    recovered = context.entries[0]
    assert recovered.metadata["kind"] == "learned_knowledge"
    assert recovered.metadata["source_type"] == "autonomous_engineering"
    assert recovered.metadata["confidence"] == 0.95
    assert learned.learned_knowledge.summary in recovered.content
    assert "A validação confirmou o reparo." in recovered.content
    assert ordinary_memory() not in context.entries

    unrelated = retriever.retrieve(KnowledgeRetrievalRequest(
        agent_id=OTHER_AGENT,
    ))
    assert unrelated.entries == ()


def test_learned_knowledge_survives_distinct_sqlite_instances(
    tmp_path: Path,
) -> None:
    database = tmp_path / "learning.db"
    writer_memory = memory_service(SQLiteMemoryStore(database))
    learned = LearningService(
        DeterministicLearningExtractor(),
        writer_memory,
    ).learn(learning_request())

    reader_memory = memory_service(SQLiteMemoryStore(database))
    context = DeterministicKnowledgeRetriever(reader_memory).retrieve(
        KnowledgeRetrievalRequest(
            agent_id=AGENT,
            source_type="autonomous_engineering",
            minimum_confidence=0.95,
        )
    )

    assert len(context.entries) == 1
    assert context.entries[0] == learned.memory_entry
    assert context.entries[0].memory_id == MemoryId(
        value="knowledge-from-execution-a"
    )

