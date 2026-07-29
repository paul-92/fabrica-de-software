from __future__ import annotations

import inspect
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from asep.application import RunQueryService
from asep.metrics import (
    DurationMetrics,
    MetricsService,
    MetricsSummary,
    ProviderMetrics,
    StatusMetrics,
)
from asep.runs import (
    InMemoryRunRepository,
    Run,
    RunError,
    RunStatus,
)
from asep.timeline import InMemoryTimelineRepository

START = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def make_run(
    run_id: str,
    *,
    status: RunStatus = RunStatus.PENDING,
    seconds: float | None = None,
    provider_name: str | None = None,
    **values,
) -> Run:
    return Run(
        id=run_id,
        status=status,
        started_at=START,
        finished_at=(
            None
            if seconds is None
            else START + timedelta(seconds=seconds)
        ),
        provider_name=provider_name,
        **values,
    )


class QueryStub:
    def __init__(self, runs: tuple[Run, ...]) -> None:
        self.runs = runs
        self.calls = 0

    def list_runs(self) -> tuple[Run, ...]:
        self.calls += 1
        return self.runs


def service_with(*runs: Run) -> MetricsService:
    return MetricsService(QueryStub(tuple(runs)))  # type: ignore[arg-type]


def test_constructs_with_run_query_service() -> None:
    query = RunQueryService(
        InMemoryRunRepository(),
        InMemoryTimelineRepository(),
    )

    service = MetricsService(query)

    assert service.get_summary().total_runs == 0


def test_service_has_no_repository_or_infrastructure_dependency() -> None:
    import asep.metrics.service as module

    source = inspect.getsource(module)
    assert "RunRepository" not in source
    assert "TimelineRepository" not in source
    assert "InMemory" not in source
    assert "asep.cli" not in source
    assert "asep.providers" not in source
    assert "asep.execution_graph" not in source


def test_metrics_do_not_require_timeline_access() -> None:
    class QueryWithoutTimeline(QueryStub):
        def get_timeline(self, run_id: str):
            raise AssertionError("stage metrics were intentionally deferred")

    service = MetricsService(
        QueryWithoutTimeline((make_run("run"),))  # type: ignore[arg-type]
    )

    assert service.get_summary().total_runs == 1
    assert service.metrics_by_provider()[0].total_runs == 1


def test_empty_summary_is_finite_and_explicit() -> None:
    summary = service_with().get_summary()

    assert summary == MetricsSummary(
        total_runs=0,
        successful_runs=0,
        failed_runs=0,
        running_runs=0,
        pending_runs=0,
        cancelled_runs=0,
        unknown_status_runs=0,
        eligible_runs=0,
        success_rate=0,
        failure_rate=0,
        duration=DurationMetrics(count=0, ignored_count=0),
    )
    assert math.isfinite(summary.success_rate)
    assert math.isfinite(summary.failure_rate)


@pytest.mark.parametrize(
    ("status", "field"),
    [
        (RunStatus.SUCCEEDED, "successful_runs"),
        (RunStatus.FAILED, "failed_runs"),
        (RunStatus.RUNNING, "running_runs"),
        (RunStatus.PENDING, "pending_runs"),
        (RunStatus.CANCELLED, "cancelled_runs"),
    ],
)
def test_summary_counts_each_real_status(
    status: RunStatus,
    field: str,
) -> None:
    summary = service_with(make_run("run", status=status)).get_summary()

    assert summary.total_runs == 1
    assert getattr(summary, field) == 1


def test_rates_use_only_succeeded_and_failed_runs() -> None:
    summary = service_with(
        make_run("success-1", status=RunStatus.SUCCEEDED),
        make_run("success-2", status=RunStatus.SUCCEEDED),
        make_run("failed", status=RunStatus.FAILED),
        make_run("running", status=RunStatus.RUNNING),
        make_run("pending", status=RunStatus.PENDING),
        make_run("cancelled", status=RunStatus.CANCELLED),
    ).get_summary()

    assert summary.total_runs == 6
    assert summary.eligible_runs == 3
    assert summary.success_rate == pytest.approx(2 / 3)
    assert summary.failure_rate == pytest.approx(1 / 3)
    assert summary.success_rate + summary.failure_rate == pytest.approx(1)


def test_non_eligible_runs_do_not_cause_division_by_zero() -> None:
    summary = service_with(
        make_run("running", status=RunStatus.RUNNING),
        make_run("cancelled", status=RunStatus.CANCELLED),
    ).get_summary()

    assert summary.eligible_runs == 0
    assert summary.success_rate == 0
    assert summary.failure_rate == 0


