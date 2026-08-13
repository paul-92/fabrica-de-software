"""Routers finos da Dashboard API."""

from __future__ import annotations

from collections.abc import Callable
from fastapi import APIRouter, Query, Response

from asep.application import RunQueryService
from asep.api.schemas import (
    ErrorResponse,
    HealthResponse,
    MetricsSummaryResponse,
    ProviderMetricResponse,
    ProviderMetricsResponse,
    RunListResponse,
    RunResponse,
    StatusMetricResponse,
    StatusMetricsResponse,
    TimelineEventResponse,
    TimelineResponse,
)
from asep.metrics import MetricsService
from asep.runs import RunStatus

API_PREFIX = "/api/v1"


def create_health_router(readiness: Callable[[], bool] | None = None) -> APIRouter:
    router = APIRouter(prefix=API_PREFIX, tags=["health"])

    @router.get(
        "/health",
        response_model=HealthResponse,
        summary="Check API health",
    )
    def health() -> HealthResponse:
        return HealthResponse(status="ok", api_version="v1")

    @router.get("/ready", summary="Check API readiness")
    def ready(response: Response) -> dict[str, str]:
        healthy = readiness is None or readiness()
        if not healthy:
            response.status_code = 503
        return {"status": "ready" if healthy else "unavailable"}

    return router


def create_runs_router(
    run_query_service: RunQueryService,
) -> APIRouter:
    router = APIRouter(prefix=f"{API_PREFIX}/runs", tags=["runs"])

    @router.get(
        "",
        response_model=RunListResponse,
        responses={422: {"model": ErrorResponse}},
        summary="List runs",
    )
    def list_runs(
        status: RunStatus | None = Query(
            default=None,
            description="Filter by an exact RunStatus value.",
        ),
    ) -> RunListResponse:
        runs = (
            run_query_service.list_runs()
            if status is None
            else run_query_service.list_runs_by_status(status)
        )
        return RunListResponse(
            items=tuple(RunResponse.from_domain(run) for run in runs)
        )

    @router.get(
        "/{run_id}/timeline",
        response_model=TimelineResponse,
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Get run timeline",
    )
    def get_timeline(run_id: str) -> TimelineResponse:
        events = run_query_service.get_timeline(run_id)
        return TimelineResponse(
            items=tuple(
                TimelineEventResponse.from_domain(event)
                for event in events
            )
        )

    @router.get(
        "/{run_id}",
        response_model=RunResponse,
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        summary="Get run details",
    )
    def get_run(run_id: str) -> RunResponse:
        return RunResponse.from_domain(
            run_query_service.get_run(run_id)
        )

    return router


def create_metrics_router(
    metrics_service: MetricsService,
) -> APIRouter:
    router = APIRouter(prefix=f"{API_PREFIX}/metrics", tags=["metrics"])

    @router.get(
        "/summary",
        response_model=MetricsSummaryResponse,
        responses={500: {"model": ErrorResponse}},
        summary="Get execution metrics summary",
    )
    def get_summary() -> MetricsSummaryResponse:
        return MetricsSummaryResponse.from_domain(
            metrics_service.get_summary()
        )

    @router.get(
        "/status",
        response_model=StatusMetricsResponse,
        responses={500: {"model": ErrorResponse}},
        summary="Get metrics by status",
    )
    def get_status_metrics() -> StatusMetricsResponse:
        return StatusMetricsResponse(
            items=tuple(
                StatusMetricResponse.from_domain(metric)
                for metric in metrics_service.count_by_status()
            )
        )

    @router.get(
        "/providers",
        response_model=ProviderMetricsResponse,
        responses={500: {"model": ErrorResponse}},
        summary="Get metrics by provider",
    )
    def get_provider_metrics() -> ProviderMetricsResponse:
        return ProviderMetricsResponse(
            items=tuple(
                ProviderMetricResponse.from_domain(metric)
                for metric in metrics_service.metrics_by_provider()
            )
        )

    return router
