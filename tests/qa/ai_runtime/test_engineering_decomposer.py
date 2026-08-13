import json

import pytest

from asep.ai_runtime import (
    AIRuntimeIdentity,
    AIRuntimeRequest,
    AIRuntimeResult,
    AIRuntimeTimeoutError,
)
from asep.ai_runtime.engineering_decomposer import (
    CodexEngineeringTaskDecomposer,
    EngineeringDecompositionError,
)
from asep.application import (
    BoundedProjectAnalysis,
    DeterministicEngineeringTaskDecomposer,
    EngineeringPlanningContext,
)
from asep.application.session_context import SessionRuntimeContext
from asep.application.session_memory import SessionMemoryContext
from asep.projects import ProjectOperationalPlanSource


class StubRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="stub")

    def __init__(self, output: object = None, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.requests: list[AIRuntimeRequest] = []

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        serialized = self.output if isinstance(self.output, str) else json.dumps(self.output)
        return AIRuntimeResult(output=serialized, identity=self.identity)


def context() -> EngineeringPlanningContext:
    return EngineeringPlanningContext(
        execution_id="execution-1",
        instruction="Add GET /health and tests.",
        analysis=BoundedProjectAnalysis(
            languages=("Python",),
            frameworks=("FastAPI",),
            modules=("src",),
            entrypoints=("src/app/main.py",),
            has_tests=True,
            file_count=3,
            test_file_count=1,
        ),
        session_context=SessionRuntimeContext(session_id="session-1"),
        memory_context=SessionMemoryContext(),
    )


def valid_step(**updates) -> dict:
    result = {
        "step_id": "inspect",
        "operation": "inspect",
        "description": "Inspect the application.",
        "dependencies": [],
        "target_hints": ["src/app/main.py"],
        "validation_hints": [],
    }
    result.update(updates)
    return result


def test_valid_structured_output_maps_to_ai_decomposition() -> None:
    runtime = StubRuntime({"steps": [valid_step()]})
    result = CodexEngineeringTaskDecomposer(runtime).decompose(context())
    assert result.source is ProjectOperationalPlanSource.AI
    assert result.steps[0].target_hints == ("src/app/main.py",)
    request = runtime.requests[0]
    assert request.execution_mode.value == "read_only"
    assert request.workspace is None
    assert "root_path" not in request.instruction
    assert "execution-1" not in request.instruction


@pytest.mark.parametrize(
    "output",
    (
        "not-json",
        {"steps": [valid_step()], "extra": True},
        {"steps": [valid_step(operation="unknown")]},
        {"steps": [valid_step()] * 8},
        {"steps": [valid_step(), valid_step()]},
        {"steps": [valid_step(dependencies=["missing"])]},
        {"steps": [
            valid_step(step_id="one", dependencies=["two"]),
            valid_step(step_id="two", dependencies=["one"]),
        ]},
        {"steps": [valid_step(target_hints=["../secret"])]},
        {"steps": [valid_step(validation_hints=["shell-command"])]},
        {"steps": [{**valid_step(), "extra": True}]},
    ),
)
def test_invalid_provider_output_is_rejected_without_partial_acceptance(output) -> None:
    with pytest.raises(EngineeringDecompositionError):
        CodexEngineeringTaskDecomposer(StubRuntime(output)).decompose(context())


@pytest.mark.parametrize(
    "error",
    (RuntimeError("provider unavailable"), AIRuntimeTimeoutError("codex")),
)
def test_provider_failure_is_explicit_without_fallback(error: Exception) -> None:
    with pytest.raises(type(error)):
        CodexEngineeringTaskDecomposer(
            StubRuntime(error=error)
        ).decompose(context())


def test_explicit_fallback_is_observable() -> None:
    result = CodexEngineeringTaskDecomposer(
        StubRuntime("invalid"),
        fallback=DeterministicEngineeringTaskDecomposer(),
    ).decompose(context())
    assert result.source is ProjectOperationalPlanSource.DETERMINISTIC_FALLBACK
    assert result.steps[-1].validation_hints == ("pytest",)
