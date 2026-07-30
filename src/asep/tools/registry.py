"""Registry determinístico e sem estado global para Tools."""

from typing import Protocol, runtime_checkable

from asep.tools.contracts import Tool
from asep.tools.exceptions import (
    InvalidToolRegistrationError,
    ToolAlreadyRegisteredError,
    ToolNotRegisteredError,
)
from asep.tools.models import ToolCapability, ToolId, ToolMetadata


@runtime_checkable
class ToolRegistry(Protocol):
    def register(self, tool: Tool) -> None: ...
    def remove(self, tool_id: ToolId) -> None: ...
    def resolve(self, tool_id: ToolId) -> Tool: ...
    def list(self) -> tuple[Tool, ...]: ...
    def find_by_capability(
        self, capability: ToolCapability
    ) -> tuple[Tool, ...]: ...


class InMemoryToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool is None or not callable(getattr(tool, "execute", None)):
            raise InvalidToolRegistrationError("Tool deve implementar execute.")
        try:
            metadata = tool.metadata
        except Exception as exc:
            raise InvalidToolRegistrationError(
                "Não foi possível consultar ToolMetadata."
            ) from exc
        if not isinstance(metadata, ToolMetadata):
            raise InvalidToolRegistrationError(
                "Tool deve expor ToolMetadata válido."
            )
        if metadata.id.value in self._tools:
            raise ToolAlreadyRegisteredError(str(metadata.id))
        self._tools[metadata.id.value] = tool

    def remove(self, tool_id: ToolId) -> None:
        key = self._key(tool_id)
        if key not in self._tools:
            raise ToolNotRegisteredError(f"Tool não registrada: {key}")
        del self._tools[key]

    def resolve(self, tool_id: ToolId) -> Tool:
        key = self._key(tool_id)
        try:
            return self._tools[key]
        except KeyError as exc:
            raise ToolNotRegisteredError(f"Tool não registrada: {key}") from exc

    def list(self) -> tuple[Tool, ...]:
        return tuple(self._tools[key] for key in sorted(self._tools))

    def find_by_capability(
        self, capability: ToolCapability
    ) -> tuple[Tool, ...]:
        if not isinstance(capability, ToolCapability):
            raise InvalidToolRegistrationError(
                "capability deve ser ToolCapability."
            )
        return tuple(
            tool
            for tool in self.list()
            if capability.id
            in {declared.id for declared in tool.metadata.capabilities}
        )

    @staticmethod
    def _key(tool_id: ToolId) -> str:
        if not isinstance(tool_id, ToolId):
            raise InvalidToolRegistrationError("tool_id deve ser ToolId.")
        return tool_id.value


__all__ = ["InMemoryToolRegistry", "ToolRegistry"]
