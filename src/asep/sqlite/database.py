"""Conexão e schema SQLite compartilhados pelos repositories."""

from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from asep.sqlite.errors import SQLiteConnectionError, SQLiteSchemaError

SCHEMA_VERSION = "4"


class SQLiteDatabase:
    """Inicializa o banco e fornece conexões transacionais curtas."""

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memberships (
            organization_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL,
            created_at TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY (organization_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS access_sessions (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ai_usage_ledger (
            id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, user_id TEXT NOT NULL,
            project_id TEXT NOT NULL, execution_id TEXT NOT NULL,
            started_at TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ai_usage_organization ON ai_usage_ledger (organization_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_user ON ai_usage_ledger (organization_id, user_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_project ON ai_usage_ledger (organization_id, project_id, started_at);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_execution ON ai_usage_ledger (organization_id, execution_id, started_at);
        CREATE TABLE IF NOT EXISTS ai_quotas (
            organization_id TEXT NOT NULL, user_id TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY (organization_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS ai_quota_reservations (
            id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, user_id TEXT NOT NULL,
            period_started_at TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ai_quota_reservations ON ai_quota_reservations (organization_id,user_id,period_started_at,status);
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
        CREATE TABLE IF NOT EXISTS quality_gate_results (
            run_id TEXT NOT NULL,
            stage_id TEXT NOT NULL,
            gate_id TEXT NOT NULL,
            evaluated_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (run_id, stage_id, gate_id)
        );
        CREATE INDEX IF NOT EXISTS idx_quality_gate_results_run
            ON quality_gate_results (run_id, stage_id, gate_id, evaluated_at);
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
            organization_id TEXT NOT NULL DEFAULT 'legacy-local',
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_project_sessions_project
            ON project_sessions (project_id, created_at);
        CREATE TABLE IF NOT EXISTS project_executions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES project_sessions(id),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_project_executions_session
            ON project_executions (session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_project_executions_project
            ON project_executions (project_id, created_at);
        CREATE TABLE IF NOT EXISTS project_session_memory (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            normalized_content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(session_id) REFERENCES project_sessions(id),
            UNIQUE(project_id, session_id, kind, normalized_content)
        );
        CREATE INDEX IF NOT EXISTS idx_project_session_memory_session
            ON project_session_memory (session_id, created_at);
        CREATE TABLE IF NOT EXISTS branding_settings (
            id TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            payload TEXT NOT NULL
        );
    """
    _EXPECTED_COLUMNS = {
        "schema_metadata": {"key", "value"},
        "organizations": {"id", "created_at", "payload"},
        "users": {"id", "email", "status", "password_hash", "created_at", "payload"},
        "memberships": {"organization_id", "user_id", "role", "created_at", "payload"},
        "access_sessions": {"id", "user_id", "token_hash", "expires_at", "payload"},
        "ai_usage_ledger": {"id", "organization_id", "user_id", "project_id", "execution_id", "started_at", "payload"},
        "ai_quotas": {"organization_id", "user_id", "payload"},
        "ai_quota_reservations": {"id", "organization_id", "user_id", "period_started_at", "status", "created_at"},
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
        "quality_gate_results": {
            "run_id",
            "stage_id",
            "gate_id",
            "evaluated_at",
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
        "projects": {"id", "organization_id", "created_at", "payload"},
        "project_sessions": {"id", "project_id", "created_at", "payload"},
        "project_executions": {
            "id", "session_id", "project_id", "status", "created_at", "payload"
        },
        "project_session_memory": {
            "id", "project_id", "session_id", "kind", "normalized_content",
            "created_at", "payload"
        },
        "branding_settings": {"id", "version", "payload"},
    }

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
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
                self._migrate(connection)
                connection.executescript(self._SCHEMA)
                connection.execute("INSERT OR REPLACE INTO schema_metadata (key,value) VALUES ('schema_version',?)", (SCHEMA_VERSION,))
                self._validate_schema(connection)
        except SQLiteConnectionError:
            raise
        except sqlite3.DatabaseError as exc:
            raise SQLiteSchemaError(
                "Falha ao inicializar o schema SQLite.",
                path=self.path,
            ) from exc

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "projects" in tables:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(projects)")}
            if "organization_id" not in columns:
                connection.execute("ALTER TABLE projects ADD COLUMN organization_id TEXT NOT NULL DEFAULT 'legacy-local'")
            rows = connection.execute("SELECT id,payload FROM projects").fetchall()
            for row in rows:
                payload = json.loads(row["payload"])
                changed = False
                if "organization_id" not in payload:
                    payload["organization_id"] = "legacy-local"; changed = True
                if "created_by_user_id" not in payload:
                    payload["created_by_user_id"] = "legacy-local-admin"; changed = True
                if changed:
                    connection.execute("UPDATE projects SET organization_id='legacy-local', payload=? WHERE id=?", (json.dumps(payload, sort_keys=True), row["id"]))

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


__all__ = ["SCHEMA_VERSION", "SQLiteDatabase"]
