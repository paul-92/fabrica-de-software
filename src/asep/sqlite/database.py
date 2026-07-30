"""Conexão e schema SQLite compartilhados pelos repositories."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from asep.sqlite.errors import SQLiteConnectionError, SQLiteSchemaError


class SQLiteDatabase:
    """Inicializa o banco e fornece conexões transacionais curtas."""

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS timeline_events (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_timeline_events_run
            ON timeline_events (run_id);
    """
    _EXPECTED_COLUMNS = {
        "runs": {"id", "started_at", "payload"},
        "timeline_events": {"id", "run_id", "timestamp", "payload"},
    }

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
        except (OSError, sqlite3.Error) as exc:
            raise SQLiteConnectionError(
                "Falha ao abrir o banco SQLite.",
                path=self.path,
            ) from exc
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SQLiteConnectionError(
                "Falha ao criar o diretório do banco SQLite.",
                path=self.path,
            ) from exc
        try:
            with self.connect() as connection:
                connection.executescript(self._SCHEMA)
                self._validate_schema(connection)
        except SQLiteConnectionError:
            raise
        except sqlite3.DatabaseError as exc:
            raise SQLiteSchemaError(
                "Falha ao inicializar o schema SQLite.",
                path=self.path,
            ) from exc

    def _validate_schema(self, connection: sqlite3.Connection) -> None:
        for table, expected in self._EXPECTED_COLUMNS.items():
            rows = connection.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
            actual = {str(row["name"]) for row in rows}
            if actual != expected:
                raise SQLiteSchemaError(
                    f"Schema SQLite incompatível para tabela {table}.",
                    path=self.path,
                )
