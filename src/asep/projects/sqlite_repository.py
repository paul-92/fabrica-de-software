import json
import sqlite3
from pathlib import Path

from asep.errors import ProjectNotFoundError
from asep.projects.models import WorkspaceProject
from asep.sqlite import SQLiteDatabase


class SQLiteProjectRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def save(self, project: WorkspaceProject) -> None:
        payload = json.dumps(project.model_dump(mode="json"), sort_keys=True)
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO projects (id, created_at, payload) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (project.project_id, project.created_at.isoformat(), payload),
            )

    def get(self, project_id: str) -> WorkspaceProject:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError("Projeto não encontrado.")
        return WorkspaceProject.model_validate_json(row["payload"])

    def list(self) -> tuple[WorkspaceProject, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM projects ORDER BY created_at, id"
            ).fetchall()
        return tuple(
            WorkspaceProject.model_validate_json(row["payload"])
            for row in rows
        )
