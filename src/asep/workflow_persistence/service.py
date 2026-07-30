"""Serviço de aplicação para criar e persistir snapshots de workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import uuid4

from asep.workflow.models import (
    WorkflowDefinition,
    WorkflowExecutionResult,
)
from asep.workflow_persistence.models import WorkflowSnapshot
from asep.workflow_persistence.repository import WorkflowRepository

Clock = Callable[[], datetime]
IdGenerator = Callable[[], str]


class WorkflowPersistenceService:
    def __init__(
        self,
        repository: WorkflowRepository,
        *,
        clock: Clock | None = None,
        id_generator: IdGenerator | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def persist(
        self,
        workflow: WorkflowDefinition,
        result: WorkflowExecutionResult,
        *,
        agent_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkflowSnapshot:
        snapshot = self.create_snapshot(
            workflow,
            result,
            agent_id=agent_id,
            metadata=metadata,
        )
        self._repository.save(snapshot)
        return snapshot

    def create_snapshot(
        self,
        workflow: WorkflowDefinition,
        result: WorkflowExecutionResult,
        *,
        agent_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkflowSnapshot:
        if workflow.id != result.workflow_id:
            raise ValueError(
                "WorkflowDefinition diverge do WorkflowExecutionResult"
            )
        executed = set(result.executed_steps)
        version = workflow.metadata.get("version", "1.0")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("metadata.version do Workflow deve ser textual")
        return WorkflowSnapshot(
            id=self._id_generator(),
            workflow_id=workflow.id,
            run_id=result.run_id,
            workflow_version=version,
            name=workflow.name,
            description=workflow.description,
            status=result.status,
            started_at=result.started_at,
            finished_at=result.finished_at,
            duration_seconds=result.duration_seconds,
            executed_steps=result.executed_steps,
            pending_steps=tuple(
                step.id for step in workflow.steps if step.id not in executed
            ),
            agent_id=agent_id,
            timeline_event_ids=tuple(
                event.id for event in result.timeline
            ),
            metrics=result.metrics,
            metadata=metadata or {},
            created_at=self._clock(),
        )

    def get(self, snapshot_id: str) -> WorkflowSnapshot:
        return self._repository.get(snapshot_id)

    def list(self) -> tuple[WorkflowSnapshot, ...]:
        return self._repository.list()
