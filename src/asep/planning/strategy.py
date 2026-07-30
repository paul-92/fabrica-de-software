"""Estratégia sequencial baseada apenas em regras declaradas."""

from __future__ import annotations

from collections.abc import Mapping

from asep.agents.contracts import AgentId
from asep.planning.exceptions import PlanningStrategyError
from asep.planning.models import PlanningPolicy, PlanningRequest, PlanStep
from asep.tools.models import ToolId


class SequentialPlanningStrategy:
    def build_steps(
        self,
        request: PlanningRequest,
        policy: PlanningPolicy,
    ) -> tuple[PlanStep, ...]:
        raw_steps = request.context.workflow.get("steps", ())
        if not isinstance(raw_steps, (list, tuple)):
            raise PlanningStrategyError(
                "workflow.steps deve ser uma lista serializável."
            )
        cost_rules = policy.rules.get("capability_cost", {})
        duration_rules = policy.rules.get("capability_duration", {})
        if not isinstance(cost_rules, Mapping):
            cost_rules = {}
        if not isinstance(duration_rules, Mapping):
            duration_rules = {}
        steps: list[PlanStep] = []
        previous: str | None = None
        for index, raw in enumerate(raw_steps):
            if not isinstance(raw, Mapping):
                raise PlanningStrategyError(
                    "cada workflow step deve ser um objeto."
                )
            step_id = str(raw.get("id", f"step-{index + 1}"))
            capability = str(
                raw.get("required_capability", "workflow_step")
            )
            declared_dependencies = raw.get("dependencies")
            if declared_dependencies is None:
                dependencies = (previous,) if previous is not None else ()
            elif isinstance(declared_dependencies, (list, tuple)):
                dependencies = tuple(str(item) for item in declared_dependencies)
            else:
                raise PlanningStrategyError(
                    "dependencies deve ser uma lista."
                )
            tool_value = raw.get("tool") or request.context.available_tools.get(
                capability
            )
            agent_value = raw.get("agent")
            step = PlanStep(
                step_id=step_id,
                description=str(raw.get("description", step_id)),
                required_capability=capability,
                tool_id=(
                    ToolId(value=str(tool_value))
                    if tool_value is not None
                    else None
                ),
                agent_id=(
                    AgentId(value=str(agent_value))
                    if agent_value is not None
                    else request.agent_id
                ),
                dependencies=dependencies,
                priority=policy.priorities.get(step_id, index),
                estimated_cost=float(cost_rules.get(capability, 1.0)),
                estimated_duration_seconds=float(
                    duration_rules.get(capability, 60.0)
                ),
                metadata={"source_index": index},
            )
            steps.append(step)
            previous = step_id
        return tuple(steps)


__all__ = ["SequentialPlanningStrategy"]

