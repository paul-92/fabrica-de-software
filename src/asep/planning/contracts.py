"""Portas públicas de planejamento."""

from typing import Protocol, runtime_checkable

from asep.planning.models import (
    PlanningPolicy,
    PlanningRequest,
    PlanningResult,
    PlanStep,
)


@runtime_checkable
class PlanningStrategy(Protocol):
    def build_steps(
        self,
        request: PlanningRequest,
        policy: PlanningPolicy,
    ) -> tuple[PlanStep, ...]: ...


@runtime_checkable
class Planner(Protocol):
    def plan(self, request: PlanningRequest) -> PlanningResult: ...


__all__ = ["Planner", "PlanningStrategy"]

