from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from asep.ai_planning import (
    AutonomousEngineeringService,
    DeterministicReflectionEvaluator,
    DeterministicRepairPlanGenerator,
    RepairProposal,
)
from asep.api import create_app
from asep.application import (
    RunQueryService,
    create_intelligent_engineering_application_service,
)
from asep.metrics import MetricsService
from asep.planning import PlanningEngine
from asep.repair import FailureAnalysis, RepairResult, RepairStatus
from asep.runs import InMemoryRunRepository
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineRecorder,
)


NOW = datetime(2026, 8, 5, 14, tzinfo=UTC)
ENDPOINT = "/api/v1/intelligent-engineering/execute"


class ProposalPlannerFake:
    """Substitui somente a geração de proposta ainda não concreta."""

    def __init__(self) -> None:
        self.calls = 0

    def propose(self, analysis: FailureAnalysis) -> RepairProposal:
        self.calls += 1
        return RepairProposal(
            summary="Corrigir implementação.",
            reasoning=analysis.summary,
            candidate_files=("app.py",),
            suggested_actions=("Aplicar substituição explícita.",),
            confidence=0.8,
        )


class RepairExecutorFake:
    """Evita efeitos reais de filesystem, Tools e subprocess."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, plan) -> RepairResult:
        self.calls += 1
        return RepairResult(
            status=RepairStatus.FAILED,
            final_analysis=plan.analysis,
            messages=("A validação continuou falhando.",),
        )


class CountingPlanner:
    def __init__(self, delegate: PlanningEngine) -> None:
        self.delegate = delegate
        self.calls = 0

    def plan(self, request):
        self.calls += 1
        return self.delegate.plan(request)


class CountingEngineering:
    def __init__(self, delegate: AutonomousEngineeringService) -> None:
        self.delegate = delegate
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        return self.delegate.execute(request)


def memory(
    identifier: str,
    *,
    category: str,
    content: str,
) -> dict:
    return {
        "memory_id": identifier,
        "agent_id": "agent-1",
        "execution_id": "execution-a",
        "category": category,
        "importance": 2,
        "content": content,
        "metadata": {
            "kind": (
                "learned_knowledge" if category == "custom" else "ordinary"
            ),
            "recommended_actions": ["Informação, não comando."],
        },
        "created_at": "2026-08-05T14:00:00Z",
        "updated_at": "2026-08-05T14:00:00Z",
    }


def http_payload() -> dict:
    existing = memory(
        "memory-existing", category="fact", content="Memória existente."
    )
    duplicate = memory(
        "memory-existing", category="custom", content="Duplicata aprendida."
    )
    learned = memory(
        "memory-learned", category="custom", content="Conhecimento aprendido."
    )
    return {
        "planning_request": {
            "goal": "Planejar correção",
            "context": {
                "objective": "Corrigir falha",
                "memory": [existing],
                "workflow": {
                    "steps": [{
                        "id": "analyze",
                        "required_capability": "analysis",
                    }]
                },
                "available_capabilities": ["analysis"],
            },
            "workflow_execution_id": "run-e2e",
            "agent_id": "agent-1",
        },
        "knowledge_context": {
            "base_context": {"execution": "B"},
            "learned_entries": [duplicate, learned],
            "knowledge_count": 2,
        },
        "engineering_request": {
            "analysis": {"summary": "Falha funcional da execução B."},
            "replacement_contents": {"app.py": "explicit replacement"},
            "test_paths": ["tests"],
        },
    }


def build_client():
    planner = CountingPlanner(
        PlanningEngine(
            timeline=TimelineRecorder(InMemoryTimelineRepository()),
            clock=lambda: NOW,
        )
    )
    proposal_planner = ProposalPlannerFake()
    repair_executor = RepairExecutorFake()
    engineering = CountingEngineering(
        AutonomousEngineeringService(
            proposal_planner,
            DeterministicRepairPlanGenerator(),
            repair_executor,
            DeterministicReflectionEvaluator(),
        )
    )
    application_service = create_intelligent_engineering_application_service(
        planner, engineering
    )
    query = RunQueryService(
        InMemoryRunRepository(), InMemoryTimelineRepository()
    )
    app = create_app(query, MetricsService(query), application_service)
    return (
        TestClient(app),
        planner,
        engineering,
        proposal_planner,
        repair_executor,
    )


def test_http_executes_full_intelligent_engineering_flow() -> None:
    client, planner, engineering, proposal_planner, repair_executor = (
        build_client()
    )
    payload = http_payload()
    original = deepcopy(payload)

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 200
    assert payload == original
    assert planner.calls == 1
    assert engineering.calls == 1
    assert proposal_planner.calls == 1
    assert repair_executor.calls == 1

    body = response.json()
    assert set(body) == {
        "planning_request",
        "planning_result",
        "engineering_result",
    }
    memory_entries = body["planning_request"]["context"]["memory"]
    assert [entry["memory_id"] for entry in memory_entries] == [
        "memory-existing",
        "memory-learned",
    ]
    assert memory_entries[1]["content"] == "Conhecimento aprendido."
    assert memory_entries[1]["metadata"]["recommended_actions"] == [
        "Informação, não comando."
    ]
    statistics = body["planning_result"]["statistics"]
    assert statistics["memory_entries_considered"] == 2
    assert statistics["total_steps"] == 1

    result = body["engineering_result"]
    assert result["proposal"]["candidate_files"] == ["app.py"]
    assert result["plan"]["changes"][0]["path"] == "app.py"
    assert result["repair_result"]["status"] == "failed"
    assert result["reflection"]["should_retry"] is True
    assert result["reflection"]["recommended_actions"]
    assert engineering.calls == 1
    assert repair_executor.calls == 1


def test_endpoint_is_absent_without_application_service() -> None:
    query = RunQueryService(
        InMemoryRunRepository(), InMemoryTimelineRepository()
    )
    client = TestClient(create_app(query, MetricsService(query)))

    assert client.post(ENDPOINT, json=http_payload()).status_code == 404
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/runs").status_code == 200
    assert client.get("/api/v1/metrics/summary").status_code == 200
