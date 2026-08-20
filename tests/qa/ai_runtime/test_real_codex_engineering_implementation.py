from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil

import pytest

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    CodexAIRuntime,
    CodexAIRuntimeConfig,
)
from asep.ai_runtime.engineering_implementation import (
    AIRuntimeEngineeringImplementationProvider,
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


@pytest.mark.integration
def test_real_codex_produces_bounded_engineering_changes(tmp_path: Path) -> None:
    codex = shutil.which("codex")

    if codex is None:
        pytest.skip("Codex CLI is not available in PATH")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    step = ProjectOperationalPlanStep(
        step_id="implement-hello",
        operation=ProjectOperationalPlanOperation.IMPLEMENT,
        description="Create a minimal hello module.",
        dependencies=(),
        target_hints=("hello.py",),
        validation_hints=(),
    )

    plan = ProjectOperationalPlan(
        execution_id="real-codex-execution",
        steps=(step,),
        source=ProjectOperationalPlanSource.AI,
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
    )

    context = EngineeringImplementationContext(
        execution_id="real-codex-execution",
        workspace=workspace,
        organization_id="integration-test",
        user_id="integration-test",
        project_id="integration-test",
        session_id="integration-test",
        task=(
            "Create hello.py containing a function hello() "
            "that returns exactly the string 'Hello ASEP'."
        ),
        analysis=BoundedProjectAnalysis(),
        plan=plan,
        step=step,
        dependency_results=(),
    )

    runtime = CodexAIRuntime(
        CodexAIRuntimeConfig(
            workspace=workspace,
            executable=codex,
            timeout=120.0,
            model_id="codex-default",
        )
    )

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    assert provider.supports(step) is True

    result = provider.invoke_ai(context)

    assert result.identity.runtime_id == "codex"
    assert result.changes

    hello_changes = tuple(
        change
        for change in result.changes
        if change.relative_path.replace("\\", "/") == "hello.py"
    )

    assert hello_changes, (
        "Codex did not propose hello.py. "
        f"Returned paths: {[change.relative_path for change in result.changes]}"
    )

    change = hello_changes[0]

    assert "def hello" in change.content
    assert "Hello ASEP" in change.content

    # Critical architecture invariant:
    # the AIRuntime provider must only propose changes.
    assert not (workspace / "hello.py").exists()
