"""Métricas injetáveis da coordenação."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CoordinationMetricsSnapshot:
    coordinated_plans_total: int
    agent_assignments_total: int
    coordination_duration: tuple[float, ...]
    coordination_failures: int
    result_aggregation_duration: tuple[float, ...]


@runtime_checkable
class CoordinationMetricsRecorder(Protocol):
    def completed(
        self,
        *,
        assignments: int,
        duration_seconds: float,
        aggregation_duration_seconds: float,
    ) -> None: ...

    def failed(self, *, duration_seconds: float) -> None: ...


class InMemoryCoordinationMetrics:
    def __init__(self) -> None:
        self._plans = 0
        self._assignments = 0
        self._durations: list[float] = []
        self._failures = 0
        self._aggregation_durations: list[float] = []

    def completed(
        self,
        *,
        assignments: int,
        duration_seconds: float,
        aggregation_duration_seconds: float,
    ) -> None:
        self._plans += 1
        self._assignments += assignments
        self._durations.append(duration_seconds)
        self._aggregation_durations.append(aggregation_duration_seconds)

    def failed(self, *, duration_seconds: float) -> None:
        self._failures += 1
        self._durations.append(duration_seconds)

    def snapshot(self) -> CoordinationMetricsSnapshot:
        return CoordinationMetricsSnapshot(
            coordinated_plans_total=self._plans,
            agent_assignments_total=self._assignments,
            coordination_duration=tuple(self._durations),
            coordination_failures=self._failures,
            result_aggregation_duration=tuple(
                self._aggregation_durations
            ),
        )


__all__ = [
    "CoordinationMetricsRecorder",
    "CoordinationMetricsSnapshot",
    "InMemoryCoordinationMetrics",
]
