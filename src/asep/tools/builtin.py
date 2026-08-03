"""Tools oficiais e restritas ao workspace da ASEP."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessResult,
    ProcessRunner,
    ProcessRunnerProtocol,
    ProcessStartError,
    ProcessTimeoutError,
)
from asep.tools.exceptions import ToolExecutionError, ToolTimeoutError
from asep.tools.models import (
    ToolCapability,
    ToolContext,
    ToolExecutionStatus,
    ToolError,
    ToolId,
    ToolMetadata,
    ToolRequest,
    ToolResult,
)
from asep.tools.workspace import (
    is_safe_discovered_path,
    resolve_workspace_path,
)


def _success(
    request: ToolRequest,
    context: ToolContext,
    output: Mapping[str, Any],
) -> ToolResult:
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

class ReadFileTool:
    metadata = ToolMetadata(
        id=ToolId(value="read-file"),
        name="Read File",
        description="Lê um arquivo UTF-8 dentro do workspace.",
        version="1.0.0",
        author="ASEP",
        category="filesystem",
        capabilities=(ToolCapability(id="read_file"),),
    )

    def execute(
        self,
        request: ToolRequest,
        context: ToolContext,
    ) -> ToolResult:
        path = resolve_workspace_path(
            context.workspace,
            request.payload.get("path", ""),
        )

        if not path.is_file():
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="NotAFile",
            )

        try:
            content = path.read_text(
                encoding="utf-8",
            )
        except UnicodeDecodeError as exc:
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="InvalidUtf8",
            ) from exc

        return _success(
            request,
            context,
            {
                "path": path.relative_to(
                    context.workspace
                ).as_posix(),
                "content": content,
            },
        )

class WriteFileTool:
    metadata = ToolMetadata(
        id=ToolId(value="write-file"),
        name="Write File",
        description="Escreve um arquivo UTF-8 dentro do workspace.",
        version="1.0.0",
        author="ASEP",
        category="filesystem",
        capabilities=(ToolCapability(id="write_file"),),
    )

    def execute(
        self,
        request: ToolRequest,
        context: ToolContext,
    ) -> ToolResult:
        relative_path = request.payload.get("path", "")
        content = request.payload.get("content")
        overwrite = request.payload.get("overwrite", False)

        if not isinstance(content, str):
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="InvalidContent",
            )

        if not isinstance(overwrite, bool):
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="InvalidOverwriteFlag",
            )

        path = resolve_workspace_path(
            context.workspace,
            relative_path,
            must_exist=False,
        )

        if path.exists() and not path.is_file():
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="NotAFile",
            )

        if path.exists() and not overwrite:
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="FileAlreadyExists",
            )

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                content,
                encoding="utf-8",
            )
        except OSError as exc:
            raise ToolExecutionError(
                str(request.tool_id),
                error_type="WriteFailed",
            ) from exc

        return _success(
            request,
            context,
            {
                "path": path.relative_to(
                    context.workspace
                ).as_posix(),
                "bytes_written": len(
                    content.encode("utf-8")
                ),
                "overwritten": overwrite,
            },
        )

class ListDirectoryTool:
    metadata = ToolMetadata(
        id=ToolId(value="list-directory"),
        name="List Directory",
        description="Lista entradas seguras de um diretório do workspace.",
        version="1.0.0",
        author="ASEP",
        category="filesystem",
        capabilities=(ToolCapability(id="directory"),),
    )

    def execute(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        path_value = request.payload.get("path", ".")
        path = resolve_workspace_path(context.workspace, path_value)
        if not path.is_dir():
            raise ToolExecutionError(
                str(request.tool_id), error_type="NotADirectory"
            )
        entries = [
            {
                "path": child.relative_to(context.workspace).as_posix(),
                "type": "directory" if child.is_dir() else "file",
            }
            for child in sorted(path.iterdir(), key=lambda item: item.name)
            if is_safe_discovered_path(context.workspace, child)
        ]
        return _success(request, context, {"entries": entries})


class SearchFilesTool:
    metadata = ToolMetadata(
        id=ToolId(value="search-files"),
        name="Search Files",
        description="Pesquisa nome, extensão ou texto no workspace.",
        version="1.0.0",
        author="ASEP",
        category="filesystem",
        capabilities=(ToolCapability(id="search"),),
    )

    def execute(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        root = resolve_workspace_path(
            context.workspace, request.payload.get("path", ".")
        )
        if not root.is_dir():
            raise ToolExecutionError(
                str(request.tool_id), error_type="NotADirectory"
            )
        name = request.payload.get("name")
        extension = request.payload.get("extension")
        text = request.payload.get("text")
        if not any(
            isinstance(value, str) and value
            for value in (name, extension, text)
        ):
            raise ToolExecutionError(
                str(request.tool_id), error_type="EmptySearch"
            )
        normalized_extension = (
            extension
            if not isinstance(extension, str) or extension.startswith(".")
            else f".{extension}"
        )
        matches: list[str] = []
        for candidate in sorted(root.rglob("*")):
            if len(matches) >= 1000:
                break
            if not candidate.is_file() or not is_safe_discovered_path(
                context.workspace, candidate
            ):
                continue
            if isinstance(name, str) and name not in candidate.name:
                continue
            if (
                isinstance(normalized_extension, str)
                and candidate.suffix != normalized_extension
            ):
                continue
            if isinstance(text, str):
                try:
                    if text not in candidate.read_text(encoding="utf-8"):
                        continue
                except (OSError, UnicodeDecodeError):
                    continue
            matches.append(candidate.relative_to(context.workspace).as_posix())
        return _success(request, context, {"matches": matches})


class ReadDocumentationTool:
    metadata = ToolMetadata(
        id=ToolId(value="read-documentation"),
        name="Read Documentation",
        description="Lê documentação UTF-8 exclusivamente em docs/.",
        version="1.0.0",
        author="ASEP",
        category="documentation",
        capabilities=(ToolCapability(id="documentation"),),
    )

    def execute(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        docs = resolve_workspace_path(context.workspace, "docs")
        requested = request.payload.get("path", "")
        path = resolve_workspace_path(docs, requested)
        if not path.is_file():
            raise ToolExecutionError(
                str(request.tool_id), error_type="NotAFile"
            )
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ToolExecutionError(
                str(request.tool_id), error_type="InvalidUtf8"
            ) from exc
        return _success(
            request,
            context,
            {
                "path": path.relative_to(context.workspace).as_posix(),
                "content": content,
            },
        )


class RunTestsTool:
    metadata = ToolMetadata(
        id=ToolId(value="run-tests"),
        name="Run Tests",
        description="Executa pytest com argumentos restritos ao workspace.",
        version="1.0.0",
        author="ASEP",
        category="testing",
        capabilities=(ToolCapability(id="test"),),
    )

    def __init__(
        self,
        runner: ProcessRunnerProtocol | None = None,
        *,
        executable: str | None = None,
    ) -> None:
        self._runner = runner or ProcessRunner()
        self._executable = executable or sys.executable

    def execute(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        paths = request.payload.get("paths", ["tests"])
        if not isinstance(paths, (list, tuple)) or not paths:
            raise ToolExecutionError(
                str(request.tool_id), error_type="InvalidTestPaths"
            )
        safe_paths: list[str] = []
        for value in paths:
            if not isinstance(value, str):
                raise ToolExecutionError(
                    str(request.tool_id), error_type="InvalidTestPaths"
                )
            path = resolve_workspace_path(context.workspace, value)
            safe_paths.append(path.relative_to(context.workspace).as_posix())
        command = (self._executable, "-m", "pytest", *safe_paths)
        timeout = request.timeout_seconds or 300.0
        try:
            result = self._runner.run(
                command,
                input_text="",
                timeout=timeout,
                working_directory=context.workspace,
                environment={},
                encoding="utf-8",
            )
        except ProcessTimeoutError as exc:
            raise ToolTimeoutError(
                str(request.tool_id),
                error_type="ProcessTimeout",
                retryable=True,
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
            return _success(request, context, output)
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
                code="tests_failed",
                message="A suíte de testes retornou código diferente de zero.",
            ),
        )


__all__ = [
    "ListDirectoryTool",
    "ReadDocumentationTool",
    "ReadFileTool",
    "RunTestsTool",
    "SearchFilesTool",
    "WriteFileTool",
]
