"""Fila lógica sequencial e dependency-aware."""

from asep.agents.coordination.exceptions import AgentAssignmentError
from asep.agents.coordination.models import AgentAssignment, CoordinationPolicy
from asep.planning.models import ExecutionPlan


class AgentExecutionQueue:
    def order(
        self,
        plan: ExecutionPlan,
        assignments: tuple[AgentAssignment, ...],
        policy: CoordinationPolicy,
    ) -> tuple[AgentAssignment, ...]:
        by_step = {item.plan_step_id: item for item in assignments}
        if policy.order == "plan":
            return tuple(by_step[step.step_id] for step in plan.steps)

        remaining = {step.step_id: step for step in plan.steps}
        completed: set[str] = set()
        ordered: list[AgentAssignment] = []
        while remaining:
            ready = [
                step
                for step in remaining.values()
                if set(step.dependencies) <= completed
            ]
            if not ready:
                raise AgentAssignmentError(
                    "Fila não pode ordenar dependências do plano."
                )
            selected = sorted(
                ready,
                key=lambda step: (
                    by_step[step.step_id].priority,
                    step.step_id,
                ),
            )[0]
            ordered.append(by_step[selected.step_id])
            completed.add(selected.step_id)
            del remaining[selected.step_id]
        return tuple(ordered)


__all__ = ["AgentExecutionQueue"]
