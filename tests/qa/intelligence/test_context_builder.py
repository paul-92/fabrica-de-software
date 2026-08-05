from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.agents import AgentId
from asep.intelligence import (
    DeterministicKnowledgeContextBuilder,
    KnowledgeAwareContext,
    KnowledgeContextBuilder,
)
from asep.learning import LearnedKnowledgeContext
from asep.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
)


NOW = datetime(2026, 8, 5, 14, tzinfo=UTC)


def learned_entry(identifier: str) -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(value=identifier),
        agent_id=AgentId(value="learning-agent"),
        execution_id=f"execution-{identifier}",
        category=MemoryCategory.CUSTOM,
        importance=MemoryImportance.NORMAL,
        content=f"Conhecimento {identifier}.",
        metadata={
            "kind": "learned_knowledge",
            "recommended_actions": ["Informação, não comando."],
        },
        created_at=NOW,
        updated_at=NOW,
    )


def build(*entries: MemoryEntry) -> KnowledgeAwareContext:
    return DeterministicKnowledgeContextBuilder().build(
        {"objective": "Corrigir calculadora", "attempt": 1},
        LearnedKnowledgeContext(
            entries=entries,
            total_matches=len(entries),
        ),
        metadata={"source": "execution-b"},
    )


def test_builder_creates_context_without_knowledge() -> None:
    result = build()

    assert result.learned_entries == ()
    assert result.knowledge_count == 0


def test_builder_preserves_single_original_memory_entry() -> None:
    entry = learned_entry("one")
    result = build(entry)

    assert result.learned_entries == (entry,)
    assert result.learned_entries[0] is entry
    assert result.knowledge_count == 1


def test_builder_preserves_multiple_entries_in_received_order() -> None:
    first = learned_entry("first")
    second = learned_entry("second")
    result = build(first, second)

    assert result.learned_entries == (first, second)
    assert result.knowledge_count == 2


def test_builder_preserves_base_context_and_metadata() -> None:
    result = build(learned_entry("one"))

    assert result.base_context["objective"] == "Corrigir calculadora"
    assert result.base_context["attempt"] == 1
    assert result.metadata == {"source": "execution-b"}


def test_knowledge_aware_context_is_immutable() -> None:
    result = build()

    with pytest.raises(ValidationError):
        result.knowledge_count = 10


def test_model_rejects_inconsistent_knowledge_count() -> None:
    with pytest.raises(ValidationError, match="knowledge_count"):
        KnowledgeAwareContext(
            learned_entries=(learned_entry("one"),),
            knowledge_count=0,
        )


def test_builder_satisfies_public_contract() -> None:
    builder: KnowledgeContextBuilder = DeterministicKnowledgeContextBuilder()

    result = builder.build({}, LearnedKnowledgeContext(total_matches=0))

    assert isinstance(result, KnowledgeAwareContext)


def test_builder_has_no_effectful_or_retrieval_dependencies() -> None:
    source = Path("src/asep/intelligence/builder.py").read_text(
        encoding="utf-8"
    )

    assert "write_text" not in source
    assert "subprocess" not in source
    assert "Tool" not in source
    assert "KnowledgeRetriever" not in source
    assert ".search(" not in source

