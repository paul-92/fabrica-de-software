"""Portas públicas da supervisão."""

from typing import Protocol, runtime_checkable

from asep.agents.runtime import AgentRuntime


@runtime_checkable
class ExecutionSupervisor(AgentRuntime, Protocol):
    """Runtime decorador que acrescenta supervisão e recuperação."""


__all__ = ["ExecutionSupervisor"]
