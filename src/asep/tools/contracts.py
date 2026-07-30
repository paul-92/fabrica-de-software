"""Portas públicas para Tools e sua execução."""

from typing import Protocol, runtime_checkable

from asep.tools.models import ToolContext, ToolMetadata, ToolRequest, ToolResult


@runtime_checkable
class Tool(Protocol):
    @property
    def metadata(self) -> ToolMetadata: ...

    def execute(self, request: ToolRequest, context: ToolContext) -> ToolResult:
        ...


@runtime_checkable
class ToolExecutor(Protocol):
    def execute(self, request: ToolRequest) -> ToolResult: ...


__all__ = ["Tool", "ToolExecutor"]

