import json
import sqlite3
from pathlib import Path

from asep.errors import ProjectHistoryConflictError, SessionMemoryNotFoundError
from asep.projects.session_memory_models import SessionMemoryEntry
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
                     _normalized(entry.content), entry.created_at.isoformat(), payload),
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


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


__all__ = ["SQLiteSessionMemoryRepository"]
