from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from asep.repair import (
    ControlledRepairExecutor,
    FailureAnalysis,
    RepairChange,
    RepairPlan,
    RepairStatus,
)
from asep.tools.exceptions import ToolExecutionError
from asep.tools.models import (
    ToolError,
    ToolExecutionStatus,
    ToolId,
    ToolRequest,
    ToolResult,
)


def tool_result(
    request: ToolRequest,
    status: ToolExecutionStatus = ToolExecutionStatus.SUCCEEDED,
    *,
    output=None,
) -> ToolResult:
    now = datetime.now(UTC)
    return ToolResult(
        execution_id=request.execution_id,
        tool_id=request.tool_id,
        status=status,
        output=output or {},
        duration_seconds=0,
        started_at=now,
        completed_at=now,
        attempts=1,
        error=(
            None
            if status is ToolExecutionStatus.SUCCEEDED
            else ToolError(code="failed", message="Falha controlada.")
        ),
    )


class FakeToolExecutor:
    def __init__(self, *, fail_write=False, fail_tests=False, raises=False):
        self.requests: list[ToolRequest] = []
        self.fail_write = fail_write
        self.fail_tests = fail_tests
        self.raises = raises

    def execute(self, request: ToolRequest) -> ToolResult:
        self.requests.append(request)
        if self.raises:
            raise ToolExecutionError(str(request.tool_id), error_type="Fake")
        if request.capability.id == "write_file" and self.fail_write:
            return tool_result(request, ToolExecutionStatus.FAILED)
        if request.capability.id == "test":
            return tool_result(
                request,
                ToolExecutionStatus.FAILED if self.fail_tests else ToolExecutionStatus.SUCCEEDED,
                output={"stdout": "pytest stdout", "stderr": "pytest stderr"},
            )
        return tool_result(request)


def plan(*changes: RepairChange, test_paths=("tests",)) -> RepairPlan:
    return RepairPlan(
        analysis=FailureAnalysis(summary="Falha funcional."),
        changes=changes,
        test_paths=test_paths,
    )


def change(path: str) -> RepairChange:
    return RepairChange(path=path, content="fixed\n", reason="Corrigir.")


def test_executor_applies_change_then_runs_custom_tests(tmp_path: Path) -> None:
    tools = FakeToolExecutor()
    result = ControlledRepairExecutor(tools, tmp_path).execute(
        plan(change("calculator.py"), test_paths=("qa/test_calc.py",))
    )

    assert result.status is RepairStatus.SUCCEEDED
    assert [item.capability.id for item in tools.requests] == ["write_file", "test"]
    assert tools.requests[-1].payload["paths"] == ["qa/test_calc.py"]
    assert result.attempts[0].validation_output == "pytest stdout\npytest stderr"
    assert result.final_analysis is not None


def test_executor_applies_all_changes_before_validation(tmp_path: Path) -> None:
    tools = FakeToolExecutor()
    result = ControlledRepairExecutor(tools, tmp_path).execute(
        plan(change("a.py"), change("b.py"))
    )
    assert result.status is RepairStatus.SUCCEEDED
    assert [item.capability.id for item in tools.requests] == [
        "write_file", "write_file", "test"
    ]


def test_executor_fails_without_validation_when_write_fails(tmp_path: Path) -> None:
    tools = FakeToolExecutor(fail_write=True)
    result = ControlledRepairExecutor(tools, tmp_path).execute(plan(change("a.py")))
    assert result.status is RepairStatus.FAILED
    assert len(tools.requests) == 1


def test_executor_fails_and_captures_output_when_pytest_fails(tmp_path: Path) -> None:
    tools = FakeToolExecutor(fail_tests=True)
    result = ControlledRepairExecutor(tools, tmp_path).execute(plan(change("a.py")))
    assert result.status is RepairStatus.FAILED
    assert result.attempts[0].validation_output == "pytest stdout\npytest stderr"


def test_executor_converts_tool_service_exception_to_failed(tmp_path: Path) -> None:
    result = ControlledRepairExecutor(FakeToolExecutor(raises=True), tmp_path).execute(
        plan(change("a.py"))
    )
    assert result.status is RepairStatus.FAILED


def test_executor_has_no_direct_filesystem_operations() -> None:
    source = Path("src/asep/repair/executor.py").read_text(encoding="utf-8")
    assert ".write_text(" not in source
    assert "subprocess" not in source

