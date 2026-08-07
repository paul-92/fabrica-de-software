from __future__ import annotations

from pathlib import Path

from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
)
from asep.application import (
    ApplicationIntelligentEngineeringRequest,
    IntelligentEngineeringApplicationService,
    create_intelligent_engineering_application_service,
)
from asep.intelligence import KnowledgeAwareContext
from asep.planning import PlanningContext, PlanningRequest, PlanningResult
from asep.repair import FailureAnalysis


class PlannerFake:
    def __init__(self) -> None:
        self.calls: list[PlanningRequest] = []
        self.result = PlanningResult.model_construct()

    def plan(self, request: PlanningRequest) -> PlanningResult:
        self.calls.append(request)
        return self.result


class EngineeringFake:
    def __init__(self) -> None:
        self.calls: list[AutonomousEngineeringRequest] = []
        self.result = AutonomousEngineeringResult.model_construct()

    def execute(
        self,
        request: AutonomousEngineeringRequest,
    ) -> AutonomousEngineeringResult:
        self.calls.append(request)
        return self.result


def request() -> ApplicationIntelligentEngineeringRequest:
    return ApplicationIntelligentEngineeringRequest(
        planning_request=PlanningRequest(
            goal="Planejar correção",
            context=PlanningContext(objective="Corrigir falha"),
        ),
        knowledge_context=KnowledgeAwareContext(knowledge_count=0),
        engineering_request=AutonomousEngineeringRequest(
            analysis=FailureAnalysis(summary="Falha funcional."),
            replacement_contents={"app.py": "explicit replacement"},
        ),
    )


def test_factory_returns_application_boundary_without_execution() -> None:
    planner = PlannerFake()
    engineering = EngineeringFake()

    service = create_intelligent_engineering_application_service(
        planner, engineering
    )

    assert isinstance(service, IntelligentEngineeringApplicationService)
    assert planner.calls == []
    assert engineering.calls == []


def test_factory_reuses_explicit_planning_adapter() -> None:
    planner = PlannerFake()
    engineering = EngineeringFake()

    class PlanningAdapterSpy:
        def __init__(self) -> None:
            self.calls = 0

        def adapt(self, planning_request, knowledge_context):
            self.calls += 1
            return planning_request

    adapter = PlanningAdapterSpy()
    service = create_intelligent_engineering_application_service(
        planner,
        engineering,
        adapter,
    )

    service.execute(request())
    assert adapter.calls == 1


def test_composed_service_reuses_dependencies_when_executed() -> None:
    planner = PlannerFake()
    engineering = EngineeringFake()
    service = create_intelligent_engineering_application_service(
        planner, engineering
    )
    application_request = request()

    result = service.execute(application_request)

    assert len(planner.calls) == 1
    assert len(engineering.calls) == 1
    assert planner.calls[0].goal == application_request.planning_request.goal
    assert engineering.calls[0] is application_request.engineering_request
    assert result.planning_result is planner.result
    assert result.engineering_result is engineering.result


def test_composition_has_no_transport_or_hidden_infrastructure() -> None:
    source = Path(
        "src/asep/application/intelligent_engineering_composition.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "fastapi",
        "asep.api",
        "MemoryService",
        "Repository",
        "SQLite",
        "Configuration",
        "subprocess",
        "Tool",
    ):
        assert forbidden not in source


def test_factory_is_exported_by_application_package() -> None:
    assert create_intelligent_engineering_application_service is not None
