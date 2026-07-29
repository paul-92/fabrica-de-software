"""Schemas públicos da camada HTTP v1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from asep.metrics import (
    DurationMetrics,
    MetricsSummary,
    ProviderMetrics,
    StatusMetrics,
)
from asep.runs import Run, RunStatus
from asep.timeline import TimelineEvent, TimelineEventType


class HttpSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(HttpSchema):
    status: str
    api_version: str


class RunErrorResponse(HttpSchema):
    type: str
    message: str
    details: dict[str, Any]


class RunResponse(HttpSchema):
    id: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    project_id: str | None
    workflow_id: str | None
    stage_id: str | None
    provider_name: str | None
    summary: str | None
    error: RunErrorResponse | None
    metadata: dict[str, Any]

    @classmethod
    def from_domain(cls, run: Run) -> RunResponse:
        return cls.model_validate(run.model_dump(mode="json"))


class RunListResponse(HttpSchema):
    items: tuple[RunResponse, ...]


class TimelineEventResponse(HttpSchema):
    id: str
    run_id: str
    timestamp: datetime
    type: TimelineEventType
    stage_id: str | None
    message: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_domain(
        cls, event: TimelineEvent
    ) -> TimelineEventResponse:
        return cls.model_validate(event.model_dump(mode="json"))


class TimelineResponse(HttpSchema):
    items: tuple[TimelineEventResponse, ...]


class DurationMetricsResponse(HttpSchema):
    count: int
    ignored_count: int
    minimum_seconds: float | None
    maximum_seconds: float | None
    average_seconds: float | None
    median_seconds: float | None

    @classmethod
    def from_domain(
        cls, metrics: DurationMetrics
    ) -> DurationMetricsResponse:
        return cls.model_validate(metrics.model_dump(mode="json"))


class MetricsSummaryResponse(HttpSchema):
    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int
    pending_runs: int
    cancelled_runs: int
    unknown_status_runs: int
    eligible_runs: int
    success_rate: float
    failure_rate: float
    duration: DurationMetricsResponse

    @classmethod
    def from_domain(
        cls, metrics: MetricsSummary
    ) -> MetricsSummaryResponse:
        return cls.model_validate(metrics.model_dump(mode="json"))


class StatusMetricResponse(HttpSchema):
    status: RunStatus
    count: int

    @classmethod
    def from_domain(
        cls, metrics: StatusMetrics
    ) -> StatusMetricResponse:
        return cls.model_validate(metrics.model_dump(mode="json"))


class StatusMetricsResponse(HttpSchema):
    items: tuple[StatusMetricResponse, ...]


class ProviderMetricResponse(HttpSchema):
    provider_name: str | None
    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int
    unknown_status_runs: int
    eligible_runs: int
    success_rate: float
    failure_rate: float
    duration: DurationMetricsResponse

    @classmethod
    def from_domain(
        cls, metrics: ProviderMetrics
    ) -> ProviderMetricResponse:
        return cls.model_validate(metrics.model_dump(mode="json"))


class ProviderMetricsResponse(HttpSchema):
    items: tuple[ProviderMetricResponse, ...]


class ErrorDetail(HttpSchema):
    code: str
    message: str


class ErrorResponse(HttpSchema):
    error: ErrorDetail
