"""Coordenação síncrona e segura da execução de Tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from asep.timeline import TimelineEventType, TimelineRecorder
from asep.tools.exceptions import (
    ToolDuplicateExecutionError,
    ToolExecutionError,
    ToolRetryExhaustedError,
    ToolTimeoutError,
    ToolValidationError,
)
from asep.tools.metrics import ToolMetricsRecorder
from asep.tools.models import (
    ToolContext,
    ToolError,
    ToolExecutionPolicy,
    ToolExecutionStatus,
    ToolRequest,
    ToolResult,
)
from asep.tools.registry import ToolRegistry
from asep.tools.validator import ToolValidator

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


class _NullMetrics:
    def record(self, result, capability, *, retries: int) -> None:
        del result, capability, retries


class ToolExecutionService:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        timeline: TimelineRecorder,
        metrics: ToolMetricsRecorder | None = None,
        validator: ToolValidator | None = None,
        policy: ToolExecutionPolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._registry = registry
        self._timeline = timeline
        self._metrics = metrics or _NullMetrics()
        self._validator = validator or ToolValidator()
        self._policy = policy or ToolExecutionPolicy()
        self._clock = clock or _utc_now
        self._results: dict[str, ToolResult] = {}
        self._in_progress: set[str] = set()
        self._lock = RLock()

    def execute(self, request: ToolRequest) -> ToolResult:
        cached = self._begin(request.execution_id)
        if cached is not None:
            return cached
        try:
            return self._execute_new(request)
        finally:
            with self._lock:
                self._in_progress.discard(request.execution_id)

    def _execute_new(self, request: ToolRequest) -> ToolResult:
        started_at = self._clock()
        event_metadata = self._event_metadata(request)
        self._record(
            request, TimelineEventType.TOOL_REQUESTED, event_metadata
        )
        try:
            tool, workspace = self._validator.validate(
                request, self._policy, self._registry
            )
        except ToolValidationError as exc:
            result = self._result(
                request,
                ToolExecutionStatus.REJECTED,
                started_at,
                self._clock(),
                attempts=0,
                error=ToolError(
                    code="validation_rejected",
                    message="Solicitação de Tool rejeitada.",
                    metadata={"error_type": type(exc).__name__},
                ),
            )
            self._record(
                request,
                TimelineEventType.TOOL_REJECTED,
                {
                    **event_metadata,
                    "status": result.status.value,
                    "error_type": type(exc).__name__,
                },
            )
            self._metrics.record(result, request.capability, retries=0)
            if self._policy.fail_fast:
                raise
            return self._store(result)

        self._record(
            request, TimelineEventType.TOOL_VALIDATED, event_metadata
        )
        last_failure: ToolExecutionError | None = None
        for attempt in range(1, self._policy.max_attempts + 1):
            self._record(
                request,
                TimelineEventType.TOOL_STARTED,
                {**event_metadata, "attempt": attempt},
            )
            context = ToolContext(
                execution_id=request.execution_id,
                started_at=started_at,
                workspace=Path(workspace),
                attempt=attempt,
                metadata=self._sanitize(request.metadata),
                correlation_id=request.correlation_id,
            )
            try:
                raw_result = tool.execute(request, context)
                if (
                    not isinstance(raw_result, ToolResult)
                    or raw_result.execution_id != request.execution_id
                    or raw_result.tool_id != request.tool_id
                ):
                    raise ToolExecutionError(
                        str(request.tool_id),
                        error_type="ToolResultIdentityMismatch",
                    )
            except ToolTimeoutError as exc:
                return self._timeout_result(
                    request, started_at, attempt, exc
                )
            except Exception as exc:
                last_failure = (
                    exc
                    if isinstance(exc, ToolExecutionError)
                    else ToolExecutionError(
                        str(request.tool_id),
                        error_type=type(exc).__name__,
                    )
                )
                if (
                    self._policy.retry_enabled
                    and last_failure.retryable
                    and attempt < self._policy.max_attempts
                ):
                    continue
                return self._failed_or_raise(
                    request, started_at, attempt, last_failure
                )

            completed_at = self._clock()
            timeout = request.timeout_seconds or self._policy.timeout_seconds
            duration = max(
                0.0, (completed_at - started_at).total_seconds()
            )
            if timeout is not None and duration > timeout:
                return self._timeout_result(
                    request,
                    started_at,
                    attempt,
                    ToolTimeoutError(
                        str(request.tool_id), error_type="DurationExceeded"
                    ),
                    completed_at=completed_at,
                )
            result = self._result(
                request,
                raw_result.status,
                started_at,
                completed_at,
                attempts=attempt,
                output=raw_result.output,
                error=raw_result.error,
            )
            event_type = (
                TimelineEventType.TOOL_SUCCEEDED
                if result.status is ToolExecutionStatus.SUCCEEDED
                else TimelineEventType.TOOL_FAILED
            )
            self._record(
                request,
                event_type,
                {
                    **event_metadata,
                    "attempt": attempt,
                    "status": result.status.value,
                },
            )
            return self._complete(request, result, attempt - 1)
        assert last_failure is not None  # pragma: no cover
        raise last_failure

    def _failed_or_raise(
        self,
        request: ToolRequest,
        started_at: datetime,
        attempt: int,
        failure: ToolExecutionError,
    ) -> ToolResult:
        exhausted = self._policy.retry_enabled and attempt > 1
        result = self._result(
            request,
            ToolExecutionStatus.FAILED,
            started_at,
            self._clock(),
            attempts=attempt,
            error=ToolError(
                code="retry_exhausted" if exhausted else "execution_failed",
                message="Execução da Tool falhou.",
                retryable=failure.retryable,
                metadata={"error_type": failure.error_type},
            ),
        )
        self._record(
            request,
            TimelineEventType.TOOL_FAILED,
            {
                **self._event_metadata(request),
                "attempt": attempt,
                "status": result.status.value,
                "error_type": failure.error_type,
            },
        )
        self._metrics.record(
            result, request.capability, retries=attempt - 1
        )
        if self._policy.fail_fast:
            if exhausted:
                raise ToolRetryExhaustedError(
                    str(request.tool_id),
                    error_type=failure.error_type,
                    retryable=failure.retryable,
                ) from failure
            raise failure
        return self._store(result)

    def _timeout_result(
        self,
        request: ToolRequest,
        started_at: datetime,
        attempt: int,
        failure: ToolTimeoutError,
        *,
        completed_at: datetime | None = None,
    ) -> ToolResult:
        result = self._result(
            request,
            ToolExecutionStatus.TIMED_OUT,
            started_at,
            completed_at or self._clock(),
            attempts=attempt,
            error=ToolError(
                code="timed_out",
                message="Execução da Tool excedeu o timeout.",
                retryable=failure.retryable,
                metadata={"error_type": failure.error_type},
            ),
        )
        self._record(
            request,
            TimelineEventType.TOOL_TIMEOUT,
            {
                **self._event_metadata(request),
                "attempt": attempt,
                "status": result.status.value,
            },
        )
        return self._complete(request, result, attempt - 1)

    def _begin(self, execution_id: str) -> ToolResult | None:
        with self._lock:
            if execution_id in self._results:
                return self._results[execution_id]
            if execution_id in self._in_progress:
                raise ToolDuplicateExecutionError(
                    f"execution_id já está em andamento: {execution_id}"
                )
            self._in_progress.add(execution_id)
        return None

    def _complete(
        self, request: ToolRequest, result: ToolResult, retries: int
    ) -> ToolResult:
        self._metrics.record(result, request.capability, retries=retries)
        return self._store(result)

    def _store(self, result: ToolResult) -> ToolResult:
        with self._lock:
            self._results[result.execution_id] = result
        return result

    @staticmethod
    def _result(
        request: ToolRequest,
        status: ToolExecutionStatus,
        started_at: datetime,
        completed_at: datetime,
        *,
        attempts: int,
        output: Mapping[str, Any] | None = None,
        error: ToolError | None = None,
    ) -> ToolResult:
        return ToolResult(
            execution_id=request.execution_id,
            tool_id=request.tool_id,
            status=status,
            output=output or {},
            duration_seconds=max(
                0.0, (completed_at - started_at).total_seconds()
            ),
            started_at=started_at,
            completed_at=completed_at,
            attempts=attempts,
            error=error,
            metadata=ToolExecutionService._sanitize(request.metadata),
        )

    def _record(
        self,
        request: ToolRequest,
        event_type: TimelineEventType,
        metadata: Mapping[str, Any],
    ) -> None:
        self._timeline.record(
            request.workflow_execution_id or request.execution_id,
            event_type,
            message=event_type.value,
            metadata=metadata,
        )

    @staticmethod
    def _event_metadata(request: ToolRequest) -> dict[str, Any]:
        return {
            "execution_id": request.execution_id,
            "tool_id": request.tool_id.value,
            "capability": request.capability.id,
            "workflow_execution_id": request.workflow_execution_id,
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


__all__ = ["ToolExecutionService"]

