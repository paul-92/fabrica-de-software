"""Porta neutra de persistência de WorkflowSnapshot."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from asep.workflow.models import WorkflowStatus
from asep.workflow_persistence.models import WorkflowSnapshot


@runtime_checkable
class WorkflowRepository(Protocol):
    def save(self, snapshot: WorkflowSnapshot) -> None: ...

    def update(self, snapshot: WorkflowSnapshot) -> None: ...

    def get(self, snapshot_id: str) -> WorkflowSnapshot: ...

    def exists(self, snapshot_id: str) -> bool: ...

    def list(self) -> tuple[WorkflowSnapshot, ...]: ...

    def find_by_status(
        self,
        status: WorkflowStatus,
    ) -> tuple[WorkflowSnapshot, ...]: ...

    def find_by_run(
        self,
        run_id: str,
    ) -> tuple[WorkflowSnapshot, ...]: ...

    def find_by_workflow(
        self,
        workflow_id: str,
    ) -> tuple[WorkflowSnapshot, ...]: ...

    def find_by_period(
        self,
        started_at: datetime,
        finished_at: datetime,
    ) -> tuple[WorkflowSnapshot, ...]: ...
