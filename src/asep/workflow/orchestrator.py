"""Lifecycle externo e delegação ao Workflow Engine."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from asep.runs import Run, RunError, RunRepository, RunStatus
from asep.timeline import (
    TimelineEventType,
    TimelineRecorder,
    TimelineRepository,
)
from asep.workflow.engine import WorkflowEngine
from asep.workflow.executor import WorkflowExecutor
from asep.workflow.models import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowFailure,
    WorkflowStatus,
)
from asep.workflow.validator import WorkflowValidator

Clock = Callable[[], datetime]
EventIdGenerator = Callable[[], str]


class WorkflowPersistencePort(Protocol):
    def persist(
        self,
        workflow: WorkflowDefinition,
        result: WorkflowExecutionResult,
    ) -> object: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowOrchestrator:
    """Inicia/finaliza Runs e delega interpretação e Steps ao Engine."""

    def __init__(
        self,
        run_repository: RunRepository,
        timeline_repository: TimelineRepository,
        *,
        engine: WorkflowEngine | None = None,
        clock: Clock | None = None,
        event_id_generator: EventIdGenerator | None = None,
        workflow_persistence: WorkflowPersistencePort | None = None,
    ) -> None:
        self._runs = run_repository
        self._clock = clock or _utc_now
        self._timeline = TimelineRecorder(
            timeline_repository,
            clock=self._clock,
            id_generator=event_id_generator,
        )
        self._engine = engine or WorkflowEngine(
            WorkflowValidator(),
            WorkflowExecutor(
                self._timeline,
                clock=self._clock,
            ),
        )
        self._workflow_persistence = workflow_persistence

    def execute(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
    ) -> WorkflowExecutionResult:
        started_at = self._clock()
        self._save_run(
            workflow,
            context,
            RunStatus.PENDING,
            started_at,
        )
        context.status = WorkflowStatus.RUNNING
        self._save_run(
            workflow,
            context,
            RunStatus.RUNNING,
            started_at,
        )
        run_started = self._timeline.record(
            context.run_id,
            TimelineEventType.RUN_STARTED,
            message="Workflow iniciado.",
            metadata={"workflow_id": workflow.id},
        )

        result = self._engine.execute(workflow, context)
        run_status, summary = self._terminal_projection(result.status)
        self._save_run(
            workflow,
            context,
            run_status,
            started_at,
            finished_at=result.finished_at,
            stage_id=(
                result.error.step_id
                if result.error is not None
                else None
            ),
            summary=summary,
            failure=result.error,
        )
        run_finished = self._timeline.record(
            context.run_id,
            TimelineEventType.RUN_FINISHED,
            stage_id=(
                result.error.step_id
                if result.error is not None
                else None
            ),
            message=summary,
            metadata={"status": result.status.value},
        )
        final_result = replace(
            result,
            started_at=started_at,
            timeline=(run_started, *result.timeline, run_finished),
        )
        if self._workflow_persistence is not None:
            self._workflow_persistence.persist(workflow, final_result)
        return final_result

    @staticmethod
    def _terminal_projection(
        status: WorkflowStatus,
    ) -> tuple[RunStatus, str]:
        projections = {
            WorkflowStatus.COMPLETED: (
                RunStatus.SUCCEEDED,
                "Workflow concluído.",
            ),
            WorkflowStatus.FAILED: (
                RunStatus.FAILED,
                "Workflow falhou.",
            ),
            WorkflowStatus.CANCELLED: (
                RunStatus.CANCELLED,
                "Workflow cancelado.",
            ),
        }
        return projections[status]

    def _save_run(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        status: RunStatus,
        started_at: datetime,
        *,
        finished_at: datetime | None = None,
        stage_id: str | None = None,
        summary: str | None = None,
        failure: WorkflowFailure | None = None,
    ) -> None:
        run_error = (
            None
            if failure is None
            else RunError(
                type=failure.type,
                message=failure.message,
                details={"step_id": failure.step_id},
            )
        )
        self._runs.save(
            Run(
                id=context.run_id,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                workflow_id=workflow.id,
                stage_id=stage_id,
                summary=summary,
                error=run_error,
                metadata={
                    "workflow_status": context.status.value,
                    "step_count": len(workflow.steps),
                },
            )
        )
