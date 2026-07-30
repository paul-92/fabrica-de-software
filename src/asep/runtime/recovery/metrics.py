"""Métricas locais da supervisão e recuperação."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RecoveryMetricsSnapshot:
    executions_total: int
    executions_succeeded: int
    executions_failed: int
    retries_total: int
    retry_success_rate: float
    fallbacks_total: int
    recoveries_total: int
    average_retry_count: float
    average_execution_time: float


@runtime_checkable
class RecoveryMetricsRecorder(Protocol):
    def execution_completed(
        self,
        *,
        succeeded: bool,
        duration_seconds: float,
        retries: int,
    ) -> None: ...

    def retry_completed(self, *, succeeded: bool) -> None: ...
    def fallback_completed(self) -> None: ...
    def recovery_completed(self) -> None: ...


class InMemoryRecoveryMetrics:
    def __init__(self) -> None:
        self._executions = 0
        self._succeeded = 0
        self._failed = 0
        self._retries = 0
        self._retry_successes = 0
        self._fallbacks = 0
        self._recoveries = 0
        self._retry_counts = 0
        self._execution_time = 0.0

    def execution_completed(
        self,
        *,
        succeeded: bool,
        duration_seconds: float,
        retries: int,
    ) -> None:
        self._executions += 1
        self._succeeded += int(succeeded)
        self._failed += int(not succeeded)
        self._retry_counts += retries
        self._execution_time += duration_seconds

    def retry_completed(self, *, succeeded: bool) -> None:
        self._retries += 1
        self._retry_successes += int(succeeded)

    def fallback_completed(self) -> None:
        self._fallbacks += 1

    def recovery_completed(self) -> None:
        self._recoveries += 1

    def snapshot(self) -> RecoveryMetricsSnapshot:
        return RecoveryMetricsSnapshot(
            executions_total=self._executions,
            executions_succeeded=self._succeeded,
            executions_failed=self._failed,
            retries_total=self._retries,
            retry_success_rate=(
                self._retry_successes / self._retries
                if self._retries
                else 0.0
            ),
            fallbacks_total=self._fallbacks,
            recoveries_total=self._recoveries,
            average_retry_count=(
                self._retry_counts / self._executions
                if self._executions
                else 0.0
            ),
            average_execution_time=(
                self._execution_time / self._executions
                if self._executions
                else 0.0
            ),
        )


__all__ = [
    "InMemoryRecoveryMetrics",
    "RecoveryMetricsRecorder",
    "RecoveryMetricsSnapshot",
]
