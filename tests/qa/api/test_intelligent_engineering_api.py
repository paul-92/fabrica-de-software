from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from asep.agents import AgentId
from asep.ai_planning import (
    AutonomousEngineeringResult,
    EngineeringReflection,
    RepairProposal,
)
from asep.api import create_app
from asep.api.intelligent_engineering_schemas import (
    IntelligentEngineeringExecuteRequest,
    IntelligentEngineeringExecuteResponse,
)
from asep.application import (
    ApplicationIntelligentEngineeringRequest,
    ApplicationIntelligentEngineeringResult,
    RunQueryService,
)
from asep.metrics import MetricsService
from asep.planning import (
    ExecutionPlan,
    PlanningContext,
    PlanningRequest,
    PlanningResult,
    PlanningStatistics,
    PlanStep,
)
from asep.repair import (
    FailureAnalysis,
    RepairChange,
    RepairPlan,
    RepairResult,
    RepairStatus,
)
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


NOW = datetime(2026, 8, 5, 14, tzinfo=UTC)


def payload() -> dict:
    return {
        "planning_request": {
            "goal": "Planejar correção",
            "context": {
                "objective": "Corrigir falha",
                "workflow": {"steps": []},
            },
            "workflow_execution_id": "run-1",
            "agent_id": "agent-1",
        },
        "knowledge_context": {
            "base_context": {"execution": "B"},
            "learned_entries": [],
            "knowledge_count": 0,
        },
        "engineering_request": {
            "analysis": {"summary": "Falha funcional."},
            "replacement_contents": {"app.py": "replacement"},
            "test_paths": ["tests"],
        },
    }


def memory_payload(**overrides) -> dict:
    values = {
        "memory_id": "memory-1",
        "agent_id": "agent-1",
        "execution_id": "execution-a",
        "category": "custom",
        "importance": 2,
        "content": "Conhecimento aprendido.",
        "metadata": {"kind": "learned_knowledge"},
        "created_at": "2026-08-05T14:00:00Z",
        "updated_at": "2026-08-05T14:00:00Z",
    }
    values.update(overrides)
    return values


def application_result() -> ApplicationIntelligentEngineeringResult:
    analysis = FailureAnalysis(summary="Falha funcional.")
    planning_request = PlanningRequest(
        goal="Planejar correção",
        context=PlanningContext(objective="Corrigir falha"),
        workflow_execution_id="run-1",
        agent_id=AgentId(value="agent-1"),
    )
    step = PlanStep(
        step_id="analyze",
        description="Analisar",
        required_capability="analysis",
    )
    planning_result = PlanningResult(
        plan=ExecutionPlan(
            plan_id="plan-1",
            goal=planning_request.goal,
            steps=(step,),
            estimated_cost=1,
            estimated_duration_seconds=60,
            created_at=NOW,
        ),
        validation_messages=("Plano validado.",),
        statistics=PlanningStatistics(
            total_steps=1,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=1,
            estimated_duration_seconds=60,
            memory_entries_considered=0,
        ),
    )
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
        messages=("Falhou.",),
    )
    engineering_result = AutonomousEngineeringResult(
        proposal=proposal,
        plan=plan,
        repair_result=repair_result,
        reflection=EngineeringReflection(
            summary="Reflexão.",
            outcome=RepairStatus.FAILED,
            lessons=("Lição.",),
            recommended_actions=("Reavaliar.",),
            should_retry=True,
            confidence=0.7,
        ),
    )
    return ApplicationIntelligentEngineeringResult(
        planning_request=planning_request,
        planning_result=planning_result,
        engineering_result=engineering_result,
    )


class ApplicationServiceFake:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or application_result()
        self.error = error
        self.calls: list[ApplicationIntelligentEngineeringRequest] = []

    def execute(self, request: ApplicationIntelligentEngineeringRequest):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.result


def app_client(service, *, raise_server_exceptions=True) -> TestClient:
    query = RunQueryService(
        InMemoryRunRepository(), InMemoryTimelineRepository()
    )
    app = create_app(query, MetricsService(query), service)
    return TestClient(
        app, raise_server_exceptions=raise_server_exceptions
    )


