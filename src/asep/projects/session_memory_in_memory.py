from asep.errors import ProjectHistoryConflictError, SessionMemoryNotFoundError
from asep.projects.session_memory_models import SessionMemoryEntry
from asep.projects.session_memory_query import (
    SessionMemoryOrder,
    SessionMemoryPage,
    SessionMemoryQuery,
    decode_session_memory_cursor,
    encode_session_memory_cursor,
    normalize_session_memory_text,
)


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

    def query(self, query: SessionMemoryQuery) -> SessionMemoryPage:
        cursor = (
            decode_session_memory_cursor(query.cursor, query)
            if query.cursor is not None
            else None
        )
        items = [
            item
            for item in self._items.values()
            if item.project_id == query.project_id
            and item.session_id == query.session_id
            and (query.kind is None or item.kind is query.kind)
            and (
                query.text is None
                or query.text in normalize_session_memory_text(item.content)
            )
        ]
        reverse = query.order is SessionMemoryOrder.NEWEST
        items.sort(
            key=lambda item: (item.created_at, item.memory_id),
            reverse=reverse,
        )
        if cursor is not None:
            anchor = (cursor.created_at, cursor.memory_id)
            items = [
                item
                for item in items
                if (
                    (item.created_at, item.memory_id) < anchor
                    if reverse
                    else (item.created_at, item.memory_id) > anchor
                )
            ]
        selected = items[: query.page_size + 1]
        has_more = len(selected) > query.page_size
        page_items = selected[: query.page_size]
        detached = tuple(item.model_copy(deep=True) for item in page_items)
        return SessionMemoryPage(
            items=detached,
            next_cursor=(
                encode_session_memory_cursor(page_items[-1], query)
                if has_more
                else None
            ),
        )


__all__ = ["InMemorySessionMemoryRepository"]
