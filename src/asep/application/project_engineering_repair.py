"""One-attempt repair boundary for project engineering executions."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from asep.repair import (
    ControlledRepairExecutor,
    FailureAnalysis,
    FailureAnalyzer,
    RepairLoopContext,
    RepairLoopPolicy,
    RepairLoopService,
    RepairPlanner,
    RepairResult,
)
from asep.tools import ToolExecutor


class ProjectRepairCapability(Protocol):
    def analyze(self, failure_output: str) -> FailureAnalysis: ...

    def repair(
        self,
        execution_id: str,
        workspace: Path,
        analysis: FailureAnalysis,
    ) -> RepairResult: ...


class ProjectRepairService:
    def __init__(
        self,
        analyzer: FailureAnalyzer,
        planner: RepairPlanner,
        tools: ToolExecutor,
    ) -> None:
        self._analyzer = analyzer
        self._planner = planner
        self._tools = tools

    def analyze(self, failure_output: str) -> FailureAnalysis:
        return self._analyzer.analyze(failure_output)

    def repair(
        self,
        execution_id: str,
        workspace: Path,
        analysis: FailureAnalysis,
    ) -> RepairResult:
        executor = ControlledRepairExecutor(
            self._tools,
            workspace,
            workflow_execution_id=execution_id,
            execution_prefix=f"{execution_id}-repair",
        )
        return RepairLoopService(self._planner, executor).execute(
            RepairLoopContext(
                initial_analysis=analysis,
                policy=RepairLoopPolicy(max_attempts=1),
            )
        )


__all__ = ["ProjectRepairCapability", "ProjectRepairService"]
