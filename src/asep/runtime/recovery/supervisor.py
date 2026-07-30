"""AgentRuntime decorador com lifecycle supervisionado."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from asep.agents.runtime import AgentRuntime
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.runtime.recovery.metrics import RecoveryMetricsRecorder
from asep.runtime.recovery.models import (
    RecoveryContext,
    SupervisedExecutionState,
)
from asep.runtime.recovery.service import ExecutionRecoveryService
from asep.runtime.recovery.state_machine import ExecutionStateMachine
from asep.timeline import TimelineEventType, TimelineRecorder

Timer = Callable[[], float]


class DefaultExecutionSupervisor:
    def __init__(
        self,
        runtime: AgentRuntime,
        recovery: ExecutionRecoveryService,
        *,
        timeline: TimelineRecorder,
        metrics: RecoveryMetricsRecorder,
        timer: Timer | None = None,
    ) -> None:
        self._runtime = runtime
        self._recovery = recovery
        self._timeline = timeline
        self._metrics = metrics
        self._timer = timer or perf_counter

    def execute(
        self, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        started = self._timer()
        run_id = request.workflow_execution_id or request.execution_id
        machine = ExecutionStateMachine()
        machine.transition(SupervisedExecutionState.READY)
        machine.transition(SupervisedExecutionState.RUNNING)
        self._record(run_id, TimelineEventType.EXECUTION_STARTED)
        recovery_result = self._recovery.recover(
            RecoveryContext(
                request=request,
                agent_id=request.agent_id,
                metadata=request.metadata,
            ),
            self._runtime.execute,
            machine,
        )
        result = recovery_result.execution_result
        assert result is not None  # validado pelo RecoveryService
        duration = max(0.0, self._timer() - started)
        succeeded = (
            recovery_result.final_state
            is SupervisedExecutionState.SUCCEEDED
        )
        self._metrics.execution_completed(
            succeeded=succeeded,
            duration_seconds=duration,
            retries=sum(
                action.startswith("retry:")
                for action in recovery_result.actions
            ),
        )
        if recovery_result.final_state is (
            SupervisedExecutionState.CANCELLED
        ):
            event_type = TimelineEventType.EXECUTION_CANCELLED
        elif succeeded:
            event_type = TimelineEventType.EXECUTION_COMPLETED
        else:
            event_type = TimelineEventType.EXECUTION_FAILED
        self._record(
            run_id,
            event_type,
            {
                "attempts": recovery_result.attempts,
                "state": recovery_result.final_state.value,
                "status": result.status.value,
            },
        )
        return result

    def _record(
        self,
        run_id: str,
        event_type: TimelineEventType,
        metadata=None,
    ) -> None:
        self._timeline.record(
            run_id,
            event_type,
            message=event_type.value,
            metadata=metadata or {},
        )


ExecutionSupervisor = DefaultExecutionSupervisor

__all__ = ["DefaultExecutionSupervisor", "ExecutionSupervisor"]
