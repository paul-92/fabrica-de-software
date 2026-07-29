"""Contratos imutáveis e serializáveis das métricas de execução."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from asep.runs import RunStatus


class DurationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    count: int = Field(ge=0)
    ignored_count: int = Field(ge=0)
    minimum_seconds: float | None = Field(default=None, ge=0)
    maximum_seconds: float | None = Field(default=None, ge=0)
    average_seconds: float | None = Field(default=None, ge=0)
    median_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def statistics_match_count(self) -> DurationMetrics:
        statistics = (
            self.minimum_seconds,
            self.maximum_seconds,
            self.average_seconds,
            self.median_seconds,
        )
        if self.count == 0 and any(value is not None for value in statistics):
            raise ValueError("estatísticas devem ser nulas quando count é zero")
        if self.count > 0 and any(value is None for value in statistics):
            raise ValueError(
                "estatísticas devem existir quando count é positivo"
            )
        if (
            self.minimum_seconds is not None
            and self.maximum_seconds is not None
            and self.minimum_seconds > self.maximum_seconds
        ):
            raise ValueError("duração mínima não pode superar a máxima")
        return self


class StatusMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: RunStatus
    count: int = Field(ge=0)


class MetricsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_runs: int = Field(ge=0)
    successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    running_runs: int = Field(ge=0)
    pending_runs: int = Field(ge=0)
    cancelled_runs: int = Field(ge=0)
    unknown_status_runs: int = Field(ge=0)
    eligible_runs: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    failure_rate: float = Field(ge=0, le=1)
    duration: DurationMetrics

    @model_validator(mode="after")
    def aggregate_is_consistent(self) -> MetricsSummary:
        known_total = (
            self.successful_runs
            + self.failed_runs
            + self.running_runs
            + self.pending_runs
            + self.cancelled_runs
        )
        if self.total_runs != known_total + self.unknown_status_runs:
            raise ValueError("total_runs não corresponde às contagens")
        _validate_rates(
            self.successful_runs,
            self.failed_runs,
            self.eligible_runs,
            self.success_rate,
            self.failure_rate,
        )
        return self


class ProviderMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: str | None
    total_runs: int = Field(ge=0)
    successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    running_runs: int = Field(ge=0)
    unknown_status_runs: int = Field(ge=0)
    eligible_runs: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    failure_rate: float = Field(ge=0, le=1)
    duration: DurationMetrics

    @model_validator(mode="after")
    def aggregate_is_consistent(self) -> ProviderMetrics:
        minimum_total = (
            self.successful_runs
            + self.failed_runs
            + self.running_runs
            + self.unknown_status_runs
        )
        if self.total_runs < minimum_total:
            raise ValueError("total_runs é menor que as contagens conhecidas")
        _validate_rates(
            self.successful_runs,
            self.failed_runs,
            self.eligible_runs,
            self.success_rate,
            self.failure_rate,
        )
        return self


def _validate_rates(
    successful: int,
    failed: int,
    eligible: int,
    success_rate: float,
    failure_rate: float,
) -> None:
    if eligible != successful + failed:
        raise ValueError("eligible_runs deve ser sucesso mais falha")
    expected_success = successful / eligible if eligible else 0.0
    expected_failure = failed / eligible if eligible else 0.0
    if not (
        math.isclose(success_rate, expected_success)
        and math.isclose(failure_rate, expected_failure)
    ):
        raise ValueError("taxas não correspondem às contagens elegíveis")
