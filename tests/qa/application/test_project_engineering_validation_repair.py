from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.application import (
    BoundedProjectAnalysis,
    ProjectRepairService,
    ProjectValidationService,
)
from asep.projects import (
    ProjectValidationFailureCategory,
    ProjectValidationResult,
    ProjectValidationStatus,
    ProjectValidationStrategy,
)
from asep.projects import (
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
)
from asep.repair import DeterministicRepairPlanner, PytestFailureAnalyzer, RepairStatus
from asep.tools import (
    ToolExecutionStatus,
    ToolRequest,
    ToolResult,
)


class RecordingTools:
    def __init__(self, *, test_exit_code: int = 0) -> None:
        self.test_exit_code = test_exit_code
        self.requests: list[ToolRequest] = []

    def execute(self, request: ToolRequest) -> ToolResult:
        self.requests.append(request)
        now = datetime.now(UTC)
        if request.capability.id in {
            "test", "compile", "typecheck", "frontend_test", "lint", "build",
        }:
            succeeded = self.test_exit_code == 0
            return ToolResult(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                status=(
                    ToolExecutionStatus.SUCCEEDED
                    if succeeded
                    else ToolExecutionStatus.FAILED
                ),
                output={
                    "exit_code": self.test_exit_code,
                    "stdout": (
                        "1 passed" if succeeded
                        else (
                            "SyntaxError: invalid syntax"
                            if request.capability.id == "compile"
                            else "AssertionError: FAILED tests/test_app.py::test_app"
                        )
                    ),
                    "stderr": "",
                    "command": (
                        [
                            "python", "-m",
                            "compileall" if request.capability.id == "compile" else "pytest",
                            "." if request.capability.id == "compile" else "tests",
                        ]
                        if request.capability.id in {"test", "compile"}
                        else ["npm", "run", {
                            "typecheck": "typecheck",
                            "frontend_test": "test",
                            "lint": "lint",
                            "build": "build",
                        }[request.capability.id]]
                    ),
                },
                duration_seconds=0,
                started_at=now,
                completed_at=now,
                attempts=1,
                error=(
                    None
                    if succeeded
                    else {
                        "code": "tests_failed",
                        "message": "pytest failed",
                    }
                ),
            )
        return ToolResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=ToolExecutionStatus.SUCCEEDED,
            output={"path": request.payload["path"]},
            duration_seconds=0,
            started_at=now,
            completed_at=now,
            attempts=1,
        )


def validation_plan(*hints: str) -> ProjectOperationalPlan:
    return ProjectOperationalPlan(
        execution_id="execution-1",
        steps=(ProjectOperationalPlanStep(
            step_id="validate",
            operation=ProjectOperationalPlanOperation.VALIDATE,
            description="Validate",
            validation_hints=hints,
        ),),
        created_at=datetime.now(UTC),
    )


