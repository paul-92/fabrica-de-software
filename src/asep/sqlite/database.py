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
        CREATE TABLE IF NOT EXISTS workflow_snapshots (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_workflow_snapshots_workflow
            ON workflow_snapshots (workflow_id);
        CREATE INDEX IF NOT EXISTS idx_workflow_snapshots_run
            ON workflow_snapshots (run_id);
        CREATE INDEX IF NOT EXISTS idx_workflow_snapshots_status
            ON workflow_snapshots (status);
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            workflow_execution_id TEXT,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_entries_agent
            ON memory_entries (agent_id);
        CREATE INDEX IF NOT EXISTS idx_memory_entries_execution
            ON memory_entries (execution_id);
        CREATE INDEX IF NOT EXISTS idx_memory_entries_workflow
            ON memory_entries (workflow_execution_id);
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        );
    """
    _EXPECTED_COLUMNS = {
        "runs": {"id", "started_at", "payload"},
        "timeline_events": {"id", "run_id", "timestamp", "payload"},
        "workflow_snapshots": {
            "id",
            "workflow_id",
            "run_id",
            "status",
            "started_at",
            "payload",
        },
        "memory_entries": {
            "id",
            "agent_id",
            "execution_id",
            "workflow_execution_id",
            "created_at",
            "payload",
        },
        "projects": {"id", "created_at", "payload"},
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
