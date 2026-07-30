"""Validação prévia e independente de Tool concreta."""

from pathlib import Path

from asep.tools.contracts import Tool
from asep.tools.exceptions import (
    ToolCapabilityNotSupportedError,
    ToolNotRegisteredError,
    ToolValidationError,
)
from asep.tools.models import ToolExecutionPolicy, ToolRequest
from asep.tools.registry import ToolRegistry
from asep.tools.workspace import validated_workspace


class ToolValidator:
    def validate(
        self,
        request: ToolRequest,
        policy: ToolExecutionPolicy,
        registry: ToolRegistry,
    ) -> tuple[Tool, Path]:
        if not isinstance(request, ToolRequest):
            raise ToolValidationError("request deve ser ToolRequest.")
        if not isinstance(policy, ToolExecutionPolicy):
            raise ToolValidationError("policy deve ser ToolExecutionPolicy.")
        try:
            tool = registry.resolve(request.tool_id)
        except ToolNotRegisteredError:
            raise
        if request.capability.id not in {
            item.id for item in tool.metadata.capabilities
        }:
            raise ToolCapabilityNotSupportedError(
                f"Tool {request.tool_id} não suporta "
                f"{request.capability.id}."
            )
        workspace = validated_workspace(request.workspace)
        return tool, workspace


__all__ = ["ToolValidator"]
