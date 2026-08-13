from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeRequest,
    AIRuntimeResult,
    InMemoryAIRuntimeRegistry,
)
from asep.api import create_project_engineering_operational_composition
from asep.application import EngineeringFileChange
from asep.configuration import ApplicationSettings
from asep.projects import (
    ProjectExecution,
    ProjectExecutionStatus,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
)


class NeverCalledRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="unused")

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.calls += 1
        raise AssertionError("external implementation runtime must not be called")


class StructuredHealthProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def supports(self, step):
        return True

    def changes_for(self, context):
        self.calls.append(context.step.step_id)
        if context.step.step_id == "implement-change":
            return (EngineeringFileChange(
                relative_path="health.py",
                content="STATUS = {'status': 'ok'}\n",
            ),)
        if context.step.step_id == "update-tests":
            return (EngineeringFileChange(
                relative_path="tests/test_health.py",
                content=(
                    "from health import STATUS\n\n"
                    "def test_health():\n"
                    "    assert STATUS == {'status': 'ok'}\n"
                ),
            ),)
        return None


class UnsupportedProvider:
    def supports(self, step):
        return False

    def changes_for(self, context):
        raise AssertionError("unsupported provider must not be called")


class FailingWriteProvider:
    def supports(self, step):
        return True

    def changes_for(self, context):
        if context.step.step_id == "implement-change":
            return (EngineeringFileChange(
                relative_path="blocked",
                content="cannot replace a directory",
            ),)
        if context.step.step_id == "update-tests":
            return (EngineeringFileChange(
                relative_path="must-not-exist.py",
                content="VALUE = 1\n",
            ),)
        return None


class FallbackRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="fallback")

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.calls = 0

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.calls += 1
        (self.workspace / "fallback.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(exist_ok=True)
        (self.workspace / "tests" / "test_fallback.py").write_text(
            "def test_fallback(): assert True\n", encoding="utf-8"
        )
        return AIRuntimeResult(output="fallback", identity=self.identity)


def registry(runtime) -> InMemoryAIRuntimeRegistry:
    result = InMemoryAIRuntimeRegistry()
    result.register(runtime)
    return result


def project_and_session(composition, workspace: Path) -> tuple[str, str]:
    client = TestClient(composition.app)
    project = client.post(
        "/api/v1/projects",
        json={"name": "Fixture", "workspace_path": str(workspace)},
    ).json()
    session = client.post(
        f"/api/v1/projects/{project['project_id']}/sessions",
        json={"title": "Health"},
    ).json()
    return project["project_id"], session["session_id"]


def test_structured_change_is_strict_and_rejects_unsafe_paths() -> None:
    change = EngineeringFileChange(relative_path="src/app.py", content="x")
    with pytest.raises(ValidationError):
        change.content = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        EngineeringFileChange.model_validate({**change.model_dump(), "extra": True})
    for path in ("../secret", "/absolute", "C:/secret"):
        with pytest.raises(ValidationError, match="safe and relative"):
            EngineeringFileChange(relative_path=path, content="x")


def test_developer_agent_acceptance_writes_validates_and_approves(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="fixture"\ndependencies=["fastapi", "pytest"]\n',
        encoding="utf-8",
    )
    runtime = NeverCalledRuntime()
    provider = StructuredHealthProvider()
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(),
        runtime_registry=registry(runtime),
        implementation_provider=provider,
    )
    project_id, session_id = project_and_session(composition, tmp_path)

    from asep.application import ProjectAIRuntimeExecutionRequest
    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project_id,
            session_id=session_id,
            runtime_id="codex",
            instruction="Add GET /health returning status ok and create a test.",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )

    execution = result.execution
    assert runtime.calls == 0
    assert provider.calls == ["implement-change", "update-tests"]
    assert (tmp_path / "health.py").is_file()
    assert (tmp_path / "tests" / "test_health.py").is_file()
    assert execution.status is ProjectExecutionStatus.SUCCEEDED
    assert execution.validations[0].status.value == "passed"
    assert execution.quality_gate.decision.value == "APPROVED"
    assert len(execution.step_results) == 2
    assert all(item.execution_id == execution.execution_id for item in execution.step_results)
    assert all(item.executor == "developer_agent" for item in execution.step_results)
    assert {item.tool_id for item in execution.step_results} == {"write-file"}
    assert composition.quality_gate_results.list_by_run(execution.execution_id)


def test_unsupported_internal_plan_explicitly_uses_external_runtime(
    tmp_path: Path,
) -> None:
    runtime = FallbackRuntime(tmp_path)
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(),
        runtime_registry=registry(runtime),
        implementation_provider=UnsupportedProvider(),
    )
    project_id, session_id = project_and_session(composition, tmp_path)
    from asep.application import ProjectAIRuntimeExecutionRequest

    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project_id,
            session_id=session_id,
            runtime_id="codex",
            instruction="Implement a change.",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )
    assert runtime.calls == 1
    assert result.execution.step_results == ()
    assert result.runtime_result.identity.runtime_id == "codex"


def test_developer_agent_failure_blocks_dependent_write_and_validation(
    tmp_path: Path,
) -> None:
    (tmp_path / "blocked").mkdir()
    runtime = NeverCalledRuntime()
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(),
        runtime_registry=registry(runtime),
        implementation_provider=FailingWriteProvider(),
    )
    project_id, session_id = project_and_session(composition, tmp_path)
    from asep.application import ProjectAIRuntimeExecutionRequest

    with pytest.raises(RuntimeError, match="DeveloperAgent"):
        composition.project_engineering_execution.execute(
            ProjectAIRuntimeExecutionRequest(
                project_id=project_id,
                session_id=session_id,
                runtime_id="codex",
                instruction="Implement a change.",
                execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
            )
        )
    history = TestClient(composition.app).get(
        f"/api/v1/projects/{project_id}/sessions/{session_id}/executions"
    ).json()["items"]
    assert history[0]["status"] == "failed"
    assert history[0]["validations"] == []
    assert history[0]["quality_gate"] is None
    assert len(history[0]["step_results"]) == 1
    assert history[0]["step_results"][0]["succeeded"] is False
    assert not (tmp_path / "must-not-exist.py").exists()
    assert runtime.calls == 0
