from typing import Protocol, runtime_checkable

from asep.projects.session_memory_models import SessionMemoryEntry


@runtime_checkable
class SessionMemoryRepository(Protocol):
    def add(self, entry: SessionMemoryEntry) -> None: ...
    def get(self, memory_id: str) -> SessionMemoryEntry: ...
    def list_by_session(self, session_id: str) -> tuple[SessionMemoryEntry, ...]: ...


__all__ = ["SessionMemoryRepository"]
