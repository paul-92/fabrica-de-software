"""WorkflowRepository baseado no SQLite compartilhado da ASEP."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from asep.sqlite import SQLiteDatabase, SQLiteStorageError
from asep.workflow.models import WorkflowStatus
from asep.workflow_persistence.errors import (
    InvalidWorkflowStorageFormatError,
    WorkflowSnapshotAlreadyExistsError,
    WorkflowSnapshotNotFoundError,
    WorkflowStorageReadError,
    WorkflowStorageWriteError,
)
from asep.workflow_persistence.models import WorkflowSnapshot
from asep.workflow_persistence.serialization import WorkflowSnapshotCodec


class SQLiteWorkflowRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def save(self, snapshot: WorkflowSnapshot) -> None:
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO workflow_snapshots
                        (id, workflow_id, run_id, status, started_at, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    self._parameters(snapshot),
                )
        except sqlite3.IntegrityError as exc:
            raise WorkflowSnapshotAlreadyExistsError(
                f"WorkflowSnapshot já existe: {snapshot.id}"
            ) from exc
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise WorkflowStorageWriteError(
                "Falha ao salvar WorkflowSnapshot no SQLite.",
                path=self._database.path,
            ) from exc

    def update(self, snapshot: WorkflowSnapshot) -> None:
        try:
            with self._database.connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE workflow_snapshots
                    SET workflow_id = ?, run_id = ?, status = ?,
                        started_at = ?, payload = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.workflow_id,
                        snapshot.run_id,
                        snapshot.status.value,
                        snapshot.started_at.isoformat(),
                        self._serialize(snapshot),
                        snapshot.id,
                    ),
                )
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise WorkflowStorageWriteError(
                "Falha ao atualizar WorkflowSnapshot no SQLite.",
                path=self._database.path,
            ) from exc
        if cursor.rowcount == 0:
            raise WorkflowSnapshotNotFoundError(
                f"WorkflowSnapshot não encontrado: {snapshot.id}"
            )

    def get(self, snapshot_id: str) -> WorkflowSnapshot:
        rows = self._select(
            "SELECT payload FROM workflow_snapshots WHERE id = ?",
            (snapshot_id,),
        )
        if not rows:
            raise WorkflowSnapshotNotFoundError(
                f"WorkflowSnapshot não encontrado: {snapshot_id}"
            )
        return self._deserialize(rows[0]["payload"])

    def exists(self, snapshot_id: str) -> bool:
        return bool(
            self._select(
                "SELECT 1 FROM workflow_snapshots WHERE id = ?",
                (snapshot_id,),
            )
        )

    def list(self) -> tuple[WorkflowSnapshot, ...]:
        return self._decoded(
            self._select("SELECT payload FROM workflow_snapshots", ())
        )

    def find_by_status(
        self,
        status: WorkflowStatus,
    ) -> tuple[WorkflowSnapshot, ...]:
        return self._decoded(
            self._select(
                "SELECT payload FROM workflow_snapshots WHERE status = ?",
                (status.value,),
            )
        )

    def find_by_run(self, run_id: str) -> tuple[WorkflowSnapshot, ...]:
        return self._decoded(
            self._select(
                "SELECT payload FROM workflow_snapshots WHERE run_id = ?",
                (run_id,),
            )
        )

    def find_by_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowSnapshot, ...]:
        return self._decoded(
            self._select(
                """
                SELECT payload FROM workflow_snapshots
                WHERE workflow_id = ?
                """,
                (workflow_id,),
            )
        )

    def find_by_period(
        self,
        started_at: datetime,
        finished_at: datetime,
    ) -> tuple[WorkflowSnapshot, ...]:
        if finished_at < started_at:
            raise ValueError("período final não pode preceder o inicial")
        return tuple(
            item
            for item in self.list()
            if started_at <= item.started_at <= finished_at
        )

    def _select(
        self,
        statement: str,
        parameters: tuple[Any, ...],
    ) -> list[sqlite3.Row]:
        try:
            with self._database.connect() as connection:
                return connection.execute(
                    statement,
                    parameters,
                ).fetchall()
        except SQLiteStorageError:
            raise
        except sqlite3.Error as exc:
            raise WorkflowStorageReadError(
                "Falha ao consultar WorkflowSnapshots no SQLite.",
                path=self._database.path,
            ) from exc

    def _decoded(
        self,
        rows: list[sqlite3.Row],
    ) -> tuple[WorkflowSnapshot, ...]:
        snapshots = tuple(
            self._deserialize(row["payload"]) for row in rows
        )
        return tuple(
            sorted(
                snapshots,
                key=lambda item: (item.started_at, item.id),
            )
        )

    def _parameters(self, snapshot: WorkflowSnapshot) -> tuple[str, ...]:
        return (
            snapshot.id,
            snapshot.workflow_id,
            snapshot.run_id,
            snapshot.status.value,
            snapshot.started_at.isoformat(),
            self._serialize(snapshot),
        )

    def _serialize(self, snapshot: WorkflowSnapshot) -> str:
        try:
            return json.dumps(
                WorkflowSnapshotCodec.encode(snapshot),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise WorkflowStorageWriteError(
                "Falha ao serializar WorkflowSnapshot.",
                path=self._database.path,
            ) from exc

    def _deserialize(self, payload: Any) -> WorkflowSnapshot:
        try:
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise TypeError
            return WorkflowSnapshotCodec.decode(document)
        except (
            json.JSONDecodeError,
            TypeError,
            InvalidWorkflowStorageFormatError,
        ) as exc:
            raise InvalidWorkflowStorageFormatError(
                "WorkflowSnapshot no SQLite possui formato inválido.",
                path=self._database.path,
            ) from exc
