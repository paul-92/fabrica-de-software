"""Contratos públicos do Intelligent Orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from asep.orchestrator.models import (
        IntelligentExecutionRequest,
        IntelligentExecutionResult,
    )


@runtime_checkable
class IntelligentOrchestrator(Protocol):
    """Porta pública para execução do pipeline inteligente."""

    def execute(
        self,
        request: IntelligentExecutionRequest,
    ) -> IntelligentExecutionResult:
        """Executa o pipeline inteligente e retorna seu resultado."""
        ...


__all__ = [
    "IntelligentOrchestrator",
]