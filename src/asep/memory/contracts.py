"""Portas públicas de memória e contexto."""

from typing import Protocol, runtime_checkable

from asep.agents.contracts import AgentId
from asep.memory.models import (
    ContextBuildRequest,
    ContextBuildResult,
    MemoryEntry,
    MemoryId,
    MemoryQuery,
)


@runtime_checkable
class MemoryStore(Protocol):
    def save(self, entry: MemoryEntry) -> None: ...
    def update(self, entry: MemoryEntry) -> None: ...
    def get(self, memory_id: MemoryId) -> MemoryEntry: ...
    def delete(self, memory_id: MemoryId) -> None: ...
    def find_by_agent(self, agent_id: AgentId) -> tuple[MemoryEntry, ...]: ...
    def find_by_execution(
        self, execution_id: str
    ) -> tuple[MemoryEntry, ...]: ...
    def search(self, query: MemoryQuery) -> tuple[MemoryEntry, ...]: ...
    def clear(self, agent_id: AgentId | None = None) -> int: ...
    def count(self, agent_id: AgentId | None = None) -> int: ...


MemoryRepository = MemoryStore


@runtime_checkable
class AgentMemory(Protocol):
    def save(self, entry: MemoryEntry) -> MemoryEntry: ...
    def get(self, memory_id: MemoryId) -> MemoryEntry: ...
    def search(self, query: MemoryQuery) -> tuple[MemoryEntry, ...]: ...
    def find_by_agent(
        self, agent_id: AgentId
    ) -> tuple[MemoryEntry, ...]: ...
    def summarize(self, agent_id: AgentId) -> str: ...
    def remove(self, memory_id: MemoryId) -> None: ...


@runtime_checkable
class ContextProvider(Protocol):
    def build(self, request: ContextBuildRequest) -> ContextBuildResult: ...


__all__ = [
    "AgentMemory",
    "ContextProvider",
    "MemoryRepository",
    "MemoryStore",
]
