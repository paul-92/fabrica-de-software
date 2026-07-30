"""Execução sequencial de uma WorkflowDefinition validada."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from asep.timeline import TimelineEvent, TimelineEventType, TimelineRecorder
from asep.workflow.exceptions import WorkflowStepException
from asep.workflow.models import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowFailure,
    WorkflowStatus,
)
from asep.workflow.step_executor import WorkflowStepExecutor

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowExecutor:
    def __init__(
        self,
        timeline: TimelineRecorder,
        *,
        step_executor: WorkflowStepExecutor | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._timeline = timeline
        self._step_executor = step_executor or WorkflowStepExecutor()
        self._clock = clock or _utc_now

    def execute(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
    ) -> WorkflowExecutionResult:
        started_at = self._clock()
        completed: list[str] = []
        events: list[TimelineEvent] = []
        context.status = WorkflowStatus.RUNNING

        for step in workflow.steps:
            if (
                workflow.policy.allow_cancellation
                and context.cancellation_requested
            ):
                return self._cancel(
                    workflow,
                    context,
                    started_at,
                    completed,
                    events,
                )
            events.append(
                self._timeline.record(
                    context.run_id,
                    TimelineEventType.STAGE_STARTED,
                    stage_id=step.id,
                    message="Step iniciada.",
                )
            )
            try:
                self._step_executor.execute(step, context)
            except WorkflowStepException as exc:
                return self._fail(
                    workflow,
                    context,
                    started_at,
                    completed,
                    events,
                    exc,
                )
            if (
                workflow.policy.allow_cancellation
                and context.cancellation_requested
            ):
                events.append(
                    self._timeline.record(
                        context.run_id,
                        TimelineEventType.STAGE_FINISHED,
                        stage_id=step.id,
                        message="Step interrompida por cancelamento.",
                        metadata={"status": "cancelled"},
                    )
                )
                return self._cancel(
                    workflow,
                    context,
                    started_at,
                    completed,
                    events,
                    step.id,
                )
            completed.append(step.id)
            events.append(
                self._timeline.record(
                    context.run_id,
                    TimelineEventType.STAGE_FINISHED,
                    stage_id=step.id,
                    message="Step concluída.",
                    metadata={"status": "completed"},
                )
            )

        context.status = WorkflowStatus.COMPLETED
        return self._result(
            workflow,
            context,
            started_at,
            completed,
            events,
        )

    def _fail(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        started_at: datetime,
        completed: list[str],
        events: list[TimelineEvent],
        error: WorkflowStepException,
    ) -> WorkflowExecutionResult:
        context.status = WorkflowStatus.FAILED
        failure = WorkflowFailure(
            type=type(error.cause).__name__,
            message=str(error.cause) or type(error.cause).__name__,
            step_id=error.step_id,
        )
        events.append(
            self._timeline.record_error(
                context.run_id,
                error.cause,
                stage_id=error.step_id,
                message="Step falhou.",
            )
        )
        events.append(
            self._timeline.record(
                context.run_id,
                TimelineEventType.STAGE_FINISHED,
                stage_id=error.step_id,
                message="Step falhou.",
                metadata={"status": "failed"},
            )
        )
        return self._result(
            workflow,
            context,
            started_at,
            completed,
            events,
            failure=failure,
            failed_steps=(error.step_id,),
        )

    def _cancel(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        started_at: datetime,
        completed: list[str],
        events: list[TimelineEvent],
        step_id: str | None = None,
    ) -> WorkflowExecutionResult:
        context.status = WorkflowStatus.CANCELLED
        events.append(
            self._timeline.record(
                context.run_id,
                TimelineEventType.WARNING,
                stage_id=step_id,
                message="Workflow cancelado.",
            )
        )
        return self._result(
            workflow,
            context,
            started_at,
            completed,
            events,
        )

    def _result(
        self,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        started_at: datetime,
        completed: list[str],
        events: list[TimelineEvent],
        *,
        failure: WorkflowFailure | None = None,
        failed_steps: tuple[str, ...] = (),
    ) -> WorkflowExecutionResult:
        finished_at = self._clock()
        snapshot = context.snapshot()
        return WorkflowExecutionResult(
            run_id=context.run_id,
            workflow_id=workflow.id,
            status=context.status,
            started_at=started_at,
            finished_at=finished_at,
            completed_steps=tuple(completed),
            failed_steps=failed_steps,
            context=snapshot,
            error=failure,
            timeline=tuple(events),
            metrics={
                "total_steps": len(workflow.steps),
                "completed_steps": len(completed),
                "failed_steps": len(failed_steps),
                "duration_seconds": (
                    finished_at - started_at
                ).total_seconds(),
            },
            final_result=deepcopy_last_value(snapshot.values),
        )


def deepcopy_last_value(values: dict[str, object]) -> object:
    """Mantém resultado neutro sem impor uma chave obrigatória ao Context."""
    from copy import deepcopy

    return deepcopy(values.get("result"))