def test_count_by_status_includes_zeroes_in_enum_order() -> None:
    metrics = service_with(
        make_run("failed", status=RunStatus.FAILED)
    ).count_by_status()

    assert tuple(item.status for item in metrics) == tuple(RunStatus)
    assert tuple(item.count for item in metrics) == (0, 0, 0, 1, 0)


def test_duration_for_finished_run_uses_seconds() -> None:
    duration = service_with(
        make_run("run", seconds=2.5)
    ).get_duration_metrics()

    assert duration.count == 1
    assert duration.ignored_count == 0
    assert duration.minimum_seconds == 2.5
    assert duration.maximum_seconds == 2.5
    assert duration.average_seconds == 2.5
    assert duration.median_seconds == 2.5


def test_duration_statistics_preserve_precision() -> None:
    duration = service_with(
        make_run("one", seconds=0.1),
        make_run("two", seconds=0.2),
        make_run("three", seconds=0.6),
    ).get_duration_metrics()

    assert duration.count == 3
    assert duration.minimum_seconds == pytest.approx(0.1)
    assert duration.maximum_seconds == pytest.approx(0.6)
    assert duration.average_seconds == pytest.approx(0.3)
    assert duration.median_seconds == pytest.approx(0.2)


def test_active_run_is_ignored_for_duration_without_using_clock() -> None:
    duration = service_with(
        make_run("active", status=RunStatus.RUNNING)
    ).get_duration_metrics()

    assert duration == DurationMetrics(count=0, ignored_count=1)


@dataclass(frozen=True)
class LegacyRun:
    id: str
    status: object
    started_at: object = None
    finished_at: object = None
    provider_name: str | None = None


@pytest.mark.parametrize(
    "legacy",
    [
        LegacyRun(
            id="missing-start",
            status=RunStatus.SUCCEEDED,
            finished_at=START,
        ),
        LegacyRun(
            id="missing-finish",
            status=RunStatus.SUCCEEDED,
            started_at=START,
        ),
        LegacyRun(
            id="inverted",
            status=RunStatus.SUCCEEDED,
            started_at=START,
            finished_at=START - timedelta(seconds=1),
        ),
        LegacyRun(
            id="incompatible",
            status=RunStatus.SUCCEEDED,
            started_at="not-a-date",
            finished_at=START,
        ),
    ],
)
def test_invalid_legacy_duration_is_counted_as_ignored(
    legacy: LegacyRun,
) -> None:
    service = MetricsService(
        QueryStub((legacy,))  # type: ignore[arg-type]
    )

    duration = service.get_duration_metrics()

    assert duration == DurationMetrics(count=0, ignored_count=1)


def test_invalid_status_is_visible_in_summary() -> None:
    legacy = LegacyRun(
        id="legacy",
        status="obsolete",
        started_at=START,
        finished_at=START + timedelta(seconds=1),
    )
    service = MetricsService(
        QueryStub((legacy,))  # type: ignore[arg-type]
    )

    summary = service.get_summary()

    assert summary.total_runs == 1
    assert summary.unknown_status_runs == 1
    assert summary.eligible_runs == 0


def test_provider_metrics_for_single_provider() -> None:
    metrics = service_with(
        make_run(
            "success",
            status=RunStatus.SUCCEEDED,
            seconds=2,
            provider_name="codex",
        ),
        make_run(
            "failed",
            status=RunStatus.FAILED,
            seconds=4,
            provider_name="codex",
        ),
    ).metrics_by_provider()

    assert metrics == (
        ProviderMetrics(
            provider_name="codex",
            total_runs=2,
            successful_runs=1,
            failed_runs=1,
            running_runs=0,
            unknown_status_runs=0,
            eligible_runs=2,
            success_rate=0.5,
            failure_rate=0.5,
            duration=DurationMetrics(
                count=2,
                ignored_count=0,
                minimum_seconds=2,
                maximum_seconds=4,
                average_seconds=3,
                median_seconds=3,
            ),
        ),
    )


def test_providers_are_sorted_and_missing_provider_is_explicit() -> None:
    metrics = service_with(
        make_run("z", provider_name="zeta"),
        make_run("none"),
        make_run("a", provider_name="Alpha"),
    ).metrics_by_provider()

    assert tuple(item.provider_name for item in metrics) == (
        None,
        "Alpha",
        "zeta",
    )
    assert all(item.total_runs == 1 for item in metrics)


