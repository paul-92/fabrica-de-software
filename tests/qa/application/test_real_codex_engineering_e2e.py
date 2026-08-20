from __future__ import annotations

from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    CodexAIRuntime,
    CodexAIRuntimeConfig,
    InMemoryAIRuntimeRegistry,
)
from asep.ai_runtime.engineering_implementation import (
    AIRuntimeEngineeringImplementationProvider,
)
from asep.api import create_project_engineering_operational_composition
from asep.application import ProjectAIRuntimeExecutionRequest
from asep.configuration import ApplicationSettings
from asep.projects import ProjectExecutionStatus


@pytest.mark.integration
def test_real_codex_implementation_is_written_by_developer_agent(
    tmp_path: Path,
) -> None:
    codex = shutil.which("codex")

    if codex is None:
        pytest.skip("Codex CLI is not available in PATH")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Give the analyzer a minimal Python project.
    (workspace / "pyproject.toml").write_text(
        '[project]\n'
        'name = "real-codex-e2e"\n'
        'version = "0.1.0"\n',
        encoding="utf-8",
    )

    runtime = CodexAIRuntime(
        CodexAIRuntimeConfig(
            workspace=workspace,
            executable=codex,
            timeout=120.0,
            model_id="codex-default",
        )
    )

    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)

    provider = AIRuntimeEngineeringImplementationProvider(runtime)

    composition = create_project_engineering_operational_composition(
        ApplicationSettings(
            hosted_root=tmp_path / "hosted",
        ),
        runtime_registry=registry,
        implementation_provider=provider,
    )

    client = TestClient(composition.app)

    project = client.post(
        "/api/v1/projects",
        json={
            "name": "Real Codex E2E",
            "workspace_path": str(workspace),
        },
    ).json()

    session = client.post(
        f"/api/v1/projects/{project['project_id']}/sessions",
        json={"title": "Real Codex engineering E2E"},
    ).json()

    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project["project_id"],
            session_id=session["session_id"],
            runtime_id="codex",
            instruction=(
                "Create hello.py containing a function hello() "
                "that returns exactly the string 'Hello ASEP'."
            ),
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )

    execution = result.execution

    # The controlled engineering pipeline must succeed.
    assert execution.status is ProjectExecutionStatus.SUCCEEDED

    # The implementation must have been executed as bounded plan steps.
    assert execution.step_results
    assert all(
        item.executor == "developer_agent"
        for item in execution.step_results
    )
    assert {
        item.tool_id
        for item in execution.step_results
    } == {"write-file"}

    # The final mutation must now exist in the workspace.
    hosted_workspace = (
        tmp_path
        / "hosted"
        / "legacy-local"
        / project["project_id"]
        / "workspace"
    )

    hello_file = hosted_workspace / "hello.py"

    assert hello_file.is_file(), (
        f"Expected DeveloperAgent output at {hello_file}"
    )
    assert not (workspace / "hello.py").exists()

    content = hello_file.read_text(encoding="utf-8")

    assert "def hello" in content
    assert "Hello ASEP" in content

    # The execution must retain the controlled validation result.
    assert execution.validations
    assert all(
        validation.status.value == "passed"
        for validation in execution.validations
    )

    assert execution.quality_gate is not None
    assert execution.quality_gate.decision.value == "APPROVED"
