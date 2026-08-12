import json
import sqlite3
from datetime import UTC
from pathlib import Path

from asep.errors import ProjectHistoryConflictError, SessionMemoryNotFoundError
from asep.projects.session_memory_models import SessionMemoryEntry
from asep.projects.session_memory_query import (
    SessionMemoryOrder,
    SessionMemoryPage,
    SessionMemoryQuery,
    decode_session_memory_cursor,
    encode_session_memory_cursor,
)
from asep.sqlite import SQLiteDatabase


class SQLiteSessionMemoryRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def add(self, entry: SessionMemoryEntry) -> None:
        payload = json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    "INSERT INTO project_session_memory (id, project_id, session_id, kind, normalized_content, created_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (entry.memory_id, entry.project_id, entry.session_id, entry.kind.value,
                     _normalized(entry.content),
                     entry.created_at.astimezone(UTC).isoformat(), payload),
                )
        except sqlite3.IntegrityError as exc:
            raise ProjectHistoryConflictError("Session memory already exists.") from exc

    def get(self, memory_id: str) -> SessionMemoryEntry:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM project_session_memory WHERE id = ?", (memory_id,)
            ).fetchone()
        if row is None:
            raise SessionMemoryNotFoundError("Session memory not found.")
        return SessionMemoryEntry.model_validate_json(row["payload"])

    def list_by_session(self, session_id: str) -> tuple[SessionMemoryEntry, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM project_session_memory WHERE session_id = ? ORDER BY created_at DESC, id DESC",
                (session_id,),
            ).fetchall()
        return tuple(SessionMemoryEntry.model_validate_json(row["payload"]) for row in rows)

    def query(self, query: SessionMemoryQuery) -> SessionMemoryPage:
        cursor = (
            decode_session_memory_cursor(query.cursor, query)
            if query.cursor is not None
            else None
        )
        clauses = ["project_id = ?", "session_id = ?"]
        parameters: list[object] = [query.project_id, query.session_id]
        if query.kind is not None:
            clauses.append("kind = ?")
            parameters.append(query.kind.value)
        if query.text is not None:
            clauses.append("instr(normalized_content, ?) > 0")
            parameters.append(query.text)

        descending = query.order is SessionMemoryOrder.NEWEST
        operator = "<" if descending else ">"
        direction = "DESC" if descending else "ASC"
        if cursor is not None:
            timestamp = cursor.created_at.isoformat()
            clauses.append(
                f"(julianday(created_at) {operator} julianday(?) OR "
                f"(julianday(created_at) = julianday(?) "
                f"AND id {operator} ?))"
            )
            parameters.extend((timestamp, timestamp, cursor.memory_id))
        parameters.append(query.page_size + 1)
        statement = (
            "SELECT payload FROM project_session_memory WHERE "
            + " AND ".join(clauses)
            + f" ORDER BY julianday(created_at) {direction}, "
            + f"id {direction} LIMIT ?"
        )
        with self._database.connect() as connection:
            rows = connection.execute(statement, tuple(parameters)).fetchall()
        selected = tuple(
            SessionMemoryEntry.model_validate_json(row["payload"])
            for row in rows
        )
        has_more = len(selected) > query.page_size
        items = selected[: query.page_size]
        return SessionMemoryPage(
            items=items,
            next_cursor=(
                encode_session_memory_cursor(items[-1], query)
                if has_more
                else None
            ),
        )


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


__all__ = ["SQLiteSessionMemoryRepository"]
