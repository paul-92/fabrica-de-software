from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from asep.agents import AgentId
from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
    EngineeringReflection,
    RepairProposal,
)
from asep.intelligence import (
    IntelligentEngineeringRequest,
    IntelligentEngineeringResult,
    IntelligentEngineeringService,
    KnowledgeAwareContext,
    KnowledgeAwarePlanningAdapter,
)
from asep.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
)
from asep.planning import (
    PlanningContext,
    PlanningEngine,
    PlanningRequest,
    PlanningResult,
)
from asep.repair import (
    FailureAnalysis,
    RepairChange,
    RepairPlan,
    RepairResult,
    RepairStatus,
)
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder


NOW = datetime(2026, 8, 5, 14, tzinfo=UTC)


def learned_entry() -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(value="knowledge-1"),
        agent_id=AgentId(value="agent-1"),
        execution_id="source-execution",
        category=MemoryCategory.CUSTOM,
        importance=MemoryImportance.NORMAL,
        content="Conhecimento aprendido.",
        metadata={"kind": "learned_knowledge"},
        created_at=NOW,
        updated_at=NOW,
    )


def base_planning_request() -> PlanningRequest:
    return PlanningRequest(
        goal="Planejar correção",
        context=PlanningContext(
            objective="Corrigir falha",
            workflow={
                "steps": [{
                    "id": "analyze",
                    "required_capability": "analysis",
                }]
            },
            available_capabilities=("analysis",),
        ),
        workflow_execution_id="run-1",
        agent_id=AgentId(value="agent-1"),
    )


def autonomous_request() -> AutonomousEngineeringRequest:
    return AutonomousEngineeringRequest(
        analysis=FailureAnalysis(summary="Falha funcional."),
        replacement_contents={"app.py": "replacement"},
    )


def autonomous_result(*, should_retry: bool = True) -> AutonomousEngineeringResult:
    analysis = FailureAnalysis(summary="Falha funcional.")
    proposal = RepairProposal(
        summary="Proposta.",
        reasoning="Razão.",
        candidate_files=("app.py",),
        suggested_actions=("Corrigir.",),
        confidence=0.8,
    )
    plan = RepairPlan(
        analysis=analysis,
        changes=(RepairChange(
            path="app.py", content="replacement", reason="Corrigir."
        ),),
    )
    repair_result = RepairResult(
        status=RepairStatus.FAILED,
        final_analysis=analysis,
    )
    reflection = EngineeringReflection(
        summary="Reflexão.",
        outcome=RepairStatus.FAILED,
        lessons=("Lição.",),
        recommended_actions=("Tentar novamente.",),
        should_retry=should_retry,
        confidence=0.7,
    )
    return AutonomousEngineeringResult(
        proposal=proposal,
        plan=plan,
        repair_result=repair_result,
        reflection=reflection,
    )


class AdapterSpy:
    def __init__(self) -> None:
        self.calls = []
        self.delegate = KnowledgeAwarePlanningAdapter()

    def adapt(self, request, knowledge_context):
        self.calls.append((request, knowledge_context))
        return self.delegate.adapt(request, knowledge_context)


class PlannerSpy:
    def __init__(self, result: PlanningResult) -> None:
        self.result = result
        self.calls = []

    def plan(self, request: PlanningRequest) -> PlanningResult:
        self.calls.append(request)
        return self.result


class EngineeringSpy:
    def __init__(self, result: AutonomousEngineeringResult) -> None:
        self.result = result
        self.calls = []

    def execute(self, request: AutonomousEngineeringRequest):
        self.calls.append(request)
        return self.result


def test_composes_both_subsystems_once_and_preserves_results() -> None:
    entry = learned_entry()
    planning = base_planning_request()
    knowledge = KnowledgeAwareContext(
        learned_entries=(entry,), knowledge_count=1
    )
    planning_result = PlanningResult.model_construct()
    engineering_result = autonomous_result()
    adapter = AdapterSpy()
    planner = PlannerSpy(planning_result)
    engineering = EngineeringSpy(engineering_result)
    request = IntelligentEngineeringRequest(
        planning_request=planning,
        knowledge_context=knowledge,
        engineering_request=autonomous_request(),
    )

    result = IntelligentEngineeringService(
        adapter, planner, engineering
    ).execute(request)

    assert isinstance(result, IntelligentEngineeringResult)
    assert adapter.calls == [(planning, knowledge)]
    assert len(planner.calls) == 1
    assert len(engineering.calls) == 1
    assert planner.calls[0].context.memory == (entry,)
    assert planner.calls[0].context.memory[0] is entry
    assert result.planning_request is planner.calls[0]
    assert result.planning_result is planning_result
    assert result.engineering_result is engineering_result


def test_preserves_inputs_and_does_not_retry_from_reflection() -> None:
    planning = base_planning_request()
    knowledge = KnowledgeAwareContext(knowledge_count=0)
    planner = PlannerSpy(PlanningResult.model_construct())
    engineering = EngineeringSpy(autonomous_result(should_retry=True))
    request = IntelligentEngineeringRequest(
        planning_request=planning,
        knowledge_context=knowledge,
        engineering_request=autonomous_request(),
    )

    result = IntelligentEngineeringService(
        KnowledgeAwarePlanningAdapter(), planner, engineering
    ).execute(request)

    assert planning.context.memory == ()
    assert knowledge.learned_entries == ()
    assert result.engineering_result.reflection.should_retry is True
    assert len(planner.calls) == 1
    assert len(engineering.calls) == 1


def test_integrates_with_real_planning_engine() -> None:
    entry = learned_entry()
    planning_engine = PlanningEngine(
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
        clock=lambda: NOW,
    )
    engineering_result = autonomous_result()
    engineering = EngineeringSpy(engineering_result)
    request = IntelligentEngineeringRequest(
        planning_request=base_planning_request(),
        knowledge_context=KnowledgeAwareContext(
            learned_entries=(entry,), knowledge_count=1
        ),
        engineering_request=autonomous_request(),
    )

    result = IntelligentEngineeringService(
        KnowledgeAwarePlanningAdapter(), planning_engine, engineering
    ).execute(request)

    assert result.planning_result.statistics.memory_entries_considered == 1
    assert result.engineering_result is engineering_result
    assert len(engineering.calls) == 1


def test_service_has_no_retrieval_persistence_or_effectful_dependencies() -> None:
    source = Path("src/asep/intelligence/engineering.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "KnowledgeRetriever",
        "AgentMemory",
        "MemoryService",
        "LearningService",
        "RepairLoop",
        "subprocess",
        "write_text",
    ):
        assert forbidden not in source
