"""Bounded pytest validation for project engineering executions."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from asep.memory import MemoryFilter
from asep.projects import ProjectValidationResult, ProjectValidationStatus
from asep.tools import (
    ToolCapability,
    ToolExecutionStatus,
    ToolExecutor,
    ToolId,
    ToolRequest,
)

_MAX_PUBLIC_OUTPUT_CHARS = 20_000


class ProjectValidationCapability(Protocol):
    def validate(
        self,
        execution_id: str,
        workspace: Path,
        *,
        sequence: int,
        test_paths: tuple[str, ...] | None = None,
    ) -> ProjectValidationResult: ...


class ProjectValidationService:
    def __init__(self, tools: ToolExecutor) -> None:
        self._tools = tools
        self._filter = MemoryFilter()

    def validate(
        self,
        execution_id: str,
        workspace: Path,
        *,
        sequence: int,
        test_paths: tuple[str, ...] | None = None,
    ) -> ProjectValidationResult:
        selected = test_paths or self._discover_test_paths(workspace)
        result = self._tools.execute(ToolRequest(
            execution_id=f"{execution_id}-validation-{sequence}",
            tool_id=ToolId(value="run-tests"),
            capability=ToolCapability(id="test"),
            workspace=workspace,
            payload={"paths": list(selected)},
            metadata={"project_execution_id": execution_id},
            workflow_execution_id=execution_id,
        ))
        output = result.output if isinstance(result.output, Mapping) else {}
        exit_code = output.get("exit_code", -1)
        command = output.get("command", ())
        passed = (
            result.status is ToolExecutionStatus.SUCCEEDED
            and isinstance(exit_code, int)
            and exit_code == 0
        )
        return ProjectValidationResult(
            execution_id=execution_id,
            sequence=sequence,
            command=tuple(str(item) for item in command) or ("pytest",),
            exit_code=exit_code if isinstance(exit_code, int) else -1,
            status=(
                ProjectValidationStatus.PASSED
                if passed
                else ProjectValidationStatus.FAILED
            ),
            output=self._safe_output(output),
            completed_at=result.completed_at,
        )

    @staticmethod
    def _discover_test_paths(workspace: Path) -> tuple[str, ...]:
        return ("tests",) if (workspace / "tests").is_dir() else (".",)

    def _safe_output(self, output: Mapping[str, object]) -> str:
        combined = "\n".join(
            value.strip()
            for key in ("stdout", "stderr")
            if isinstance((value := output.get(key)), str) and value.strip()
        )
        safe, _, _ = self._filter.sanitize(combined, {})
        if len(safe) <= _MAX_PUBLIC_OUTPUT_CHARS:
            return safe
        return safe[:_MAX_PUBLIC_OUTPUT_CHARS] + "\n[output truncated]"


__all__ = ["ProjectValidationCapability", "ProjectValidationService"]
