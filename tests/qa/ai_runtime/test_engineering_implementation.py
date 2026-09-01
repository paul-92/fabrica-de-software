

from __future__ import annotations
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from asep.ai_runtime import (
    AIRuntimeCapability,
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeResult,
    AIRuntimeUsage,
)
from asep.ai_runtime.engineering_implementation import (
    AIRuntimeEngineeringImplementationProvider,
    EngineeringImplementationError,
)
from asep.application.project_engineering_agent_execution import (
    EngineeringImplementationContext,
)
from asep.application.project_engineering_planning import BoundedProjectAnalysis
from asep.projects import (
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanSource,
    ProjectOperationalPlanStep,
)


class StubRuntime:
    def __init__(self, output: str) -> None:
        self.output = output
        self.requests = []

        self._identity = AIRuntimeIdentity(
            runtime_id="stub-runtime",
            model_id="stub-model",
            capabilities=(
                AIRuntimeCapability(id="text-generation"),
                AIRuntimeCapability(id="code-reasoning"),
            ),
        )

    @property
    def identity(self) -> AIRuntimeIdentity:
        return self._identity

    def execute(self, request):
        self.requests.append(request)

        return AIRuntimeResult(
            output=self.output,
            identity=self.identity,
            usage=AIRuntimeUsage(
                input_units=10,
                output_units=20,
                total_units=30,
            ),
            metadata={
                "provider_request_id": "request-123",
            },
        )


def implementation_step() -> ProjectOperationalPlanStep:
    return ProjectOperationalPlanStep(
        step_id="implement-1",
        operation=ProjectOperationalPlanOperation.IMPLEMENT,
        description="Create application module",
        dependencies=(),
        target_hints=("src/example.py",),
        validation_hints=(),
    )


def inspect_step() -> ProjectOperationalPlanStep:
    return ProjectOperationalPlanStep(
        step_id="inspect-1",
        operation=ProjectOperationalPlanOperation.INSPECT,
        description="Inspect application",
        dependencies=(),
        target_hints=("src",),
        validation_hints=(),
    )


def context(workspace: Path) -> EngineeringImplementationContext:
    step = implementation_step()

    plan = ProjectOperationalPlan(
        execution_id="execution-1",
        steps=(step,),
        source=ProjectOperationalPlanSource.AI,
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
    )

    return EngineeringImplementationContext(
        execution_id="execution-1",
        workspace=workspace,
        organization_id="organization-1",
        user_id="user-1",
        project_id="project-1",
        session_id="session-1",
        task="Create an example module",
        analysis=BoundedProjectAnalysis(),
        plan=plan,
        step=step,
        dependency_results=(),
    )


def test_supports_only_implementation_steps():
    runtime = StubRuntime(
        json.dumps(
            {
                "changes": [
                    {
                        "relative_path": "src/example.py",
                        "content": "print('hello')",
                        "operation": "create_or_replace",
                    }
                ]
            }
        )
    )

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    assert provider.supports(implementation_step()) is True
    assert provider.supports(inspect_step()) is False


def test_invokes_runtime_in_read_only_mode(tmp_path: Path):
    runtime = StubRuntime(
        json.dumps(
            {
                "changes": [
                    {
                        "relative_path": "src/example.py",
                        "content": "print('hello')",
                        "operation": "create_or_replace",
                    }
                ]
            }
        )
    )

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    provider.invoke_ai(context(tmp_path))

    assert len(runtime.requests) == 1
    request = runtime.requests[0]

    assert request.execution_mode is AIRuntimeExecutionMode.READ_ONLY
    assert request.workspace == tmp_path.resolve()
    assert request.metadata["purpose"] == "project_engineering_implementation"


def test_valid_runtime_output_becomes_engineering_file_change(tmp_path: Path):
    runtime = StubRuntime(
        json.dumps(
            {
                "changes": [
                    {
                        "relative_path": "src/example.py",
                        "content": "print('hello')",
                        "operation": "create_or_replace",
                    }
                ]
            }
        )
    )

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    result = provider.invoke_ai(context(tmp_path))

    assert len(result.changes) == 1
    assert result.changes[0].relative_path == "src/example.py"
    assert result.changes[0].content == "print('hello')"
    assert result.changes[0].operation.value == "create_or_replace"


def test_preserves_runtime_identity_usage_and_request_id(tmp_path: Path):
    runtime = StubRuntime(
        json.dumps(
            {
                "changes": [
                    {
                        "relative_path": "src/example.py",
                        "content": "print('hello')",
                        "operation": "create_or_replace",
                    }
                ]
            }
        )
    )

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    result = provider.invoke_ai(context(tmp_path))

    assert result.identity == runtime.identity
    assert result.provider == "stub-runtime"

    assert result.usage is not None
    assert result.usage.input_units == 10
    assert result.usage.output_units == 20
    assert result.usage.total_units == 30

    assert result.provider_request_id == "request-123"
    assert result.already_metered is False



def test_empty_changes_is_valid_noop_candidate(tmp_path: Path):
    runtime = StubRuntime('{"changes":[]}')

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    result = provider.invoke_ai(context(tmp_path))

    assert result.changes == ()



@pytest.mark.parametrize(
    "output",
    [
        "not-json",
        "{}",
        '{"changes":[{"relative_path":"../unsafe.py","content":"bad"}]}',
        '{"unexpected":"value"}',
    ],
)
def test_invalid_runtime_output_is_rejected(output: str, tmp_path: Path):
    runtime = StubRuntime(output)

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    with pytest.raises(EngineeringImplementationError):
        provider.invoke_ai(context(tmp_path))
