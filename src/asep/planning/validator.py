"""Validação estrutural e semântica de ExecutionPlan."""

from __future__ import annotations

from collections.abc import Mapping

from asep.planning.exceptions import (
    CircularDependencyError,
    InvalidPlanError,
    PlanningValidationError,
)
from asep.planning.models import (
    ExecutionPlan,
    PlanningPolicy,
    PlanningRequest,
)


class PlanningValidator:
    def validate_request(self, request: PlanningRequest) -> None:
        if not isinstance(request, PlanningRequest):
            raise PlanningValidationError(
                "request deve ser PlanningRequest."
            )
        if not request.goal.strip():
            raise PlanningValidationError("goal não pode ser vazio.")

    def validate_plan(
        self,
        plan: ExecutionPlan,
        request: PlanningRequest,
        policy: PlanningPolicy,
    ) -> int:
        if not plan.steps:
            raise InvalidPlanError("ExecutionPlan deve possuir passos.")
        if len(plan.steps) > policy.max_steps:
            raise InvalidPlanError("ExecutionPlan excede max_steps.")
        identifiers = tuple(step.step_id for step in plan.steps)
        if len(identifiers) != len(set(identifiers)):
            raise InvalidPlanError("ExecutionPlan possui IDs duplicados.")
        known = set(identifiers)
        for step in plan.steps:
            missing = set(step.dependencies) - known
            if missing:
                raise InvalidPlanError(
                    f"Dependências inexistentes em {step.step_id}: "
                    f"{', '.join(sorted(missing))}."
                )
            if (
                step.required_capability
                not in request.context.available_capabilities
            ):
                raise InvalidPlanError(
                    "Capability indisponível: "
                    f"{step.required_capability}."
                )
        depth = self._maximum_depth(plan)
        if depth > policy.max_depth:
            raise InvalidPlanError("ExecutionPlan excede max_depth.")
        if (
            policy.max_estimated_cost is not None
            and plan.estimated_cost > policy.max_estimated_cost
        ):
            raise InvalidPlanError(
                "ExecutionPlan excede max_estimated_cost."
            )
        self._validate_workflow_consistency(plan, request)
        return depth

    @staticmethod
    def _maximum_depth(plan: ExecutionPlan) -> int:
        dependencies = {
            step.step_id: step.dependencies for step in plan.steps
        }
        visiting: set[str] = set()
        depths: dict[str, int] = {}

        def visit(step_id: str) -> int:
            if step_id in visiting:
                raise CircularDependencyError(
                    "ExecutionPlan possui dependência circular."
                )
            if step_id in depths:
                return depths[step_id]
            visiting.add(step_id)
            depth = 1 + max(
                (visit(parent) for parent in dependencies[step_id]),
                default=0,
            )
            visiting.remove(step_id)
            depths[step_id] = depth
            return depth

        return max((visit(step.step_id) for step in plan.steps), default=0)

    @staticmethod
    def _validate_workflow_consistency(
        plan: ExecutionPlan,
        request: PlanningRequest,
    ) -> None:
        raw_steps = request.context.workflow.get("steps")
        if raw_steps is None:
            return
        if not isinstance(raw_steps, (list, tuple)):
            raise InvalidPlanError("workflow.steps possui formato inválido.")
        workflow_ids = tuple(
            str(item.get("id"))
            for item in raw_steps
            if isinstance(item, Mapping)
        )
        plan_ids = tuple(step.step_id for step in plan.steps)
        if workflow_ids != plan_ids:
            raise InvalidPlanError(
                "ExecutionPlan diverge da ordem declarada no workflow."
            )


__all__ = ["PlanningValidator"]

