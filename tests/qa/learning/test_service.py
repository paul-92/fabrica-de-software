from __future__ import annotations

from datetime import UTC, datetime

from asep.agents import AgentId
from asep.ai_planning import EngineeringReflection
from asep.learning import (
    DeterministicLearningExtractor,
    LearnedKnowledgeMemoryAdapter,
    LearningRequest,
    LearningService,
)
from asep.memory import (
    InMemoryMemoryStore,
    MemoryCategory,
    MemoryId,
    MemoryService,
)
from asep.repair import RepairResult, RepairStatus
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder


NOW = datetime(2026, 8, 4, 15, tzinfo=UTC)


def request() -> LearningRequest:
    return LearningRequest(
        repair_result=RepairResult(status=RepairStatus.FAILED),
        reflection=EngineeringReflection(
            summary="A tentativa falhou.",
            outcome=RepairStatus.FAILED,
            lessons=("O plano não corrigiu o teste.",),
            recommended_actions=("Reavaliar a proposta.",),
            should_retry=True,
            confidence=0.7,
        ),
        source_execution_id="repair-source-1",
        source_type="repair_reflection",
        memory_id=MemoryId(value="learned-1"),
        agent_id=AgentId(value="learning-agent"),
        execution_id="learning-execution-1",
        workflow_execution_id="workflow-1",
        created_at=NOW,
        updated_at=NOW,
    )


class CountingExtractor(DeterministicLearningExtractor):
    def __init__(self) -> None:
        self.calls = 0

    def extract(self, *args, **kwargs):
        self.calls += 1
        return super().extract(*args, **kwargs)


class CountingAdapter(LearnedKnowledgeMemoryAdapter):
    def __init__(self) -> None:
        self.calls = 0

    def adapt(self, *args, **kwargs):
        self.calls += 1
        return super().adapt(*args, **kwargs)


def test_learning_service_composes_once_and_persists_with_memory_service() -> None:
    store = InMemoryMemoryStore()
    memory = MemoryService(
        store,
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
    )
    extractor = CountingExtractor()
    adapter = CountingAdapter()
    service = LearningService(extractor, memory, adapter=adapter)

    result = service.learn(request())

    assert extractor.calls == 1
    assert adapter.calls == 1
    assert result.learned_knowledge.lessons == (
        "O plano não corrigiu o teste.",
    )
    assert result.learned_knowledge.recommended_actions == (
        "Reavaliar a proposta.",
    )
    assert result.memory_entry.category is MemoryCategory.CUSTOM
    assert result.memory_entry.metadata["kind"] == "learned_knowledge"
    assert store.get(MemoryId(value="learned-1")) == result.memory_entry


def test_recommended_actions_do_not_trigger_another_extraction_or_save() -> None:
    class MemoryFake:
        def __init__(self) -> None:
            self.calls = 0

        def save(self, entry):
            self.calls += 1
            return entry

    extractor = CountingExtractor()
    memory = MemoryFake()

    result = LearningService(extractor, memory).learn(request())

    assert result.learned_knowledge.recommended_actions
    assert result.learned_knowledge.metadata["should_retry"] is True
    assert extractor.calls == 1
    assert memory.calls == 1

