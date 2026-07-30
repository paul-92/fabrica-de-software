"""Implementação SQLite do RunRepository."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from asep.errors import RunNotFoundError
from asep.runs.errors import (
    InvalidRunStorageFormatError,
    RunStorageReadError,
    RunStorageWriteError,
)
from asep.runs.models import Run
from asep.runs.serialization import RunCodec
from asep.sqlite import SQLiteDatabase, SQLiteStorageError


class SQLiteRunRepository:
    """Persiste snapshots de Runs em uma tabela SQLite."""

    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def save(self, run: Run) -> None:
        payload = self._serialize(run)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO runs (id, started_at, payload)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        started_at = excluded.started_at,
                        payload = excluded.payload
                    """,
                    (run.id, run.started_at.isoformat(), payload),
                )
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise RunStorageWriteError(
                "Falha ao persistir Run no SQLite.",
                path=self._database.path,
            ) from exc

    def get(self, run_id: str) -> Run:
        try:
            with self._database.connect() as connection:
                row = connection.execute(
                    "SELECT payload FROM runs WHERE id = ?",
                    (run_id,),
                ).fetchone()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise RunStorageReadError(
                "Falha ao ler Run do SQLite.",
                path=self._database.path,
            ) from exc
        if row is None:
            raise RunNotFoundError(
                f"Run não encontrado no repositório: {run_id}"
            )
        return self._deserialize(row["payload"])

    def list(self) -> tuple[Run, ...]:
        try:
            with self._database.connect() as connection:
                rows = connection.execute(
                    "SELECT payload FROM runs"
                ).fetchall()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise RunStorageReadError(
                "Falha ao listar Runs do SQLite.",
                path=self._database.path,
            ) from exc
        runs = tuple(self._deserialize(row["payload"]) for row in rows)
        return tuple(sorted(runs, key=lambda item: (item.started_at, item.id)))

    def _serialize(self, run: Run) -> str:
        try:
            return json.dumps(
                RunCodec.encode(run),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise RunStorageWriteError(
                "Falha ao serializar Run para SQLite.",
                path=self._database.path,
            ) from exc

    def _deserialize(self, payload: Any) -> Run:
        try:
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise TypeError
            return RunCodec.decode(document)
        except (
            json.JSONDecodeError,
            TypeError,
            InvalidRunStorageFormatError,
        ) as exc:
            raise InvalidRunStorageFormatError(
                "Run persistido no SQLite possui formato inválido.",
                path=self._database.path,
            ) from exc
