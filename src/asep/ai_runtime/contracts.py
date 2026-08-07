"""Portas públicas do AI Runtime."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.ai_runtime.models import (
    AIRuntimeIdentity,
    AIRuntimeRequest,
    AIRuntimeResult,
)


@runtime_checkable
class AIRuntime(Protocol):
    """Executa uma intenção sem expor conceitos de fornecedor."""

    @property
    def identity(self) -> AIRuntimeIdentity: ...

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult: ...


@runtime_checkable
class AIRuntimeRegistry(Protocol):
    """Registra e resolve runtimes por identidade extensível."""

    def register(self, runtime: AIRuntime) -> None: ...

    def get(self, runtime_id: str) -> AIRuntime: ...

    def contains(self, runtime_id: str) -> bool: ...

    def list_all(self) -> tuple[AIRuntime, ...]: ...


__all__ = ["AIRuntime", "AIRuntimeRegistry"]
