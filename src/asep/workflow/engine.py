"""Fachada do Workflow Engine genérico."""

from __future__ import annotations

from typing import TYPE_CHECKING

from asep.workflow.models import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
)
from asep.workflow.executor import WorkflowExecutor
from asep.workflow.validator import WorkflowValidator
from asep.planning.contracts import Planner
from asep.planning.models import PlanningContext, PlanningRequest

if TYPE_CHECKING:
    from asep.agents.coordination.contracts import Coordinator


class WorkflowEngine:
    def __init__(
        self,
        validator: WorkflowValidator,
        executor: WorkflowExecutor,
        planner: Planner | None = None,
        coordinator: Coordinator | None = None,
    ) -> None:
        self._validator = validator
        self._executor = executor
        self._planner = planner
        self._coordinator = coordinator

    def execute(
        self,
        workflow: WorkflowDefinition | None,
        context: WorkflowContext,
    ) -> WorkflowExecutionResult:
        validated = self._validator.validate(workflow)
        if self._planner is not None:
            objective = (
                validated.description
                or validated.name
                or validated.id
            )
            planning_result = self._planner.plan(
                PlanningRequest(
                    goal=objective,
                    context=PlanningContext(
                        objective=objective,
                        workflow={
                            "id": validated.id,
                            "steps": [
                                {
                                    "id": step.id,
                                    "description": (
                                        f"Executar workflow step {step.id}"
                                    ),
                                    "required_capability": "workflow_step",
                                }
                                for step in validated.steps
                            ],
                        },
                        available_capabilities=("workflow_step",),
                    ),
                    workflow_execution_id=context.run_id,
                )
            )
            context.values["execution_plan"] = (
                planning_result.plan.model_dump(mode="json")
            )
            if self._coordinator is not None:
                from asep.agents.coordination.models import (
                    CoordinationContext,
                )

                coordination_result = self._coordinator.coordinate(
                    CoordinationContext(
                        execution_plan=planning_result.plan,
                        workflow={
                            "id": validated.id,
                            "name": validated.name,
                        },
                        metadata={"run_id": context.run_id},
                    )
                )
                context.values["coordination_result"] = (
                    coordination_result.model_dump(mode="json")
                )
        return self._executor.execute(validated, context)
