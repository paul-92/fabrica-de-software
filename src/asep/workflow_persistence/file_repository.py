"""WorkflowRepository persistente em arquivo JSON atômico."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from asep.workflow.models import WorkflowStatus
from asep.workflow_persistence.errors import (
    InvalidWorkflowStorageFormatError,
    WorkflowSnapshotAlreadyExistsError,
    WorkflowSnapshotNotFoundError,
    WorkflowStorageReadError,
    WorkflowStorageWriteError,
)
from asep.workflow_persistence.in_memory import InMemoryWorkflowRepository
from asep.workflow_persistence.models import WorkflowSnapshot
from asep.workflow_persistence.serialization import WorkflowSnapshotCodec

WORKFLOW_STORAGE_VERSION = "1.0"


class FileWorkflowRepository:
    """Mantém snapshots em um arquivo versionado no mesmo filesystem."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._snapshots = self._load_or_initialize()

    def save(self, snapshot: WorkflowSnapshot) -> None:
        if snapshot.id in self._snapshots:
            raise WorkflowSnapshotAlreadyExistsError(
                f"WorkflowSnapshot já existe: {snapshot.id}"
            )
        updated = dict(self._snapshots)
        updated[snapshot.id] = self._copy(snapshot)
        self._commit(updated)

    def update(self, snapshot: WorkflowSnapshot) -> None:
        if snapshot.id not in self._snapshots:
            raise WorkflowSnapshotNotFoundError(
                f"WorkflowSnapshot não encontrado: {snapshot.id}"
            )
        updated = dict(self._snapshots)
        updated[snapshot.id] = self._copy(snapshot)
        self._commit(updated)

    def get(self, snapshot_id: str) -> WorkflowSnapshot:
        try:
            return self._copy(self._snapshots[snapshot_id])
        except KeyError as exc:
            raise WorkflowSnapshotNotFoundError(
                f"WorkflowSnapshot não encontrado: {snapshot_id}"
            ) from exc

    def exists(self, snapshot_id: str) -> bool:
        return snapshot_id in self._snapshots

    def list(self) -> tuple[WorkflowSnapshot, ...]:
        return self._query().list()

    def find_by_status(
        self,
        status: WorkflowStatus,
    ) -> tuple[WorkflowSnapshot, ...]:
        return self._query().find_by_status(status)

    def find_by_run(self, run_id: str) -> tuple[WorkflowSnapshot, ...]:
        return self._query().find_by_run(run_id)

    def find_by_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowSnapshot, ...]:
        return self._query().find_by_workflow(workflow_id)

    def find_by_period(
        self,
        started_at: datetime,
        finished_at: datetime,
    ) -> tuple[WorkflowSnapshot, ...]:
        return self._query().find_by_period(started_at, finished_at)

    def _query(self) -> InMemoryWorkflowRepository:
        repository = InMemoryWorkflowRepository()
        for item in self._snapshots.values():
            repository.save(item)
        return repository

    def _load_or_initialize(self) -> dict[str, WorkflowSnapshot]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._write(())
            return {}
        except OSError as exc:
            raise WorkflowStorageReadError(
                "Falha ao ler arquivo de WorkflowSnapshots.",
                path=self._path,
            ) from exc
        if not raw.strip():
            return {}
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidWorkflowStorageFormatError(
                "Arquivo de WorkflowSnapshots contém JSON inválido.",
                path=self._path,
            ) from exc
        if (
            not isinstance(document, dict)
            or set(document) != {"version", "workflows"}
            or document.get("version") != WORKFLOW_STORAGE_VERSION
            or not isinstance(document.get("workflows"), list)
        ):
            raise InvalidWorkflowStorageFormatError(
                "Envelope de WorkflowSnapshots é inválido.",
                path=self._path,
            )
        snapshots: dict[str, WorkflowSnapshot] = {}
        for record in document["workflows"]:
            if not isinstance(record, dict):
                raise InvalidWorkflowStorageFormatError(
                    "WorkflowSnapshot deve ser um objeto.",
                    path=self._path,
                )
            snapshot = WorkflowSnapshotCodec.decode(record)
            if snapshot.id in snapshots:
                raise InvalidWorkflowStorageFormatError(
                    "Arquivo possui IDs de WorkflowSnapshot duplicados.",
                    path=self._path,
                )
            snapshots[snapshot.id] = snapshot
        return snapshots

    def _commit(self, snapshots: dict[str, WorkflowSnapshot]) -> None:
        ordered = tuple(
            sorted(
                snapshots.values(),
                key=lambda item: (item.started_at, item.id),
            )
        )
        self._write(ordered)
        self._snapshots = {item.id: item for item in ordered}

    def _write(self, snapshots: tuple[WorkflowSnapshot, ...]) -> None:
        try:
            content = json.dumps(
                {
                    "version": WORKFLOW_STORAGE_VERSION,
                    "workflows": [
                        WorkflowSnapshotCodec.encode(item)
                        for item in snapshots
                    ],
                },
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise WorkflowStorageWriteError(
                "Falha ao serializar WorkflowSnapshots.",
                path=self._path,
            ) from exc
        temporary: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".asep-workflows-",
                suffix=".tmp",
                dir=self._path.parent,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
        except OSError as exc:
            raise WorkflowStorageWriteError(
                "Falha ao persistir WorkflowSnapshots.",
                path=self._path,
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _copy(snapshot: WorkflowSnapshot) -> WorkflowSnapshot:
        return WorkflowSnapshotCodec.decode(
            WorkflowSnapshotCodec.encode(snapshot)
        )
