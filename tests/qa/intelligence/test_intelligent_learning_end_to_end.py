from __future__ import annotations

from datetime import UTC, datetime, timedelta

from asep.agents import AgentId
from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringService,
    DeterministicReflectionEvaluator,
    DeterministicRepairPlanGenerator,
    EngineeringReflection,
    RepairProposal,
)
from asep.intelligence import (
    DeterministicKnowledgeContextBuilder,
    IntelligentEngineeringRequest,
    IntelligentEngineeringService,
    KnowledgeAwarePlanningAdapter,
)
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
)
from asep.planning import PlanningContext, PlanningEngine, PlanningRequest
from asep.repair import FailureAnalysis, RepairResult, RepairStatus
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder


NOW = datetime(2026, 8, 5, 14, tzinfo=UTC)
AGENT = AgentId(value="engineer")
OTHER_AGENT = AgentId(value="other-engineer")


def memory_service() -> MemoryService:
    return MemoryService(
        InMemoryMemoryStore(),
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
        clock=lambda: NOW,
    )


def learning_request(
    identifier: str,
    *,
    agent_id: AgentId = AGENT,
    status: RepairStatus = RepairStatus.SUCCEEDED,
    should_retry: bool = False,
    timestamp: datetime = NOW,
) -> LearningRequest:
    analysis = FailureAnalysis(summary=f"Falha {identifier}.")
    result = RepairResult(
        status=status,
        final_analysis=analysis,
        messages=(f"Lição {identifier}.",),
    )
    reflection = EngineeringReflection(
        summary=f"Conhecimento {identifier}.",
        outcome=status,
        lessons=(f"Lição {identifier}.",),
        recommended_actions=(f"Recomendação {identifier}.",),
        should_retry=should_retry,
        confidence=0.8,
    )
    return LearningRequest(
        repair_result=result,
        reflection=reflection,
        source_execution_id=f"source-{identifier}",
        source_type="engineering_reflection",
        memory_id=MemoryId(value=f"memory-{identifier}"),
        agent_id=agent_id,
        execution_id=f"execution-{identifier}",
        created_at=timestamp,
        updated_at=timestamp,
    )


class ProposalPlannerFake:
    def __init__(self) -> None:
        self.calls = 0

    def propose(self, analysis: FailureAnalysis) -> RepairProposal:
        self.calls += 1
        return RepairProposal(
            summary="Reparar arquivo.",
            reasoning=analysis.summary,
            candidate_files=("app.py",),
            suggested_actions=("Aplicar conteúdo explícito.",),
            confidence=0.8,
        )


class RepairExecutorFake:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, plan) -> RepairResult:
        self.calls += 1
        return RepairResult(
            status=RepairStatus.FAILED,
            final_analysis=plan.analysis,
            messages=("A validação continuou falhando.",),
        )


def test_learn_plan_engineer_learn_and_retrieve_end_to_end() -> None:
    memory = memory_service()
    learning = LearningService(DeterministicLearningExtractor(), memory)
    retriever = DeterministicKnowledgeRetriever(memory)

    previous = learning.learn(learning_request("previous"))
    other = learning.learn(
        learning_request("other", agent_id=OTHER_AGENT)
    )
    ordinary = MemoryEntry(
        memory_id=MemoryId(value="ordinary-memory"),
        agent_id=AGENT,
        execution_id="ordinary-execution",
        category=MemoryCategory.FACT,
        importance=MemoryImportance.NORMAL,
        content="Memória operacional comum.",
        metadata={"recommended_actions": ["Não executar."]},
        created_at=NOW,
        updated_at=NOW,
    )
    memory.save(ordinary)

    retrieved = retriever.retrieve(
        KnowledgeRetrievalRequest(agent_id=AGENT, max_results=10)
    )
    assert retrieved.entries == (previous.memory_entry,)
    assert retrieved.entries[0] is previous.memory_entry
    assert other.memory_entry not in retrieved.entries
    assert ordinary not in retrieved.entries

    knowledge_context = DeterministicKnowledgeContextBuilder().build(
        {"execution": "B"}, retrieved
    )
    planning_request = PlanningRequest(
        goal="Planejar reparo",
        context=PlanningContext(
            objective="Corrigir falha",
            memory=(previous.memory_entry,),
            workflow={
                "steps": [{
                    "id": "analyze",
                    "required_capability": "analysis",
                }]
            },
            available_capabilities=("analysis",),
        ),
        workflow_execution_id="execution-b",
        agent_id=AGENT,
    )
    planning = PlanningEngine(
        timeline=TimelineRecorder(InMemoryTimelineRepository()),
        clock=lambda: NOW,
    )
    proposal_planner = ProposalPlannerFake()
    repair_executor = RepairExecutorFake()
    autonomous = AutonomousEngineeringService(
        proposal_planner,
        DeterministicRepairPlanGenerator(),
        repair_executor,
        DeterministicReflectionEvaluator(),
    )
    intelligent = IntelligentEngineeringService(
        KnowledgeAwarePlanningAdapter(), planning, autonomous
    )

    result = intelligent.execute(
        IntelligentEngineeringRequest(
            planning_request=planning_request,
            knowledge_context=knowledge_context,
            engineering_request=AutonomousEngineeringRequest(
                analysis=FailureAnalysis(summary="Falha da execução B."),
                replacement_contents={"app.py": "explicit replacement"},
            ),
        )
    )

    assert result.planning_result.statistics.memory_entries_considered == 1
    assert result.planning_request.context.memory == (
        previous.memory_entry,
    )
    assert proposal_planner.calls == 1
    assert repair_executor.calls == 1
    assert result.engineering_result.reflection.should_retry is True

    new_learning = learning.learn(
        LearningRequest(
            repair_result=result.engineering_result.repair_result,
            reflection=result.engineering_result.reflection,
            source_execution_id="execution-b",
            source_type="engineering_reflection",
            memory_id=MemoryId(value="memory-current"),
            agent_id=AGENT,
            execution_id="execution-b",
            created_at=NOW + timedelta(seconds=1),
            updated_at=NOW + timedelta(seconds=1),
        )
    )
    later = retriever.retrieve(
        KnowledgeRetrievalRequest(
            agent_id=AGENT,
            source_type="engineering_reflection",
            minimum_confidence=0.7,
            max_results=10,
        )
    )

    assert later.entries == (
        previous.memory_entry,
        new_learning.memory_entry,
    )
    assert all(
        entry.metadata["kind"] == "learned_knowledge"
        for entry in later.entries
    )
    assert proposal_planner.calls == 1
    assert repair_executor.calls == 1