def test_validation_records_real_tool_facts_and_canonical_identity(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    tools = RecordingTools()

    result = ProjectValidationService(tools).validate(
        "execution-1", tmp_path, sequence=1
    )

    assert result.execution_id == "execution-1"
    assert result.command == ("python", "-m", "pytest", "tests")
    assert result.exit_code == 0
    assert result.status is ProjectValidationStatus.PASSED
    assert result.output == "1 passed"
    assert tools.requests[0].workflow_execution_id == "execution-1"
    assert tools.requests[0].payload["paths"] == ["tests"]


def test_validation_falls_back_to_bounded_project_pytest(tmp_path: Path) -> None:
    tools = RecordingTools(test_exit_code=1)

    result = ProjectValidationService(tools).validate(
        "execution-1", tmp_path, sequence=2
    )

    assert result.status is ProjectValidationStatus.FAILED
    assert result.exit_code == 1
    assert "FAILED tests/test_app.py" in result.output
    assert tools.requests[0].payload["paths"] == ["."]


@pytest.mark.parametrize("hints", (("pytest",), ()))
def test_plan_validation_selects_pytest_and_empty_hints_keep_safe_fallback(
    tmp_path: Path, hints: tuple[str, ...]
) -> None:
    tools = RecordingTools()
    results = ProjectValidationService(tools).validate_plan(
        "execution-1",
        tmp_path,
        validation_plan(*hints),
        start_sequence=3,
    )
    assert [(item.validator, item.sequence) for item in results] == [
        ("pytest", 3)
    ]
    assert len(tools.requests) == 1


def test_non_executable_validation_hint_is_rejected(tmp_path: Path) -> None:
    tools = RecordingTools()
    with pytest.raises(ValueError, match="not executable"):
        ProjectValidationService(tools).validate_plan(
            "execution-1",
            tmp_path,
                validation_plan("ruff"),
            start_sequence=1,
        )
    assert tools.requests == []


def test_strategy_is_strict_frozen_and_orders_allowlisted_validators(
    tmp_path: Path,
) -> None:
    service = ProjectValidationService(RecordingTools())
    strategy = service.strategy(
        "execution-1", tmp_path,
        validation_plan("pytest", "compileall"),
    )

    assert strategy.validators == ("compileall", "pytest")
    with pytest.raises(Exception):
        strategy.reason = "changed"  # type: ignore[misc]
    with pytest.raises(Exception):
        ProjectValidationStrategy.model_validate({
            **strategy.model_dump(), "arbitrary_command": "rm -rf ."
        })


def test_multiple_validators_stop_on_failure_and_classify_compile_error(
    tmp_path: Path,
) -> None:
    tools = RecordingTools(test_exit_code=1)
    service = ProjectValidationService(tools)
    strategy = service.strategy(
        "execution-1", tmp_path,
        validation_plan("pytest", "compileall"),
    )
    results = service.validate_strategy(strategy, tmp_path, start_sequence=1)

    assert [item.validator for item in results] == ["compileall"]
    analysis = service.analyze_failure(results[0])
    assert analysis.category is ProjectValidationFailureCategory.SYNTAX_OR_COMPILE_ERROR
    assert analysis.execution_id == "execution-1"


def test_repair_loop_is_limited_and_tool_requests_keep_execution_identity(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    tools = RecordingTools()
    repair = ProjectRepairService(
        PytestFailureAnalyzer(),
        DeterministicRepairPlanner(),
        tools,
    )
    analysis = repair.analyze(
        "FAILED tests/test_app.py::test_app - AssertionError"
    )

    result = repair.repair("execution-1", tmp_path, analysis)

    assert result.status is RepairStatus.SUCCEEDED
    assert len(result.attempts) == 1
    assert all(
        request.workflow_execution_id == "execution-1"
        for request in tools.requests
    )
    assert all(
        request.execution_id.startswith("execution-1-repair-1-")
        for request in tools.requests
    )


def test_node_validators_are_ordered_and_use_confined_package_root(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    tools = RecordingTools()
    service = ProjectValidationService(tools)
    strategy = service.strategy(
        "execution-1",
        tmp_path,
        validation_plan(
            "next_build", "eslint", "vitest", "pytest", "typecheck", "compileall"
        ),
    )

    results = service.validate_strategy(strategy, tmp_path, start_sequence=1)

    assert strategy.validators == (
        "compileall", "typecheck", "pytest", "vitest", "eslint", "next_build"
    )
    assert [item.validator for item in results] == list(strategy.validators)
    node_requests = [
        request for request in tools.requests
        if request.capability.id in {"typecheck", "frontend_test", "lint", "build"}
    ]
    assert [request.payload["package_root"] for request in node_requests] == [
        ".", ".", ".", "."
    ]


@pytest.mark.parametrize(
    ("validator", "output", "category"),
    (
        ("typecheck", "TS2322: Type error", "syntax_or_compile_error"),
        ("vitest", "Test failed", "test_failure"),
        ("vitest", "AssertionError", "assertion_failure"),
        ("eslint", "1 lint problem", "lint_failure"),
        ("next_build", "Failed to compile", "syntax_or_compile_error"),
        ("next_build", "Build worker exited", "build_failure"),
    ),
)
def test_node_failure_classification(
    validator: str, output: str, category: str,
) -> None:
    result = ProjectValidationResult(
        execution_id="execution-1",
        sequence=1,
        validator=validator,
        command=("npm", "run", "fixed"),
        exit_code=1,
        status=ProjectValidationStatus.FAILED,
        output=output,
        completed_at=datetime.now(UTC),
    )

    analysis = ProjectValidationService(RecordingTools()).analyze_failure(result)

    assert analysis.category.value == category


@pytest.mark.parametrize(
    ("changed_paths", "languages", "expected"),
    (
        (("backend/app.py",), ("Python",), ("compileall", "pytest")),
        (
            ("web/app/page.tsx",),
            ("TypeScript",),
            ("typecheck", "vitest", "eslint", "next_build"),
        ),
        (
            ("backend/app.py", "web/app/page.tsx"),
            ("Python", "TypeScript"),
            ("compileall", "typecheck", "pytest", "vitest", "eslint", "next_build"),
        ),
    ),
)
def test_strategy_selects_validators_by_changed_domain(
    tmp_path: Path, changed_paths: tuple[str, ...], languages: tuple[str, ...],
    expected: tuple[str, ...],
) -> None:
    for relative in changed_paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content", encoding="utf-8")
    web = tmp_path / "web"
    if "TypeScript" in languages:
        web.mkdir(exist_ok=True)
        (web / "package.json").write_text("{}", encoding="utf-8")
    analysis = BoundedProjectAnalysis(
        languages=languages,
        package_managers=("npm",) if "TypeScript" in languages else (),
        package_manifests=("web/package.json",) if "TypeScript" in languages else (),
        has_tests=True,
    )

    strategy = ProjectValidationService(RecordingTools()).strategy(
        "execution-1", tmp_path, validation_plan(),
        analysis=analysis, changed_paths=changed_paths,
    )

    assert strategy.validators == expected
    node_targets = {
        item.validator_id: item.targets for item in strategy.target_hints
        if item.validator_id in {"typecheck", "vitest", "eslint", "next_build"}
    }
    if node_targets:
        assert set(node_targets.values()) == {("web",)}


def test_strategy_rejects_ambiguous_package_roots(tmp_path: Path) -> None:
    for package in ("web-a", "web-b"):
        root = tmp_path / package
        root.mkdir()
        (root / "package.json").write_text("{}", encoding="utf-8")
        (root / "page.tsx").write_text("export default 1", encoding="utf-8")
    analysis = BoundedProjectAnalysis(
        languages=("TypeScript",),
        package_managers=("npm", "npm"),
        package_manifests=("web-a/package.json", "web-b/package.json"),
    )

    with pytest.raises(ValueError, match="one safe package root"):
        ProjectValidationService(RecordingTools()).strategy(
            "execution-1", tmp_path, validation_plan(), analysis=analysis,
            changed_paths=("web-a/page.tsx", "web-b/page.tsx"),
        )
