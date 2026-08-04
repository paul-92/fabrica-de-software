from __future__ import annotations

from datetime import UTC, datetime, timedelta

from asep.agents import AgentId
from asep.learning import (
    DeterministicKnowledgeRetriever,
    KnowledgeRetrievalRequest,
    KnowledgeRetriever,
    LearnedKnowledgeContext,
)
from asep.memory import (
    InMemoryMemoryStore,
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
    MemoryService,
)
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder


NOW = datetime(2026, 8, 4, 16, tzinfo=UTC)
AGENT = AgentId(value="learning-agent")


def entry(
    memory_id: str,
    *,
    agent_id: AgentId = AGENT,
    category: MemoryCategory = MemoryCategory.CUSTOM,
    kind: str = "learned_knowledge",
    source_type: str = "repair_reflection",
    confidence=0.8,
    created_offset: int = 0,
    content: str = "Conhecimento sobre reparo.",
) -> MemoryEntry:
    timestamp = NOW + timedelta(seconds=created_offset)
    return MemoryEntry(
        memory_id=MemoryId(value=memory_id),
        agent_id=agent_id,
        execution_id=f"execution-{memory_id}",
        category=category,
        importance=MemoryImportance.NORMAL,
        content=content,
        metadata={
            "kind": kind,
            "source_type": source_type,
            "confidence": confidence,
        },
        created_at=timestamp,
        updated_at=timestamp,
    )


def memory_service(*entries: MemoryEntry) -> MemoryService:
    service = MemoryService(
        InMemoryMemoryStore(),
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
    )
    for item in entries:
        service.save(item)
    return service


def retrieve(memory, **changes) -> LearnedKnowledgeContext:
    values = {"agent_id": AGENT}
    values.update(changes)
    return DeterministicKnowledgeRetriever(memory).retrieve(
        KnowledgeRetrievalRequest(**values)
    )


def test_retriever_returns_only_learned_custom_memory_for_agent() -> None:
    other_agent = AgentId(value="other-agent")
    learned = entry("learned")
    context = retrieve(memory_service(
        learned,
        entry("fact", category=MemoryCategory.FACT),
        entry("other-custom", kind="other_kind"),
        entry("other-agent", agent_id=other_agent),
    ))

    assert context.entries == (learned,)
    assert context.total_matches == 1


def test_retriever_filters_source_type_and_minimum_confidence() -> None:
    accepted = entry("accepted", confidence=0.9)
    context = retrieve(
        memory_service(
            entry("wrong-source", source_type="other", confidence=0.95),
            entry("low", confidence=0.4),
            accepted,
        ),
        source_type="repair_reflection",
        minimum_confidence=0.8,
    )

    assert context.entries == (accepted,)


def test_retriever_applies_text_query_and_explicit_limit() -> None:
    first = entry("first", content="Falha na calculadora.")
    second = entry(
        "second", content="Outra falha na calculadora.", created_offset=1
    )
    context = retrieve(
        memory_service(first, second, entry("unrelated", content="Outro tema.")),
        text="CALCULADORA",
        max_results=1,
    )

    assert context.entries == (first,)
    assert context.total_matches == 2


def test_retriever_preserves_memory_order_deterministically() -> None:
    older_b = entry("b", created_offset=0)
    older_a = entry("a", created_offset=0)
    newer = entry("newer", created_offset=1)

    context = retrieve(memory_service(newer, older_b, older_a))

    assert tuple(item.memory_id.value for item in context.entries) == (
        "a", "b", "newer"
    )


def test_retriever_returns_empty_context() -> None:
    context = retrieve(memory_service(entry("not-learned", kind="custom")))

    assert context.entries == ()
    assert context.total_matches == 0


def test_retriever_preserves_original_memory_entries() -> None:
    original = entry("original")

    class MemoryFake:
        def search(self, query):
            del query
            return (original,)

    context = retrieve(MemoryFake())

    assert context.entries[0] is original
    assert context.entries[0].metadata == original.metadata


def test_retriever_satisfies_public_contract() -> None:
    retriever: KnowledgeRetriever = DeterministicKnowledgeRetriever(
        memory_service()
    )

    result = retriever.retrieve(KnowledgeRetrievalRequest(agent_id=AGENT))

    assert isinstance(result, LearnedKnowledgeContext)
