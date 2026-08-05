from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from asep.agents import AgentId
from asep.intelligence import (
    KnowledgeAwareContext,
    KnowledgeAwarePlanningAdapter,
    KnowledgePlanningAdapter,
)
from asep.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
)
from asep.planning import PlanningContext, PlanningEngine, PlanningRequest
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder


NOW = datetime(2026, 8, 5, 14, tzinfo=UTC)


def memory(identifier: str, *, learned: bool = True) -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(value=identifier),
        agent_id=AgentId(value="planning-agent"),
        execution_id=f"execution-{identifier}",
        category=MemoryCategory.CUSTOM if learned else MemoryCategory.FACT,
        importance=MemoryImportance.NORMAL,
        content=f"Memória {identifier}",
        metadata={
            "kind": "learned_knowledge" if learned else "ordinary",
            "recommended_actions": ["Apenas informação."],
        },
        created_at=NOW,
        updated_at=NOW,
    )


def request(*entries: MemoryEntry) -> PlanningRequest:
    return PlanningRequest(
        goal="Corrigir falha",
        context=PlanningContext(
            objective="Planejar correção",
            memory=entries,
            workflow={
                "steps": [{
                    "id": "analyze",
                    "required_capability": "analysis",
                }]
            },
            metadata={"context": "preserved"},
            constraints=("safe",),
            available_capabilities=("analysis",),
            available_tools={"analysis": "analysis-tool"},
        ),
        workflow_execution_id="run-20-2",
        agent_id=AgentId(value="planning-agent"),
        metadata={"request": "preserved"},
    )


def knowledge(*entries: MemoryEntry) -> KnowledgeAwareContext:
    return KnowledgeAwareContext(
        base_context={"must_not_leak": True},
        learned_entries=entries,
        knowledge_count=len(entries),
        metadata={"source": "retrieval"},
    )


def test_adapts_request_without_learned_knowledge() -> None:
    original = request()
    adapted = KnowledgeAwarePlanningAdapter().adapt(original, knowledge())

    assert adapted.context.memory == ()
    assert adapted is not original


def test_adds_one_original_learned_entry() -> None:
    learned = memory("learned")
    adapted = KnowledgeAwarePlanningAdapter().adapt(
        request(), knowledge(learned)
    )

    assert adapted.context.memory == (learned,)
    assert adapted.context.memory[0] is learned


def test_preserves_existing_memory_then_learned_order() -> None:
    existing = memory("existing", learned=False)
    first = memory("first")
    second = memory("second")

    adapted = KnowledgeAwarePlanningAdapter().adapt(
        request(existing), knowledge(first, second)
    )

    assert adapted.context.memory == (existing, first, second)


def test_deduplicates_by_memory_id_and_keeps_existing_entry() -> None:
    existing = memory("same", learned=False)
    duplicate = memory("same")

    adapted = KnowledgeAwarePlanningAdapter().adapt(
        request(existing), knowledge(duplicate)
    )

    assert adapted.context.memory == (existing,)
    assert adapted.context.memory[0] is existing


def test_preserves_all_other_request_and_context_fields() -> None:
    original = request()
    adapted = KnowledgeAwarePlanningAdapter().adapt(
        original, knowledge(memory("learned"))
    )

    assert adapted.goal == original.goal
    assert adapted.workflow_execution_id == original.workflow_execution_id
    assert adapted.agent_id == original.agent_id
    assert adapted.metadata == original.metadata
    assert adapted.context.objective == original.context.objective
    assert adapted.context.workflow == original.context.workflow
    assert adapted.context.constraints == original.context.constraints
    assert (
        adapted.context.available_capabilities
        == original.context.available_capabilities
    )
    assert adapted.context.available_tools == original.context.available_tools
    assert adapted.context.metadata == original.context.metadata
    assert "must_not_leak" not in adapted.context.metadata


def test_does_not_modify_inputs_or_execute_recommended_actions() -> None:
    learned = memory("learned")
    original = request()
    original_knowledge = knowledge(learned)

    KnowledgeAwarePlanningAdapter().adapt(original, original_knowledge)

    assert original.context.memory == ()
    assert original_knowledge.learned_entries == (learned,)
    assert learned.metadata["recommended_actions"] == [
        "Apenas informação."
    ]


def test_adapter_satisfies_public_contract() -> None:
    adapter: KnowledgePlanningAdapter = KnowledgeAwarePlanningAdapter()

    assert adapter.adapt(request(), knowledge()).context.memory == ()


def test_adapter_has_no_memory_access_or_effectful_dependencies() -> None:
    source = Path("src/asep/intelligence/planning.py").read_text(
        encoding="utf-8"
    )

    assert "AgentMemory" not in source
    assert "MemoryService" not in source
    assert "KnowledgeRetriever" not in source
    assert "subprocess" not in source
    assert ".execute(" not in source


def test_integrates_with_real_planning_engine() -> None:
    learned = memory("learned")
    adapted = KnowledgeAwarePlanningAdapter().adapt(
        request(), knowledge(learned)
    )
    engine = PlanningEngine(
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
        clock=lambda: NOW,
    )

    result = engine.plan(adapted)

    assert result.statistics.memory_entries_considered == 1
    assert adapted.context.memory[0] is learned