def test_provider_rates_exclude_running_and_cancelled() -> None:
    metric = service_with(
        make_run(
            "success",
            status=RunStatus.SUCCEEDED,
            provider_name="provider",
        ),
        make_run(
            "running",
            status=RunStatus.RUNNING,
            provider_name="provider",
        ),
        make_run(
            "cancelled",
            status=RunStatus.CANCELLED,
            provider_name="provider",
        ),
    ).metrics_by_provider()[0]

    assert metric.total_runs == 3
    assert metric.eligible_runs == 1
    assert metric.success_rate == 1
    assert metric.failure_rate == 0


def test_provider_without_eligible_runs_has_zero_rates() -> None:
    metric = service_with(
        make_run(
            "running",
            status=RunStatus.RUNNING,
            provider_name="provider",
        )
    ).metrics_by_provider()[0]

    assert metric.success_rate == 0
    assert metric.failure_rate == 0


def test_empty_provider_metrics_are_empty() -> None:
    assert service_with().metrics_by_provider() == ()


def test_summary_uses_one_consistent_snapshot() -> None:
    query = QueryStub((make_run("one"),))
    service = MetricsService(query)  # type: ignore[arg-type]

    summary = service.get_summary()

    assert summary.total_runs == 1
    assert query.calls == 1


def test_each_public_calculation_is_on_demand_without_cache() -> None:
    query = QueryStub((make_run("one"),))
    service = MetricsService(query)  # type: ignore[arg-type]

    service.get_summary()
    service.count_by_status()
    service.get_duration_metrics()
    service.metrics_by_provider()

    assert query.calls == 4


def test_metrics_do_not_modify_runs_or_metadata() -> None:
    source = make_run(
        "run",
        status=RunStatus.FAILED,
        seconds=1,
        metadata={"nested": {"value": 1}},
        error=RunError(type="Failure", message="Failed."),
    )
    before = source.model_dump(mode="json")
    service = service_with(source)

    service.get_summary()
    service.count_by_status()
    service.get_duration_metrics()
    service.metrics_by_provider()

    assert source.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "result",
    [
        DurationMetrics(count=0, ignored_count=0),
        StatusMetrics(status=RunStatus.PENDING, count=0),
        service_with().get_summary(),
    ],
)
def test_results_are_frozen(result) -> None:
    with pytest.raises(ValidationError):
        result.count = 9  # type: ignore[attr-defined]


def test_models_serialize_to_stable_json_primitives() -> None:
    summary = service_with(
        make_run(
            "run",
            status=RunStatus.SUCCEEDED,
            seconds=1.25,
        )
    ).get_summary()

    dumped = summary.model_dump(mode="json")
    encoded = json.dumps(
        dumped,
        allow_nan=False,
        sort_keys=True,
    )

    assert json.loads(encoded) == dumped
    assert dumped["success_rate"] == 1
    assert dumped["duration"]["average_seconds"] == 1.25


def test_duration_contract_rejects_inconsistent_statistics() -> None:
    with pytest.raises(ValidationError):
        DurationMetrics(
            count=0,
            ignored_count=0,
            average_seconds=1,
        )
    with pytest.raises(ValidationError):
        DurationMetrics(
            count=1,
            ignored_count=0,
            minimum_seconds=None,
            maximum_seconds=1,
            average_seconds=1,
            median_seconds=1,
        )


def test_aggregate_contracts_reject_inconsistent_counts_and_rates() -> None:
    duration = DurationMetrics(count=0, ignored_count=0)
    with pytest.raises(ValidationError, match="total_runs"):
        MetricsSummary(
            total_runs=2,
            successful_runs=1,
            failed_runs=0,
            running_runs=0,
            pending_runs=0,
            cancelled_runs=0,
            unknown_status_runs=0,
            eligible_runs=1,
            success_rate=1,
            failure_rate=0,
            duration=duration,
        )
    with pytest.raises(ValidationError, match="taxas"):
        ProviderMetrics(
            provider_name="provider",
            total_runs=1,
            successful_runs=1,
            failed_runs=0,
            running_runs=0,
            unknown_status_runs=0,
            eligible_runs=1,
            success_rate=0,
            failure_rate=1,
            duration=duration,
        )


def test_public_exports_are_intentional() -> None:
    import asep.metrics as metrics

    assert set(metrics.__all__) == {
        "DurationMetrics",
        "MetricsService",
        "MetricsSummary",
        "ProviderMetrics",
        "StatusMetrics",
    }
