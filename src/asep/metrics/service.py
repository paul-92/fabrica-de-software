"""Cálculo sob demanda de métricas sobre o RunQueryService."""

from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import fmean, median

from asep.application import RunQueryService
from asep.metrics.models import (
    DurationMetrics,
    MetricsSummary,
    ProviderMetrics,
    StatusMetrics,
)
from asep.runs import Run, RunStatus


class MetricsService:
    """Produz snapshots analíticos sem acessar armazenamento diretamente."""

    def __init__(self, run_query_service: RunQueryService) -> None:
        self._run_query_service = run_query_service

    def get_summary(self) -> MetricsSummary:
        runs = self._run_query_service.list_runs()
        counts, unknown_count = self._status_counts(runs)
        successful = counts[RunStatus.SUCCEEDED]
        failed = counts[RunStatus.FAILED]
        eligible = successful + failed
        success_rate, failure_rate = self._rates(successful, failed)
        return MetricsSummary(
            total_runs=len(runs),
            successful_runs=successful,
            failed_runs=failed,
            running_runs=counts[RunStatus.RUNNING],
            pending_runs=counts[RunStatus.PENDING],
            cancelled_runs=counts[RunStatus.CANCELLED],
            unknown_status_runs=unknown_count,
            eligible_runs=eligible,
            success_rate=success_rate,
            failure_rate=failure_rate,
            duration=self._duration_metrics(runs),
        )

    def count_by_status(self) -> tuple[StatusMetrics, ...]:
        runs = self._run_query_service.list_runs()
        counts, _ = self._status_counts(runs)
        return tuple(
            StatusMetrics(status=status, count=counts[status])
            for status in RunStatus
        )

    def get_duration_metrics(self) -> DurationMetrics:
        runs = self._run_query_service.list_runs()
        return self._duration_metrics(runs)

    def metrics_by_provider(self) -> tuple[ProviderMetrics, ...]:
        runs = self._run_query_service.list_runs()
        grouped: dict[str | None, list[Run]] = {}
        for run in runs:
            grouped.setdefault(
                getattr(run, "provider_name", None), []
            ).append(run)

        return tuple(
            self._provider_metrics(provider_name, grouped[provider_name])
            for provider_name in sorted(
                grouped,
                key=lambda value: (value is not None, value or ""),
            )
        )

    @classmethod
    def _provider_metrics(
        cls,
        provider_name: str | None,
        runs: tuple[Run, ...] | list[Run],
    ) -> ProviderMetrics:
        counts, unknown_count = cls._status_counts(runs)
        successful = counts[RunStatus.SUCCEEDED]
        failed = counts[RunStatus.FAILED]
        success_rate, failure_rate = cls._rates(successful, failed)
        return ProviderMetrics(
            provider_name=provider_name,
            total_runs=len(runs),
            successful_runs=successful,
            failed_runs=failed,
            running_runs=counts[RunStatus.RUNNING],
            unknown_status_runs=unknown_count,
            eligible_runs=successful + failed,
            success_rate=success_rate,
            failure_rate=failure_rate,
            duration=cls._duration_metrics(runs),
        )

    @staticmethod
    def _status_counts(
        runs: Iterable[Run],
    ) -> tuple[dict[RunStatus, int], int]:
        counts = {status: 0 for status in RunStatus}
        unknown_count = 0
        for run in runs:
            status = getattr(run, "status", None)
            if isinstance(status, RunStatus):
                counts[status] += 1
            else:
                unknown_count += 1
        return counts, unknown_count

    @staticmethod
    def _rates(successful: int, failed: int) -> tuple[float, float]:
        eligible = successful + failed
        if eligible == 0:
            return 0.0, 0.0
        return successful / eligible, failed / eligible

    @classmethod
    def _duration_metrics(cls, runs: Iterable[Run]) -> DurationMetrics:
        run_snapshot = tuple(runs)
        durations = tuple(
            duration
            for run in run_snapshot
            if (duration := cls._duration_seconds(run)) is not None
        )
        if not durations:
            return DurationMetrics(
                count=0,
                ignored_count=len(run_snapshot),
            )
        return DurationMetrics(
            count=len(durations),
            ignored_count=len(run_snapshot) - len(durations),
            minimum_seconds=min(durations),
            maximum_seconds=max(durations),
            average_seconds=fmean(durations),
            median_seconds=median(durations),
        )

    @staticmethod
    def _duration_seconds(run: Run) -> float | None:
        started_at = getattr(run, "started_at", None)
        finished_at = getattr(run, "finished_at", None)
        if started_at is None or finished_at is None:
            return None
        try:
            seconds = (finished_at - started_at).total_seconds()
        except (AttributeError, TypeError, OverflowError):
            return None
        if seconds < 0 or not math.isfinite(seconds):
            return None
        return seconds
