import json
import sqlite3
from pathlib import Path

from asep.errors import (
    ProjectExecutionNotFoundError,
    ProjectHistoryConflictError,
    ProjectSessionNotFoundError,
)
from asep.projects.history_models import ProjectExecution, ProjectSession
from asep.sqlite import SQLiteDatabase


class SQLiteProjectSessionRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def create(self, session: ProjectSession) -> None:
        payload = json.dumps(session.model_dump(mode="json"), sort_keys=True)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    "INSERT INTO project_sessions (id, project_id, created_at, payload) VALUES (?, ?, ?, ?)",
                    (session.session_id, session.project_id, session.created_at.isoformat(), payload),
                )
        except sqlite3.IntegrityError as exc:
            raise ProjectHistoryConflictError("Project session could not be created.") from exc

    def get(self, session_id: str) -> ProjectSession:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM project_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise ProjectSessionNotFoundError("Project session not found.")
        return ProjectSession.model_validate_json(row["payload"])

    def get_by_project(self, project_id: str, session_id: str) -> ProjectSession:
        with self._database.connect() as connection:
            row = connection.execute("SELECT payload FROM project_sessions WHERE project_id=? AND id=?", (project_id, session_id)).fetchone()
        if row is None:
            raise ProjectSessionNotFoundError("Project session not found.")
        return ProjectSession.model_validate_json(row["payload"])

    def list_by_project(self, project_id: str) -> tuple[ProjectSession, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM project_sessions WHERE project_id = ? ORDER BY created_at DESC, id DESC",
                (project_id,),
            ).fetchall()
        return tuple(ProjectSession.model_validate_json(row["payload"]) for row in rows)


class SQLiteProjectExecutionRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def create(self, execution: ProjectExecution) -> None:
        payload = self._payload(execution)
        try:
            with self._database.connect() as connection:
                connection.execute(
                    "INSERT INTO project_executions (id, session_id, project_id, status, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)",
                    (execution.execution_id, execution.session_id, execution.project_id, execution.status.value, execution.created_at.isoformat(), payload),
                )
        except sqlite3.IntegrityError as exc:
            raise ProjectHistoryConflictError("Project execution could not be created.") from exc

    def update(self, execution: ProjectExecution) -> None:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "UPDATE project_executions SET status = ?, payload = ? WHERE id = ? AND project_id = ? AND session_id = ?",
                (execution.status.value, self._payload(execution), execution.execution_id, execution.project_id, execution.session_id),
            )
        if cursor.rowcount != 1:
            raise ProjectExecutionNotFoundError("Project execution not found.")

    def get(self, execution_id: str) -> ProjectExecution:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM project_executions WHERE id = ?", (execution_id,)
            ).fetchone()
        if row is None:
            raise ProjectExecutionNotFoundError("Project execution not found.")
        return ProjectExecution.model_validate_json(row["payload"])

    def get_by_project(self, project_id: str, execution_id: str) -> ProjectExecution:
        with self._database.connect() as connection:
            row = connection.execute("SELECT payload FROM project_executions WHERE project_id=? AND id=?", (project_id, execution_id)).fetchone()
        if row is None:
            raise ProjectExecutionNotFoundError("Project execution not found.")
        return ProjectExecution.model_validate_json(row["payload"])

    def list_by_session(self, session_id: str) -> tuple[ProjectExecution, ...]:
        return self._list("session_id", session_id)

    def list_by_project(self, project_id: str) -> tuple[ProjectExecution, ...]:
        return self._list("project_id", project_id)

    def _list(self, column: str, value: str) -> tuple[ProjectExecution, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT payload FROM project_executions WHERE {column} = ? ORDER BY created_at DESC, id DESC",
                (value,),
            ).fetchall()
        return tuple(ProjectExecution.model_validate_json(row["payload"]) for row in rows)

    @staticmethod
    def _payload(execution: ProjectExecution) -> str:
        return json.dumps(execution.model_dump(mode="json"), sort_keys=True)


__all__ = ["SQLiteProjectExecutionRepository", "SQLiteProjectSessionRepository"]
