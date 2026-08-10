from asep.errors import ProjectHistoryConflictError, SessionMemoryNotFoundError
from asep.projects.session_memory_models import SessionMemoryEntry


class InMemorySessionMemoryRepository:
    def __init__(self) -> None:
        self._items: dict[str, SessionMemoryEntry] = {}

    def add(self, entry: SessionMemoryEntry) -> None:
        if entry.memory_id in self._items:
            raise ProjectHistoryConflictError("Session memory already exists.")
        self._items[entry.memory_id] = entry.model_copy(deep=True)

    def get(self, memory_id: str) -> SessionMemoryEntry:
        try:
            return self._items[memory_id].model_copy(deep=True)
        except KeyError as exc:
            raise SessionMemoryNotFoundError("Session memory not found.") from exc

    def list_by_session(self, session_id: str) -> tuple[SessionMemoryEntry, ...]:
        items = (item for item in self._items.values() if item.session_id == session_id)
        return tuple(item.model_copy(deep=True) for item in sorted(
            items, key=lambda item: (item.created_at, item.memory_id), reverse=True
        ))


__all__ = ["InMemorySessionMemoryRepository"]
