"""Implementação em memória do WorkflowRepository."""

from __future__ import annotations

from datetime import datetime

from asep.workflow.models import WorkflowStatus
from asep.workflow_persistence.errors import (
    WorkflowSnapshotAlreadyExistsError,
    WorkflowSnapshotNotFoundError,
)
from asep.workflow_persistence.models import WorkflowSnapshot
from asep.workflow_persistence.serialization import WorkflowSnapshotCodec


class InMemoryWorkflowRepository:
    def __init__(self) -> None:
        self._snapshots: dict[str, WorkflowSnapshot] = {}

    def save(self, snapshot: WorkflowSnapshot) -> None:
        if snapshot.id in self._snapshots:
            raise WorkflowSnapshotAlreadyExistsError(
                f"WorkflowSnapshot já existe: {snapshot.id}"
            )
        self._snapshots[snapshot.id] = self._copy(snapshot)

    def update(self, snapshot: WorkflowSnapshot) -> None:
        if snapshot.id not in self._snapshots:
            raise WorkflowSnapshotNotFoundError(
                f"WorkflowSnapshot não encontrado: {snapshot.id}"
            )
        self._snapshots[snapshot.id] = self._copy(snapshot)

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
        return tuple(
            self._copy(item)
            for item in sorted(
                self._snapshots.values(),
                key=lambda value: (value.started_at, value.id),
            )
        )

    def find_by_status(
        self,
        status: WorkflowStatus,
    ) -> tuple[WorkflowSnapshot, ...]:
        return tuple(item for item in self.list() if item.status is status)

    def find_by_run(self, run_id: str) -> tuple[WorkflowSnapshot, ...]:
        return tuple(item for item in self.list() if item.run_id == run_id)

    def find_by_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowSnapshot, ...]:
        return tuple(
            item for item in self.list() if item.workflow_id == workflow_id
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

    @staticmethod
    def _copy(snapshot: WorkflowSnapshot) -> WorkflowSnapshot:
        return WorkflowSnapshotCodec.decode(
            WorkflowSnapshotCodec.encode(snapshot)
        )
