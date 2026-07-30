"""Contrato público do runtime inteligente de agentes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionResult,
)


@runtime_checkable
class AgentRuntime(Protocol):
    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult: ...


__all__ = ["AgentRuntime"]
