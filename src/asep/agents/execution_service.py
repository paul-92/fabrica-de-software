"""Coordenação síncrona e determinística do runtime inteligente."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any

from pydantic import ValidationError

from asep.agents.contracts import (
    AgentError,
    AgentRequest,
    AgentResult,
    AgentStatus,
)
from asep.agents.exceptions import (
    AgentDuplicateExecutionError,
    AgentExecutionFailedError,
    AgentExecutionValidationError,
    AgentRetryExhaustedError,
)
from asep.agents.registry import AgentRegistry
from asep.agents.runtime_metrics import AgentExecutionMetricsRecorder
from asep.agents.runtime_models import (
    AgentExecutionContext,
    AgentExecutionPolicy,
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.agents.validator import AgentExecutionValidator
from asep.execution.models import AgentContext
from asep.timeline import TimelineEventType, TimelineRecorder

Clock = Callable[[], datetime]
_SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _NullMetricsRecorder:
    def record(
        self,
        result: AgentExecutionResult,
        capability: Any,
        *,
        retries: int,
    ) -> None:
        del result, capability, retries


class AgentExecutionService:
    """Implementação concreta da porta AgentRuntime."""

    def __init__(
        self,
        registry: AgentRegistry,
        *,
        timeline: TimelineRecorder,
        metrics: AgentExecutionMetricsRecorder | None = None,
        validator: AgentExecutionValidator | None = None,
        policy: AgentExecutionPolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._registry = registry
        self._timeline = timeline
        self._metrics = metrics or _NullMetricsRecorder()
        self._validator = validator or AgentExecutionValidator()
        self._policy = policy or AgentExecutionPolicy()
        self._clock = clock or _utc_now
        self._results: dict[str, AgentExecutionResult] = {}
        self._in_progress: set[str] = set()
        self._lock = RLock()

    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult:
        cached = self._begin(request.execution_id)
        if cached is not None:
            return cached
        try:
            return self._execute_new(request)
        finally:
            with self._lock:
                self._in_progress.discard(request.execution_id)

    def _execute_new(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult:
        started_at = self._clock()
        safe_metadata = self._event_metadata(request)
        self._record(
            request,
            TimelineEventType.AGENT_EXECUTION_REQUESTED,
            metadata=safe_metadata,
        )

        if request.cancellation_requested:
            result = self._terminal_result(
                request,
                AgentExecutionStatus.CANCELLED,
                started_at,
                attempts=0,
                error=AgentError(
                    code="cancelled",
                    message="Execução cancelada antes do início.",
                ),
            )
            self._record(
                request,
                TimelineEventType.AGENT_EXECUTION_CANCELLED,
                metadata={**safe_metadata, "status": result.status.value},
            )
            return self._complete(request, result, retries=0)

        try:
            agent = self._validator.validate(
                request,
                self._policy,
                self._registry,
            )
        except AgentExecutionValidationError as exc:
            result = self._terminal_result(
                request,
                AgentExecutionStatus.REJECTED,
                started_at,
                attempts=0,
                error=AgentError(
                    code="validation_rejected",
                    message="Solicitação de agente rejeitada.",
                    metadata={"error_type": type(exc).__name__},
                ),
            )
            self._record(
                request,
                TimelineEventType.AGENT_EXECUTION_REJECTED,
                metadata={
                    **safe_metadata,
                    "status": result.status.value,
                    "error_type": type(exc).__name__,
                },
            )
            self._metrics.record(result, request.capability, retries=0)
            if self._policy.fail_fast:
                raise
            return self._store(result)

        self._record(
            request,
            TimelineEventType.AGENT_EXECUTION_VALIDATED,
            metadata=safe_metadata,
        )
        last_error: AgentExecutionFailedError | None = None
        for attempt in range(1, self._policy.max_attempts + 1):
            runtime_context = self._runtime_context(
                request,
                started_at,
                attempt,
            )
            self._record(
                request,
                TimelineEventType.AGENT_EXECUTION_STARTED,
                metadata={**safe_metadata, "attempt": attempt},
            )
            try:
                agent_result = AgentResult.model_validate(
                    agent.execute(
                        self._agent_request(request),
                        self._agent_context(request, runtime_context),
                    )
                )
                self._validate_result_identity(request, agent_result)
            except Exception as exc:
                last_error = self._classify_error(request, exc)
                retryable = (
                    last_error.retryable
                    or self._policy.retry_unexpected_errors
                )
                if (
                    self._policy.retry_enabled
                    and retryable
                    and attempt < self._policy.max_attempts
                ):
                    self._record(
                        request,
                        TimelineEventType.AGENT_EXECUTION_RETRYING,
                        metadata={
                            **safe_metadata,
                            "attempt": attempt,
                            "error_type": last_error.error_type,
                        },
                    )
                    continue
                return self._failed_or_raise(
                    request,
                    started_at,
                    attempt,
                    last_error,
                )

            completed_at = self._clock()
            duration = max(
                0.0,
                (completed_at - started_at).total_seconds(),
            )
            timeout = request.timeout_seconds or self._policy.timeout_seconds
            if timeout is not None and duration > timeout:
                result = self._build_result(
                    request,
                    AgentExecutionStatus.TIMED_OUT,
                    started_at,
                    completed_at,
                    attempts=attempt,
                    error=AgentError(
                        code="timed_out",
                        message="Execução excedeu o timeout configurado.",
                    ),
                    agent_result=agent_result,
                )
                self._record(
                    request,
                    TimelineEventType.AGENT_EXECUTION_TIMED_OUT,
                    metadata={
                        **safe_metadata,
                        "attempt": attempt,
                        "status": result.status.value,
                    },
                )
                return self._complete(
                    request,
                    result,
                    retries=attempt - 1,
                )

            status = self._map_status(agent_result.status)
            error = (
                None
                if status is AgentExecutionStatus.SUCCEEDED
                else AgentError(
                    code=f"agent_{agent_result.status.value}",
                    message="Agente retornou resultado não concluído.",
                )
            )
            result = self._build_result(
                request,
                status,
                started_at,
                completed_at,
                attempts=attempt,
                error=error,
                agent_result=agent_result,
            )
            event_type = (
                TimelineEventType.AGENT_EXECUTION_SUCCEEDED
                if status is AgentExecutionStatus.SUCCEEDED
                else TimelineEventType.AGENT_EXECUTION_FAILED
                if status is AgentExecutionStatus.FAILED
                else TimelineEventType.AGENT_EXECUTION_REJECTED
            )
            self._record(
                request,
                event_type,
                metadata={
                    **safe_metadata,
                    "attempt": attempt,
                    "status": result.status.value,
                },
            )
            return self._complete(
                request,
                result,
                retries=attempt - 1,
            )

        assert last_error is not None  # pragma: no cover - defesa
        raise AgentRetryExhaustedError("Tentativas esgotadas.")

    def _begin(self, execution_id: str) -> AgentExecutionResult | None:
        with self._lock:
            cached = self._results.get(execution_id)
            if cached is not None:
                return cached
            if execution_id in self._in_progress:
                raise AgentDuplicateExecutionError(
                    f"execution_id já está em andamento: {execution_id}"
                )
            self._in_progress.add(execution_id)
            return None

    def _failed_or_raise(
        self,
        request: AgentExecutionRequest,
        started_at: datetime,
        attempts: int,
        failure: AgentExecutionFailedError,
    ) -> AgentExecutionResult:
        exhausted = self._policy.retry_enabled and attempts > 1
        result = self._terminal_result(
            request,
            AgentExecutionStatus.FAILED,
            started_at,
            attempts=attempts,
            error=AgentError(
                code="retry_exhausted" if exhausted else "execution_failed",
                message=(
                    "Tentativas de execução esgotadas."
                    if exhausted
                    else "Execução do agente falhou."
                ),
                retryable=failure.retryable,
                metadata={"error_type": failure.error_type},
            ),
        )
        self._record(
            request,
            TimelineEventType.AGENT_EXECUTION_FAILED,
            metadata={
                **self._event_metadata(request),
                "attempt": attempts,
                "status": result.status.value,
                "error_type": failure.error_type,
            },
        )
        self._metrics.record(
            result,
            request.capability,
            retries=attempts - 1,
        )
        if self._policy.fail_fast:
            if exhausted:
                raise AgentRetryExhaustedError(
                    f"Tentativas esgotadas para {request.agent_id}."
                ) from failure
            raise failure
        return self._store(result)

    def _complete(
        self,
        request: AgentExecutionRequest,
        result: AgentExecutionResult,
        *,
        retries: int,
    ) -> AgentExecutionResult:
        self._metrics.record(
            result,
            request.capability,
            retries=retries,
        )
        return self._store(result)

    def _store(
        self,
        result: AgentExecutionResult,
    ) -> AgentExecutionResult:
        with self._lock:
            self._results[result.execution_id] = result
        return result

    def _runtime_context(
        self,
        request: AgentExecutionRequest,
        started_at: datetime,
        attempt: int,
    ) -> AgentExecutionContext:
        timeout = request.timeout_seconds or self._policy.timeout_seconds
        return AgentExecutionContext(
            execution_id=request.execution_id,
            agent_id=request.agent_id,
            started_at=started_at,
            workflow_execution_id=request.workflow_execution_id,
            workflow_step_id=request.workflow_step_id,
            correlation_id=request.correlation_id,
            metadata=self._sanitize(request.metadata),
            cancellation_requested=request.cancellation_requested,
            attempt=attempt,
            deadline=(
                started_at + timedelta(seconds=timeout)
                if timeout is not None
                else None
            ),
        )

    @staticmethod
    def _agent_request(
        request: AgentExecutionRequest,
    ) -> AgentRequest:
        objective = request.context.get("objective", request.capability.id)
        if not isinstance(objective, str) or not objective.strip():
            objective = request.capability.id
        return AgentRequest(
            request_id=request.execution_id,
            objective=objective,
            inputs=request.input,
            metadata=request.metadata,
        )

    @staticmethod
    def _agent_context(
        request: AgentExecutionRequest,
        runtime: AgentExecutionContext,
    ) -> AgentContext:
        values = request.context

        def text(name: str, fallback: str) -> str:
            value = values.get(name, fallback)
            return value if isinstance(value, str) and value.strip() else fallback

        def texts(name: str) -> tuple[str, ...]:
            value = values.get(name, ())
            if not isinstance(value, (list, tuple)):
                return ()
            return tuple(item for item in value if isinstance(item, str))

        return AgentContext(
            run_id=request.workflow_execution_id or request.execution_id,
            project_id=text("project_id", "agent-runtime"),
            project_name=text("project_name", "Agent Runtime"),
            workflow_id=text(
                "workflow_id",
                "standalone-agent-execution",
            ),
            stage_id=request.workflow_step_id or "agent-execution",
            agent_id=request.agent_id.value,
            started_at=runtime.started_at,
            objective=text("objective", request.capability.id),
            scope_received=text(
                "scope_received",
                "AgentExecutionRequest.input",
            ),
            constraints=texts("constraints"),
            pending_items=texts("pending_items"),
        )

    @staticmethod
    def _validate_result_identity(
        request: AgentExecutionRequest,
        result: AgentResult,
    ) -> None:
        if (
            result.agent_id != request.agent_id.value
            or result.run_id
            != (request.workflow_execution_id or request.execution_id)
            or result.stage_id
            != (request.workflow_step_id or "agent-execution")
        ):
            raise AgentExecutionFailedError(
                request.agent_id.value,
                error_type="AgentResultIdentityMismatch",
            )

    @staticmethod
    def _classify_error(
        request: AgentExecutionRequest,
        error: Exception,
    ) -> AgentExecutionFailedError:
        if isinstance(error, AgentExecutionFailedError):
            return error
        if isinstance(error, ValidationError):
            error_type = "AgentResultValidationError"
        else:
            error_type = type(error).__name__
        return AgentExecutionFailedError(
            request.agent_id.value,
            error_type=error_type,
        )

    def _terminal_result(
        self,
        request: AgentExecutionRequest,
        status: AgentExecutionStatus,
        started_at: datetime,
        *,
        attempts: int,
        error: AgentError,
    ) -> AgentExecutionResult:
        return self._build_result(
            request,
            status,
            started_at,
            self._clock(),
            attempts=attempts,
            error=error,
        )

    @staticmethod
    def _build_result(
        request: AgentExecutionRequest,
        status: AgentExecutionStatus,
        started_at: datetime,
        completed_at: datetime,
        *,
        attempts: int,
        error: AgentError | None,
        agent_result: AgentResult | None = None,
    ) -> AgentExecutionResult:
        duration = max(0.0, (completed_at - started_at).total_seconds())
        return AgentExecutionResult(
            execution_id=request.execution_id,
            agent_id=request.agent_id,
            status=status,
            output=(
                {}
                if agent_result is None
                else agent_result.model_dump(mode="json")
            ),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            attempts=attempts,
            error=error,
            metadata=AgentExecutionService._sanitize(request.metadata),
            agent_result=agent_result,
        )

    def _record(
        self,
        request: AgentExecutionRequest,
        event_type: TimelineEventType,
        *,
        metadata: Mapping[str, Any],
    ) -> None:
        self._timeline.record(
            request.workflow_execution_id or request.execution_id,
            event_type,
            stage_id=request.workflow_step_id,
            message=event_type.value,
            metadata=metadata,
        )

    @staticmethod
    def _event_metadata(
        request: AgentExecutionRequest,
    ) -> dict[str, Any]:
        return {
            "execution_id": request.execution_id,
            "agent_id": request.agent_id.value,
            "capability": request.capability.id,
            "workflow_execution_id": request.workflow_execution_id,
            "workflow_step_id": request.workflow_step_id,
            "correlation_id": request.correlation_id,
        }

    @staticmethod
    def _sanitize(value: Mapping[str, Any]) -> dict[str, Any]:
        def clean(item: Any) -> Any:
            if isinstance(item, Mapping):
                return {
                    str(key): clean(child)
                    for key, child in item.items()
                    if str(key).lower() not in _SENSITIVE_KEYS
                }
            if isinstance(item, (list, tuple)):
                return [clean(child) for child in item]
            return item

        return clean(value)

    @staticmethod
    def _map_status(status: AgentStatus) -> AgentExecutionStatus:
        return {
            AgentStatus.COMPLETED: AgentExecutionStatus.SUCCEEDED,
            AgentStatus.FAILED: AgentExecutionStatus.FAILED,
            AgentStatus.BLOCKED: AgentExecutionStatus.REJECTED,
            AgentStatus.AWAITING_APPROVAL: AgentExecutionStatus.REJECTED,
        }[status]


__all__ = ["AgentExecutionService"]
