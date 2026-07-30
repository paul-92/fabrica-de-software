"""Validação de planos e assignments antes da coordenação."""

from asep.agents.coordination.exceptions import CoordinationValidationError
from asep.agents.coordination.models import (
    AgentAssignment,
    CoordinationContext,
    CoordinationPolicy,
)
from asep.agents.registry import AgentRegistry


class CoordinationValidator:
    def validate_context(
        self,
        context: CoordinationContext,
        policy: CoordinationPolicy,
    ) -> None:
        steps = context.execution_plan.steps
        if not steps:
            raise CoordinationValidationError(
                "ExecutionPlan deve possuir passos."
            )
        if len(steps) > policy.max_assignments:
            raise CoordinationValidationError(
                "ExecutionPlan excede max_assignments."
            )
        identifiers = tuple(step.step_id for step in steps)
        if len(identifiers) != len(set(identifiers)):
            raise CoordinationValidationError(
                "ExecutionPlan possui etapas duplicadas."
            )
        known = set(identifiers)
        if any(set(step.dependencies) - known for step in steps):
            raise CoordinationValidationError(
                "ExecutionPlan possui etapas órfãs."
            )

    def validate_assignments(
        self,
        context: CoordinationContext,
        assignments: tuple[AgentAssignment, ...],
        registry: AgentRegistry,
        policy: CoordinationPolicy,
    ) -> None:
        step_ids = {step.step_id for step in context.execution_plan.steps}
        assigned_ids = tuple(item.plan_step_id for item in assignments)
        if len(assigned_ids) != len(set(assigned_ids)):
            raise CoordinationValidationError(
                "Há assignments duplicados."
            )
        if set(assigned_ids) != step_ids:
            raise CoordinationValidationError(
                "Assignments não cobrem todas as etapas do plano."
            )
        agents = {item.agent_id.value for item in assignments}
        if len(agents) > policy.max_agents:
            raise CoordinationValidationError(
                "Coordenação excede max_agents."
            )
        for assignment in assignments:
            if not registry.contains(assignment.agent_id):
                raise CoordinationValidationError(
                    f"Agente inexistente: {assignment.agent_id}."
                )
            capabilities = {
                item.id
                for item in registry.get_metadata(
                    assignment.agent_id
                ).capabilities
            }
            if assignment.required_capability not in capabilities:
                raise CoordinationValidationError(
                    "Capability ausente no agente selecionado."
                )


__all__ = ["CoordinationValidator"]
