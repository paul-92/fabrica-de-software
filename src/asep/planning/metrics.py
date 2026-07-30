"""Métricas locais e injetáveis do Planning Engine."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PlanningMetricsSnapshot:
    plans_created_total: int
    planning_duration: tuple[float, ...]
    planning_failures: int
    average_plan_steps: float


@runtime_checkable
class PlanningMetricsRecorder(Protocol):
    def completed(self, *, steps: int, duration_seconds: float) -> None: ...
    def failed(self, *, duration_seconds: float) -> None: ...


class InMemoryPlanningMetrics:
    def __init__(self) -> None:
        self._created = 0
        self._failures = 0
        self._durations: list[float] = []
        self._steps = 0

    def completed(self, *, steps: int, duration_seconds: float) -> None:
        self._created += 1
        self._steps += steps
        self._durations.append(duration_seconds)

    def failed(self, *, duration_seconds: float) -> None:
        self._failures += 1
        self._durations.append(duration_seconds)

    def snapshot(self) -> PlanningMetricsSnapshot:
        return PlanningMetricsSnapshot(
            plans_created_total=self._created,
            planning_duration=tuple(self._durations),
            planning_failures=self._failures,
            average_plan_steps=(
                self._steps / self._created if self._created else 0.0
            ),
        )


__all__ = [
    "InMemoryPlanningMetrics",
    "PlanningMetricsRecorder",
    "PlanningMetricsSnapshot",
]

