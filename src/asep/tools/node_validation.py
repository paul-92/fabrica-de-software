"""Controlled npm-script validation tools for Node projects."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path

from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessRunner,
    ProcessRunnerProtocol,
    ProcessStartError,
    ProcessTimeoutError,
)
from asep.tools.exceptions import (
    ToolExecutionError,
    ToolSecurityError,
    ToolTimeoutError,
    ToolValidationError,
)
from asep.tools.models import (
    ToolCapability,
    ToolContext,
    ToolError,
    ToolExecutionStatus,
    ToolId,
    ToolMetadata,
    ToolRequest,
    ToolResult,
)
from asep.tools.workspace import resolve_workspace_path

ExecutableResolver = Callable[[str], str | None]


def resolve_npm_executable(
    *, platform_name: str | None = None,
    resolver: ExecutableResolver = shutil.which,
) -> str:
    """Resolve npm once at the process boundary without invoking a shell."""
    executable = "npm.cmd" if (platform_name or os.name) == "nt" else "npm"
    resolved = resolver(executable)
    if resolved is None:
        raise ProcessExecutableNotFoundError(executable)
    return resolved


class NpmScriptValidationTool:
    """Run one constructor-controlled npm script in a confined package root."""

    def __init__(
        self,
        tool_id: str,
        capability: str,
        script: str,
        *,
        runner: ProcessRunnerProtocol | None = None,
        executable: str | None = None,
        executable_resolver: Callable[[], str] = resolve_npm_executable,
    ) -> None:
        self.metadata = ToolMetadata(
            id=ToolId(value=tool_id),
            name=f"Run npm {script}",
            description=f"Executes the controlled npm script '{script}'.",
            version="1.0.0",
            author="ASEP",
            category="validation",
            capabilities=(ToolCapability(id=capability),),
        )
        self._script = script
        self._runner = runner or ProcessRunner()
        self._executable = executable
        self._executable_resolver = executable_resolver

    def execute(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        if set(request.payload) - {"package_root"}:
            raise ToolExecutionError(
                str(request.tool_id), error_type="InvalidNodeValidationOptions"
            )
        package_root = request.payload.get("package_root", ".")
        if not isinstance(package_root, str):
            raise ToolExecutionError(
                str(request.tool_id), error_type="InvalidPackageRoot"
            )
        try:
            root = resolve_workspace_path(context.workspace, package_root)
        except ToolSecurityError:
            raise
        except ToolValidationError as exc:
            raise ToolExecutionError(
                str(request.tool_id), error_type="InvalidPackageRoot"
            ) from exc
        if not root.is_dir() or not (root / "package.json").is_file():
            raise ToolExecutionError(
                str(request.tool_id), error_type="PackageManifestNotFound"
            )

        try:
            executable = self._executable or self._executable_resolver()
            result = self._runner.run(
                (executable, "run", self._script),
                input_text="",
                timeout=request.timeout_seconds or 300.0,
                working_directory=root,
                environment={},
                encoding="utf-8",
            )
        except ProcessTimeoutError as exc:
            raise ToolTimeoutError(
                str(request.tool_id), error_type="ProcessTimeout", retryable=True
            ) from exc
        except (
            ProcessExecutableNotFoundError,
            ProcessInterruptedError,
            ProcessStartError,
        ) as exc:
            raise ToolExecutionError(
                str(request.tool_id), error_type=type(exc).__name__
            ) from exc

        output = {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": list(result.command),
        }
        if result.exit_code == 0:
            return ToolResult(
                execution_id=request.execution_id,
                tool_id=request.tool_id,
                status=ToolExecutionStatus.SUCCEEDED,
                output=output,
                duration_seconds=0,
                started_at=context.started_at,
                completed_at=context.started_at,
                attempts=context.attempt,
            )
        return ToolResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=ToolExecutionStatus.FAILED,
            output=output,
            duration_seconds=0,
            started_at=context.started_at,
            completed_at=context.started_at,
            attempts=context.attempt,
            error=ToolError(
                code="node_validation_failed",
                message="The controlled npm validation returned a non-zero exit code.",
            ),
        )


def node_validation_tools() -> tuple[NpmScriptValidationTool, ...]:
    return (
        NpmScriptValidationTool("typecheck", "typecheck", "typecheck"),
        NpmScriptValidationTool("vitest", "frontend_test", "test"),
        NpmScriptValidationTool("eslint", "lint", "lint"),
        NpmScriptValidationTool("next-build", "build", "build"),
    )


__all__ = [
    "NpmScriptValidationTool",
    "node_validation_tools",
    "resolve_npm_executable",
]
