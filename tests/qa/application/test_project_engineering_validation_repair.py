from datetime import UTC, datetime
from pathlib import Path

from asep.application import ProjectRepairService, ProjectValidationService
from asep.projects import ProjectValidationStatus
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
        if request.capability.id == "test":
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
                    "stdout": "1 passed" if succeeded else "FAILED tests/test_app.py::test_app",
                    "stderr": "",
                    "command": ["python", "-m", "pytest", "tests"],
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
