from __future__ import annotations

from pathlib import Path

from asep.repair import (
    ControlledRepairExecutor,
    FailureAnalysis,
    PytestFailureAnalyzer,
    RepairChange,
    RepairLoopContext,
    RepairLoopPolicy,
    RepairLoopService,
    RepairPlan,
    RepairStatus,
)
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder
from asep.tools import InMemoryToolRegistry, RunTestsTool, ToolCapability, ToolId, ToolRequest, WriteFileTool
from asep.tools.execution_service import ToolExecutionService


def tool_service() -> ToolExecutionService:
    registry = InMemoryToolRegistry()
    registry.register(WriteFileTool())
    registry.register(RunTestsTool())
    return ToolExecutionService(
        registry, timeline=TimelineRecorder(InMemoryTimelineRepository())
    )


def run_pytest(service: ToolExecutionService, workspace: Path):
    return service.execute(ToolRequest(
        execution_id="initial-validation",
        tool_id=ToolId(value="run-tests"),
        capability=ToolCapability(id="test"),
        workspace=workspace,
        payload={"paths": ["tests/test_calculator.py"]},
        workflow_execution_id="repair-e2e",
    ))


class FixedPlanner:
    def __init__(self, content: str) -> None:
        self.content = content

    def plan(self, analysis: FailureAnalysis) -> RepairPlan:
        return RepairPlan(
            analysis=analysis,
            changes=(RepairChange(
                path="calculator.py", content=self.content, overwrite=True,
                reason="Corrigir a soma.",
            ),),
            test_paths=("tests/test_calculator.py",),
        )


class SequencePlanner:
    def __init__(self, contents: tuple[str, ...]) -> None:
        self._contents = iter(contents)

    def plan(self, analysis: FailureAnalysis) -> RepairPlan:
        return FixedPlanner(next(self._contents)).plan(analysis)


def workspace_with_bug(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "calculator.py").write_text(
        "def add(a, b):\n    return a - b\n", encoding="utf-8"
    )
    (tmp_path / "tests/test_calculator.py").write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    return tmp_path


def test_real_repair_pipeline_turns_red_pytest_green(tmp_path: Path) -> None:
    workspace = workspace_with_bug(tmp_path)
    tools = tool_service()
    initial = run_pytest(tools, workspace)
    assert initial.status.value == "failed"
    failure_output = f"{initial.output['stdout']}\n{initial.output['stderr']}"
    analysis = PytestFailureAnalyzer().analyze(failure_output)
    loop = RepairLoopService(
        FixedPlanner("def add(a, b):\n    return a + b\n"),
        ControlledRepairExecutor(tools, workspace),
    )
    result = loop.execute(RepairLoopContext(initial_analysis=analysis))
    assert result.status is RepairStatus.SUCCEEDED
    assert len(result.attempts) == 1
    assert "return a + b" in (workspace / "calculator.py").read_text(encoding="utf-8")
    assert "passed" in result.attempts[0].validation_output


def test_real_repair_pipeline_exhausts_when_bug_remains(tmp_path: Path) -> None:
    workspace = workspace_with_bug(tmp_path)
    tools = tool_service()
    initial = run_pytest(tools, workspace)
    analysis = PytestFailureAnalyzer().analyze(str(initial.output["stdout"]))
    result = RepairLoopService(
        FixedPlanner("def add(a, b):\n    return a - b\n"),
        ControlledRepairExecutor(tools, workspace),
    ).execute(RepairLoopContext(
        initial_analysis=analysis,
        policy=RepairLoopPolicy(max_attempts=2),
    ))
    assert result.status is RepairStatus.EXHAUSTED
    assert len(result.attempts) == 2


def test_real_repair_pipeline_reapplies_changed_plan_on_second_attempt(
    tmp_path: Path,
) -> None:
    workspace = workspace_with_bug(tmp_path)
    tools = tool_service()
    initial = run_pytest(tools, workspace)
    analysis = PytestFailureAnalyzer().analyze(str(initial.output["stdout"]))
    result = RepairLoopService(
        SequencePlanner((
            "def add(a, b):\n    return a - b\n",
            "def add(a, b):\n    return a + b\n",
        )),
        ControlledRepairExecutor(tools, workspace),
    ).execute(RepairLoopContext(
        initial_analysis=analysis,
        policy=RepairLoopPolicy(max_attempts=2),
    ))
    assert result.status is RepairStatus.SUCCEEDED
    assert [item.status for item in result.attempts] == [
        RepairStatus.FAILED,
        RepairStatus.SUCCEEDED,
    ]
