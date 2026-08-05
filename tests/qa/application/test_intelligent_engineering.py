from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.ai_planning import (
    AutonomousEngineeringRequest,
    AutonomousEngineeringResult,
)
from asep.application import (
    ApplicationIntelligentEngineeringRequest,
    ApplicationIntelligentEngineeringResult,
    IntelligentEngineeringApplicationService,
    IntelligentEngineeringCapability,
)
from asep.intelligence import (
    IntelligentEngineeringRequest,
    IntelligentEngineeringResult,
    KnowledgeAwareContext,
)
from asep.planning import PlanningContext, PlanningRequest, PlanningResult
from asep.repair import FailureAnalysis


def application_request() -> ApplicationIntelligentEngineeringRequest:
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


def internal_result(
    request: ApplicationIntelligentEngineeringRequest,
) -> IntelligentEngineeringResult:
    return IntelligentEngineeringResult(
        planning_request=request.planning_request,
        planning_result=PlanningResult.model_construct(),
        engineering_result=AutonomousEngineeringResult.model_construct(),
    )


class CapabilitySpy:
    def __init__(self, result: IntelligentEngineeringResult) -> None:
        self.result = result
        self.calls: list[IntelligentEngineeringRequest] = []

    def execute(
        self,
        request: IntelligentEngineeringRequest,
    ) -> IntelligentEngineeringResult:
        self.calls.append(request)
        return self.result


def test_public_request_is_strict_and_immutable() -> None:
    request = application_request()

    with pytest.raises(ValidationError):
        ApplicationIntelligentEngineeringRequest(
            **request.model_dump(mode="python"),
            branding="forbidden",
        )
    with pytest.raises(ValidationError):
        request.planning_request = request.planning_request


def test_public_result_is_strict_and_immutable() -> None:
    request = application_request()
    result = internal_result(request)
    public = ApplicationIntelligentEngineeringResult(
        planning_request=result.planning_request,
        planning_result=result.planning_result,
        engineering_result=result.engineering_result,
    )

    with pytest.raises(ValidationError):
        ApplicationIntelligentEngineeringResult(
            **public.model_dump(mode="python"),
            theme="forbidden",
        )
    with pytest.raises(ValidationError):
        public.planning_result = public.planning_result


def test_service_delegates_once_and_preserves_request_fields() -> None:
    request = application_request()
    capability = CapabilitySpy(internal_result(request))

    IntelligentEngineeringApplicationService(capability).execute(request)

    assert len(capability.calls) == 1
    delegated = capability.calls[0]
    assert delegated.planning_request is request.planning_request
    assert delegated.knowledge_context is request.knowledge_context
    assert delegated.engineering_request is request.engineering_request


def test_service_preserves_internal_results_in_public_result() -> None:
    request = application_request()
    expected = internal_result(request)

    result = IntelligentEngineeringApplicationService(
        CapabilitySpy(expected)
    ).execute(request)

    assert result.planning_request is expected.planning_request
    assert result.planning_result is expected.planning_result
    assert result.engineering_result is expected.engineering_result


def test_service_does_not_swallow_internal_errors() -> None:
    class FailingCapability:
        def execute(self, request: IntelligentEngineeringRequest):
            del request
            raise RuntimeError("internal failure")

    with pytest.raises(RuntimeError, match="internal failure"):
        IntelligentEngineeringApplicationService(
            FailingCapability()
        ).execute(application_request())


def test_service_satisfies_public_capability_contract() -> None:
    request = application_request()
    capability: IntelligentEngineeringCapability = CapabilitySpy(
        internal_result(request)
    )

    assert capability.execute(
        IntelligentEngineeringRequest(
            planning_request=request.planning_request,
            knowledge_context=request.knowledge_context,
            engineering_request=request.engineering_request,
        )
    )


def test_application_boundary_has_no_transport_or_concrete_infrastructure() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "src/asep/application/contracts.py",
            "src/asep/application/intelligent_engineering.py",
        )
    )

    for forbidden in (
        "fastapi",
        "asep.api",
        "PlanningEngine",
        "AutonomousEngineeringService",
        "MemoryService",
        "SQLite",
        "subprocess",
        "Tool",
    ):
        assert forbidden not in sources


def test_application_package_exports_public_api() -> None:
    assert ApplicationIntelligentEngineeringRequest is not None
    assert ApplicationIntelligentEngineeringResult is not None
    assert IntelligentEngineeringApplicationService is not None
    assert IntelligentEngineeringCapability is not None
