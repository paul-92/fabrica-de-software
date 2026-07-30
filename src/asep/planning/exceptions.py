"""Exceções tipadas do Planning Engine."""


class PlanningError(Exception):
    pass


class PlanningValidationError(PlanningError):
    pass


class CircularDependencyError(PlanningValidationError):
    pass


class InvalidPlanError(PlanningValidationError):
    pass


class PlanningStrategyError(PlanningError):
    pass


__all__ = [
    "CircularDependencyError",
    "InvalidPlanError",
    "PlanningError",
    "PlanningStrategyError",
    "PlanningValidationError",
]

