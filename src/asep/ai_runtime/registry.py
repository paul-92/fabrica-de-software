"""Registry local e determinístico de AI Runtimes."""

from __future__ import annotations

from asep.ai_runtime.contracts import AIRuntime
from asep.ai_runtime.errors import (
    AIRuntimeAlreadyRegisteredError,
    AIRuntimeConfigurationError,
    AIRuntimeNotFoundError,
)


class InMemoryAIRuntimeRegistry:
    """Mantém runtimes injetados; não descobre nem instancia providers."""

    def __init__(self) -> None:
        self._runtimes: dict[str, AIRuntime] = {}

    def register(self, runtime: AIRuntime) -> None:
        if not isinstance(runtime, AIRuntime):
            raise AIRuntimeConfigurationError()
        runtime_id = runtime.identity.runtime_id
        if runtime_id in self._runtimes:
            raise AIRuntimeAlreadyRegisteredError(runtime_id)
        self._runtimes[runtime_id] = runtime

    def get(self, runtime_id: str) -> AIRuntime:
        key = self._normalize_id(runtime_id)
        try:
            return self._runtimes[key]
        except KeyError as exc:
            raise AIRuntimeNotFoundError(key) from exc

    def contains(self, runtime_id: str) -> bool:
        return self._normalize_id(runtime_id) in self._runtimes

    def list_all(self) -> tuple[AIRuntime, ...]:
        return tuple(self._runtimes[key] for key in sorted(self._runtimes))

    @staticmethod
    def _normalize_id(runtime_id: str) -> str:
        if not isinstance(runtime_id, str) or not runtime_id.strip():
            raise AIRuntimeConfigurationError()
        return runtime_id.strip()


__all__ = ["InMemoryAIRuntimeRegistry"]
