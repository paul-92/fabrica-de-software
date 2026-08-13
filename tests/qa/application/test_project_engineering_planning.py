from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application import (
    BoundedProjectAnalysis,
    DeterministicEngineeringTaskDecomposer,
    EngineeringDecomposition,
    EngineeringPlanningContext,
    ProjectEngineeringPlanningService,
    ProjectEngineeringPlanValidator,
)
from asep.application.session_context import SessionRuntimeContext
from asep.application.session_memory import SessionMemoryContext
from asep.project_analysis import ProjectAnalyzer
from asep.projects import (
    ProjectExecution,
    ProjectExecutionStatus,
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
    ProjectOperationalPlanSource,
)

NOW = datetime(2026, 8, 12, tzinfo=UTC)


def execution(instruction: str = "Add GET /health and tests.") -> ProjectExecution:
    return ProjectExecution(
        execution_id="execution-1",
        session_id="session-1",
        project_id="project-1",
        runtime_id="codex",
        instruction=instruction,
        execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        status=ProjectExecutionStatus.RUNNING,
        created_at=NOW,
    )


def step(step_id: str, **updates) -> ProjectOperationalPlanStep:
    return ProjectOperationalPlanStep(
        step_id=step_id,
        operation=ProjectOperationalPlanOperation.INSPECT,
        description=step_id,
        **updates,
    )


def plan(*steps: ProjectOperationalPlanStep) -> ProjectOperationalPlan:
    return ProjectOperationalPlan(
        execution_id="execution-1", steps=steps, created_at=NOW
    )


def write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def fastapi_fixture(root: Path) -> None:
    write(
        root / "pyproject.toml",
        '[project]\nname="fixture"\ndependencies=["fastapi", "pytest"]\n',
    )
    write(root / "src/app/main.py", "from fastapi import FastAPI\napp=FastAPI()\n")
    write(root / "tests/test_health.py", "def test_placeholder(): assert True\n")


def test_operational_step_is_strict_frozen_and_historical_defaults_work() -> None:
    current = step("inspect")
    assert current.dependencies == current.target_hints == current.validation_hints == ()
    with pytest.raises((FrozenInstanceError, ValidationError)):
        current.description = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ProjectOperationalPlanStep.model_validate(
            {**current.model_dump(), "unsupported": True}
        )


def test_operational_plan_limits_and_graph_validation() -> None:
    with pytest.raises(ValidationError):
        plan(*(step(f"step-{index}") for index in range(8)))
    with pytest.raises(ValidationError, match="unique"):
        plan(step("same"), step("same"))
    validator = ProjectEngineeringPlanValidator()
    with pytest.raises(ValueError, match="does not exist"):
        validator.validate(plan(step("one", dependencies=("missing",))))
    with pytest.raises(ValueError, match="itself"):
        validator.validate(plan(step("one", dependencies=("one",))))
    with pytest.raises(ValueError, match="acyclic"):
        validator.validate(plan(
            step("one", dependencies=("two",)),
            step("two", dependencies=("one",)),
        ))


@pytest.mark.parametrize("hint", ("../secret", "/absolute", "C:/secret", "safe/../../secret"))
def test_unsafe_target_hints_are_rejected(hint: str) -> None:
    with pytest.raises(ValueError, match="safe relative"):
        ProjectEngineeringPlanValidator().validate(
            plan(step("inspect", target_hints=(hint,)))
        )


def test_unknown_validation_hint_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        ProjectEngineeringPlanValidator().validate(
            plan(step("validate", validation_hints=("arbitrary-command",)))
        )


def test_bounded_analysis_contains_only_planning_facts(tmp_path: Path) -> None:
    fastapi_fixture(tmp_path)
    bounded = BoundedProjectAnalysis.from_domain(ProjectAnalyzer().analyze(tmp_path))
    payload = bounded.model_dump(mode="json")
    assert bounded.frameworks == ("FastAPI",)
    assert bounded.entrypoints == ("src/app/main.py",)
    assert bounded.has_tests is True
    assert bounded.test_file_count == 1
    assert "root_path" not in payload
    assert "files" not in payload
    assert str(tmp_path.resolve()) not in str(payload)
    with pytest.raises(ValidationError):
        BoundedProjectAnalysis.model_validate({**payload, "root_path": str(tmp_path)})


class RecordingDecomposer:
    def __init__(self, steps: tuple[ProjectOperationalPlanStep, ...]) -> None:
        self.steps = steps
        self.context: EngineeringPlanningContext | None = None

    def decompose(self, context: EngineeringPlanningContext):
        self.context = context
        return EngineeringDecomposition(
            steps=self.steps,
            source=ProjectOperationalPlanSource.DETERMINISTIC,
        )


def test_planning_service_passes_bounded_context_and_returns_detached_plan(
    tmp_path: Path,
) -> None:
    fastapi_fixture(tmp_path)
    source = step("inspect", target_hints=("src/app/main.py",))
    decomposer = RecordingDecomposer((source,))
    service = ProjectEngineeringPlanningService(ProjectAnalyzer(), decomposer)

    result = service.plan(
        execution(), tmp_path, SessionRuntimeContext(session_id="session-1"),
        SessionMemoryContext(),
    )

    assert result.execution_id == "execution-1"
    assert result.steps[0] == source
    assert result.steps[0] is not source
    assert decomposer.context is not None
    assert decomposer.context.analysis.frameworks == ("FastAPI",)
    assert not hasattr(decomposer.context.analysis, "root_path")


def test_planning_service_always_validates_decomposer_output(tmp_path: Path) -> None:
    decomposer = RecordingDecomposer((
        step("implement", dependencies=("missing",)),
    ))
    service = ProjectEngineeringPlanningService(ProjectAnalyzer(), decomposer)
    with pytest.raises(ValueError, match="does not exist"):
        service.plan(
            execution(), tmp_path,
            SessionRuntimeContext(session_id="session-1"),
            SessionMemoryContext(),
        )


def test_reference_health_plan_is_useful_bounded_and_deterministic(tmp_path: Path) -> None:
    fastapi_fixture(tmp_path)
    service = ProjectEngineeringPlanningService(
        ProjectAnalyzer(), DeterministicEngineeringTaskDecomposer()
    )
    args = (
        execution(), tmp_path, SessionRuntimeContext(session_id="session-1"),
        SessionMemoryContext(),
    )
    first = service.plan(*args)
    second = service.plan(*args)
    assert first == second
    assert len(first.steps) == 6
    assert first.steps[0].target_hints == ("src/app/main.py", "src")
    assert first.steps[-1].validation_hints == ("pytest",)
    assert first.steps[-1].dependencies == ("update-tests",)


def test_task_description_scenario_has_multiple_dependencies(tmp_path: Path) -> None:
    fastapi_fixture(tmp_path)
    service = ProjectEngineeringPlanningService(
        ProjectAnalyzer(), DeterministicEngineeringTaskDecomposer()
    )
    result = service.plan(
        execution("Add optional description to Task, update API and tests."),
        tmp_path,
        SessionRuntimeContext(session_id="session-1"),
        SessionMemoryContext(),
    )
    implement = next(item for item in result.steps if item.step_id == "implement-change")
    tests = next(item for item in result.steps if item.step_id == "update-tests")
    assert "description" in implement.description
    assert tests.dependencies == ("inspect-tests", "implement-change")