def test_http_schema_rejects_extra_fields() -> None:
    body = payload()
    body["branding"] = "forbidden"

    response = app_client(ApplicationServiceFake()).post(
        "/api/v1/intelligent-engineering/execute", json=body
    )

    assert response.status_code == 422


def test_invalid_memory_category_is_rejected_as_422() -> None:
    body = payload()
    body["knowledge_context"]["learned_entries"] = [
        memory_payload(category="not-a-category")
    ]
    body["knowledge_context"]["knowledge_count"] = 1

    response = app_client(ApplicationServiceFake()).post(
        "/api/v1/intelligent-engineering/execute", json=body
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_invalid_memory_importance_is_rejected_as_422() -> None:
    body = payload()
    body["knowledge_context"]["learned_entries"] = [
        memory_payload(importance=99)
    ]
    body["knowledge_context"]["knowledge_count"] = 1

    response = app_client(ApplicationServiceFake()).post(
        "/api/v1/intelligent-engineering/execute", json=body
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_blank_required_memory_identifier_is_rejected_as_422() -> None:
    body = payload()
    body["knowledge_context"]["learned_entries"] = [
        memory_payload(memory_id="   ")
    ]
    body["knowledge_context"]["knowledge_count"] = 1

    response = app_client(ApplicationServiceFake()).post(
        "/api/v1/intelligent-engineering/execute", json=body
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_http_request_maps_to_application_request() -> None:
    mapped = IntelligentEngineeringExecuteRequest.model_validate(
        payload()
    ).to_application()

    assert isinstance(mapped, ApplicationIntelligentEngineeringRequest)
    assert mapped.planning_request.goal == "Planejar correção"
    assert mapped.planning_request.agent_id == AgentId(value="agent-1")
    assert mapped.knowledge_context.base_context["execution"] == "B"
    assert mapped.engineering_request.replacement_contents == {
        "app.py": "replacement"
    }


def test_endpoint_calls_application_once_and_maps_response() -> None:
    service = ApplicationServiceFake()

    response = app_client(service).post(
        "/api/v1/intelligent-engineering/execute", json=payload()
    )

    assert response.status_code == 200
    assert len(service.calls) == 1
    body = response.json()
    assert body["planning_result"]["plan"]["plan_id"] == "plan-1"
    assert body["engineering_result"]["repair_result"]["status"] == "failed"
    assert body["engineering_result"]["reflection"]["should_retry"] is True


def test_response_mapper_preserves_application_result() -> None:
    mapped = IntelligentEngineeringExecuteResponse.from_application(
        application_result()
    )

    assert mapped.planning_request.workflow_execution_id == "run-1"
    assert mapped.planning_result.statistics.total_steps == 1
    assert mapped.engineering_result.proposal.candidate_files == ("app.py",)


def test_application_error_uses_existing_safe_http_policy() -> None:
    service = ApplicationServiceFake(error=RuntimeError("secret details"))

    response = app_client(
        service, raise_server_exceptions=False
    ).post("/api/v1/intelligent-engineering/execute", json=payload())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "secret details" not in response.text


def test_existing_endpoints_remain_available() -> None:
    client = app_client(ApplicationServiceFake())

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/runs").status_code == 200
    assert client.get("/api/v1/metrics/summary").status_code == 200


def test_openapi_includes_intelligent_engineering_endpoint() -> None:
    schema = app_client(ApplicationServiceFake()).get("/openapi.json").json()

    assert "/api/v1/intelligent-engineering/execute" in schema["paths"]


def test_http_adapter_does_not_call_core_implementations_directly() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "src/asep/api/intelligent_engineering_routes.py",
            "src/asep/api/intelligent_engineering_schemas.py",
        )
    )

    for forbidden in (
        "PlanningEngine",
        "IntelligentEngineeringService",
        "AutonomousEngineeringService",
        "MemoryService",
        "LearningService",
        "SQLite",
        "subprocess",
    ):
        assert forbidden not in sources


def test_fastapi_is_not_imported_by_application_layer() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/asep/application").glob("*.py")
    )

    assert "fastapi" not in sources.casefold()
