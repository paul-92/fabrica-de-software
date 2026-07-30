"""MemoryStore persistente sobre o adaptador SQLite compartilhado."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from asep.agents.contracts import AgentId
from asep.memory.exceptions import (
    MemoryAlreadyExistsError,
    MemoryNotFoundError,
    MemoryStorageError,
)
from asep.memory.in_memory import _matches_metadata, _sorted
from asep.memory.models import MemoryEntry, MemoryId, MemoryQuery
from asep.memory.serialization import MemoryEntryCodec
from asep.sqlite import SQLiteDatabase, SQLiteStorageError


class SQLiteMemoryStore:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def save(self, entry: MemoryEntry) -> None:
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO memory_entries
                        (id, agent_id, execution_id,
                         workflow_execution_id, created_at, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    self._parameters(entry),
                )
        except sqlite3.IntegrityError as exc:
            raise MemoryAlreadyExistsError(
                f"Memória já existe: {entry.memory_id}"
            ) from exc
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise MemoryStorageError("Falha ao salvar memória.") from exc

    def update(self, entry: MemoryEntry) -> None:
        try:
            with self._database.connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE memory_entries
                    SET agent_id = ?, execution_id = ?,
                        workflow_execution_id = ?, created_at = ?, payload = ?
                    WHERE id = ?
                    """,
                    (
                        entry.agent_id.value,
                        entry.execution_id,
                        entry.workflow_execution_id,
                        entry.created_at.isoformat(),
                        self._serialize(entry),
                        entry.memory_id.value,
                    ),
                )
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise MemoryStorageError("Falha ao atualizar memória.") from exc
        if cursor.rowcount == 0:
            raise MemoryNotFoundError(
                f"Memória não encontrada: {entry.memory_id}"
            )

    def get(self, memory_id: MemoryId) -> MemoryEntry:
        rows = self._select(
            "SELECT payload FROM memory_entries WHERE id = ?",
            (memory_id.value,),
        )
        if not rows:
            raise MemoryNotFoundError(
                f"Memória não encontrada: {memory_id}"
            )
        return self._deserialize(rows[0]["payload"])

    def delete(self, memory_id: MemoryId) -> None:
        try:
            with self._database.connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM memory_entries WHERE id = ?",
                    (memory_id.value,),
                )
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise MemoryStorageError("Falha ao excluir memória.") from exc
        if cursor.rowcount == 0:
            raise MemoryNotFoundError(
                f"Memória não encontrada: {memory_id}"
            )

    def find_by_agent(self, agent_id: AgentId) -> tuple[MemoryEntry, ...]:
        return self._decoded(
            self._select(
                "SELECT payload FROM memory_entries WHERE agent_id = ?",
                (agent_id.value,),
            )
        )

    def find_by_execution(
        self, execution_id: str
    ) -> tuple[MemoryEntry, ...]:
        return self._decoded(
            self._select(
                "SELECT payload FROM memory_entries WHERE execution_id = ?",
                (execution_id,),
            )
        )

    def search(self, query: MemoryQuery) -> tuple[MemoryEntry, ...]:
        text = query.text.casefold() if query.text is not None else None
        return _sorted(
            item
            for item in self._decoded(
                self._select("SELECT payload FROM memory_entries", ())
            )
            if (query.agent_id is None or item.agent_id == query.agent_id)
            and (query.category is None or item.category == query.category)
            and (text is None or text in item.content.casefold())
            and (
                query.execution_id is None
                or item.execution_id == query.execution_id
            )
            and (
                query.workflow_execution_id is None
                or item.workflow_execution_id
                == query.workflow_execution_id
            )
            and _matches_metadata(item.metadata, query.metadata)
        )

    def clear(self, agent_id: AgentId | None = None) -> int:
        statement = "DELETE FROM memory_entries"
        parameters: tuple[str, ...] = ()
        if agent_id is not None:
            statement += " WHERE agent_id = ?"
            parameters = (agent_id.value,)
        try:
            with self._database.connect() as connection:
                return connection.execute(statement, parameters).rowcount
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise MemoryStorageError("Falha ao limpar memórias.") from exc

    def count(self, agent_id: AgentId | None = None) -> int:
        statement = "SELECT COUNT(*) AS total FROM memory_entries"
        parameters: tuple[str, ...] = ()
        if agent_id is not None:
            statement += " WHERE agent_id = ?"
            parameters = (agent_id.value,)
        return int(self._select(statement, parameters)[0]["total"])

    def _select(
        self, statement: str, parameters: tuple[Any, ...]
    ) -> list[sqlite3.Row]:
        try:
            with self._database.connect() as connection:
                return connection.execute(statement, parameters).fetchall()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise MemoryStorageError("Falha ao consultar memórias.") from exc

    def _decoded(self, rows: list[sqlite3.Row]) -> tuple[MemoryEntry, ...]:
        return _sorted(self._deserialize(row["payload"]) for row in rows)

    def _parameters(self, entry: MemoryEntry) -> tuple[str | None, ...]:
        return (
            entry.memory_id.value,
            entry.agent_id.value,
            entry.execution_id,
            entry.workflow_execution_id,
            entry.created_at.isoformat(),
            self._serialize(entry),
        )

    def _serialize(self, entry: MemoryEntry) -> str:
        try:
            return json.dumps(
                MemoryEntryCodec.encode(entry),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise MemoryStorageError("Falha ao serializar memória.") from exc

    @staticmethod
    def _deserialize(payload: Any) -> MemoryEntry:
        try:
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise TypeError
            return MemoryEntryCodec.decode(document)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise MemoryStorageError(
                "Memória persistida possui formato inválido."
            ) from exc


__all__ = ["SQLiteMemoryStore"]
