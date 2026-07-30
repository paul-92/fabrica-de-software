"""Aplicação determinística de retry e fallback sobre AgentRuntime."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter, sleep

from asep.agents.contracts import AgentCapability, AgentError
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.runtime.recovery.backoff import (
    BackoffStrategy,
    ConstantBackoff,
    ExponentialBackoff,
    LinearBackoff,
)
from asep.runtime.recovery.classifier import FailureClassifier
from asep.runtime.recovery.metrics import RecoveryMetricsRecorder
from asep.runtime.recovery.models import (
    BackoffKind,
    FailureCategory,
    FallbackAction,
    RecoveryContext,
    RecoveryPolicy,
    RecoveryResult,
    RetryDecision,
    SupervisedExecutionState,
)
from asep.runtime.recovery.state_machine import ExecutionStateMachine
from asep.runtime.recovery.validator import RecoveryValidator
from asep.timeline import TimelineEventType, TimelineRecorder

Clock = Callable[[], datetime]
Timer = Callable[[], float]
Sleeper = Callable[[float], None]
Operation = Callable[[AgentExecutionRequest], AgentExecutionResult]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ExecutionRecoveryService:
    def __init__(
        self,
        *,
        timeline: TimelineRecorder,
        metrics: RecoveryMetricsRecorder,
        policy: RecoveryPolicy | None = None,
        classifier: FailureClassifier | None = None,
        validator: RecoveryValidator | None = None,
        backoffs: dict[BackoffKind, BackoffStrategy] | None = None,
        clock: Clock | None = None,
        timer: Timer | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._timeline = timeline
        self._metrics = metrics
        self._policy = policy or RecoveryPolicy()
        self._classifier = classifier or FailureClassifier()
        self._validator = validator or RecoveryValidator()
        self._backoffs = backoffs or {
            BackoffKind.CONSTANT: ConstantBackoff(),
            BackoffKind.LINEAR: LinearBackoff(),
            BackoffKind.EXPONENTIAL: ExponentialBackoff(),
        }
        self._clock = clock or _utc_now
        self._timer = timer or perf_counter
        self._sleeper = sleeper or sleep

    def recover(
        self,
        context: RecoveryContext,
        operation: Operation,
        state_machine: ExecutionStateMachine,
    ) -> RecoveryResult:
        self._validator.validate(context, self._policy)
        started = self._timer()
        run_id = (
            context.request.workflow_execution_id
            or context.request.execution_id
        )
        actions: list[str] = []
        messages: list[str] = []
        attempts = context.attempts
        last_category: FailureCategory | None = None
        last_result: AgentExecutionResult | None = None
        retry_active = False
        request = context.request

        while True:
            attempts += 1
            result, raised = self._invoke(operation, request)
            if result.status is AgentExecutionStatus.SUCCEEDED:
                if retry_active:
                    self._record(
                        run_id,
                        TimelineEventType.RETRY_COMPLETED,
                        {"attempt": attempts},
                    )
                    self._metrics.retry_completed(succeeded=True)
                state_machine.transition(
                    SupervisedExecutionState.SUCCEEDED
                )
                return self._result(
                    state_machine,
                    actions,
                    attempts,
                    started,
                    messages,
                    last_category,
                    result,
                )

            category = self._classifier.classify(raised or result)
            last_category = category
            last_result = result
            if retry_active:
                self._record(
                    run_id,
                    TimelineEventType.RETRY_FAILED,
                    {"attempt": attempts, "category": category.value},
                )
                self._metrics.retry_completed(succeeded=False)
                retry_active = False
            decision = self._policy.retry.decide(category, attempts)
            if decision is RetryDecision.RETRY:
                state_machine.transition(
                    SupervisedExecutionState.RETRYING
                )
                delay = self._backoffs[
                    self._policy.retry.backoff
                ].delay(attempts, self._policy.retry)
                actions.append(f"retry:{attempts + 1}")
                self._record(
                    run_id,
                    TimelineEventType.RETRY_STARTED,
                    {
                        "attempt": attempts + 1,
                        "delay_seconds": delay,
                        "category": category.value,
                    },
                )
                self._sleeper(delay)
                state_machine.transition(
                    SupervisedExecutionState.RUNNING
                )
                request = request.model_copy(
                    update={
                        "execution_id": (
                            f"{context.request.execution_id}"
                            f"-retry-{attempts + 1}"
                        )
                    }
                )
                retry_active = True
                continue
            if decision is RetryDecision.LIMIT_EXCEEDED:
                messages.append("Limite de tentativas atingido.")
            else:
                messages.append("Falha não elegível para retry.")
            break

        state_machine.transition(SupervisedExecutionState.RECOVERING)
        recovered, fallback_attempts = self._fallback(
            run_id,
            request,
            last_result,
            operation,
            state_machine,
            actions,
        )
        attempts += fallback_attempts
        self._metrics.recovery_completed()
        self._record(
            run_id,
            TimelineEventType.RECOVERY_COMPLETED,
            {
                "state": state_machine.state.value,
                "attempts": attempts,
            },
        )
        return self._result(
            state_machine,
            actions,
            attempts,
            started,
            messages,
            last_category,
            recovered,
        )

    def _fallback(
        self,
        run_id: str,
        request: AgentExecutionRequest,
        failed: AgentExecutionResult,
        operation: Operation,
        state_machine: ExecutionStateMachine,
        actions: list[str],
    ) -> tuple[AgentExecutionResult, int]:
        action = self._policy.fallback.action
        actions.append(f"fallback:{action.value}")
        self._record(
            run_id,
            TimelineEventType.FALLBACK_STARTED,
            {"action": action.value},
        )
        if action is FallbackAction.FAIL:
            state_machine.transition(SupervisedExecutionState.FAILED)
            self._metrics.fallback_completed()
            self._record(
                run_id,
                TimelineEventType.FALLBACK_FAILED,
                {"action": action.value},
            )
            return failed, 0
        if action is FallbackAction.CANCEL_WORKFLOW:
            result = self._cancelled(failed)
            state_machine.transition(SupervisedExecutionState.CANCELLED)
        elif action is FallbackAction.IGNORE_STEP:
            result = self._ignored(failed)
            state_machine.transition(SupervisedExecutionState.SUCCEEDED)
        else:
            fallback_request = request.model_copy(
                update={
                    "execution_id": (
                        f"{request.execution_id}-fallback"
                    ),
                    "agent_id": (
                        self._policy.fallback.replacement_agent_id
                        if action is FallbackAction.SUBSTITUTE_AGENT
                        else request.agent_id
                    ),
                    "capability": (
                        AgentCapability(
                            id=self._policy.fallback.alternative_capability
                        )
                        if action is FallbackAction.ALTERNATIVE_STEP
                        else request.capability
                    ),
                }
            )
            state_machine.transition(SupervisedExecutionState.RUNNING)
            result, _ = self._invoke(operation, fallback_request)
            state_machine.transition(
                SupervisedExecutionState.SUCCEEDED
                if result.status is AgentExecutionStatus.SUCCEEDED
                else SupervisedExecutionState.FAILED
            )
        succeeded = state_machine.state is (
            SupervisedExecutionState.SUCCEEDED
        )
        self._metrics.fallback_completed()
        self._record(
            run_id,
            (
                TimelineEventType.FALLBACK_COMPLETED
                if succeeded
                else TimelineEventType.FALLBACK_FAILED
            ),
            {"action": action.value},
        )
        return result, int(
            action
            in {
                FallbackAction.SUBSTITUTE_AGENT,
                FallbackAction.ALTERNATIVE_STEP,
            }
        )

    def _invoke(
        self, operation: Operation, request: AgentExecutionRequest
    ) -> tuple[AgentExecutionResult, BaseException | None]:
        try:
            return operation(request), None
        except Exception as exc:
            now = self._clock()
            return (
                AgentExecutionResult(
                    execution_id=request.execution_id,
                    agent_id=request.agent_id,
                    status=AgentExecutionStatus.FAILED,
                    started_at=now,
                    completed_at=now,
                    duration_seconds=0,
                    attempts=1,
                    error=AgentError(
                        code="supervised_exception",
                        message="Execução supervisionada falhou.",
                        metadata={"error_type": type(exc).__name__},
                    ),
                    metadata=request.metadata,
                ),
                exc,
            )

    @staticmethod
    def _ignored(
        result: AgentExecutionResult,
    ) -> AgentExecutionResult:
        return AgentExecutionResult.model_validate(
            {
                **result.model_dump(mode="json"),
                "status": AgentExecutionStatus.SUCCEEDED,
                "error": None,
                "output": {
                    **result.model_dump(mode="json")["output"],
                    "fallback": "ignored_step",
                },
            }
        )

    @staticmethod
    def _cancelled(
        result: AgentExecutionResult,
    ) -> AgentExecutionResult:
        return AgentExecutionResult.model_validate(
            {
                **result.model_dump(mode="json"),
                "status": AgentExecutionStatus.CANCELLED,
                "error": {
                    "code": "workflow_cancelled",
                    "message": "Workflow cancelado pela política de fallback.",
                },
            }
        )

    def _result(
        self,
        machine: ExecutionStateMachine,
        actions: list[str],
        attempts: int,
        started: float,
        messages: list[str],
        category: FailureCategory | None,
        result: AgentExecutionResult,
    ) -> RecoveryResult:
        return RecoveryResult(
            final_state=machine.state,
            actions=tuple(actions),
            attempts=attempts,
            duration_seconds=max(0.0, self._timer() - started),
            messages=tuple(messages),
            category=category,
            execution_result=result,
        )

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


RecoveryService = ExecutionRecoveryService

__all__ = ["ExecutionRecoveryService", "RecoveryService"]
