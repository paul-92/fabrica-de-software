"""Validação explícita da composição E2E."""

from dataclasses import dataclass

from asep.agents.coordination.contracts import Coordinator
from asep.memory.contracts import AgentMemory
from asep.pipeline.exceptions import (
    PipelineComponentUnavailableError,
    PipelineValidationError,
)
from asep.pipeline.models import GoalRequest
from asep.planning.contracts import Planner
from asep.timeline.repository import TimelineRepository
from asep.tools.registry import ToolRegistry
from asep.workflow.orchestrator import WorkflowOrchestrator


@dataclass(frozen=True, slots=True)
class PipelineComponents:
    workflow: WorkflowOrchestrator
    planner: Planner
    coordinator: Coordinator
    tools: ToolRegistry
    memory: AgentMemory
    timeline: TimelineRepository
    metrics: object


class PipelineValidator:
    def validate_components(
        self, components: PipelineComponents
    ) -> None:
        checks = {
            "Workflow": components.workflow,
            "Planning": components.planner,
            "Coordinator": components.coordinator,
            "Tools": components.tools,
            "Memory": components.memory,
            "Timeline": components.timeline,
            "Metrics": components.metrics,
        }
        missing = [
            name for name, component in checks.items() if component is None
        ]
        if missing:
            raise PipelineComponentUnavailableError(
                f"Componentes indisponíveis: {', '.join(missing)}."
            )
        if not components.tools.list():
            raise PipelineComponentUnavailableError(
                "Nenhuma Tool está registrada."
            )

    def validate_request(self, request: GoalRequest) -> None:
        if not isinstance(request, GoalRequest):
            raise PipelineValidationError(
                "request deve ser GoalRequest."
            )
        workspace = request.workspace.resolve()
        if not workspace.is_dir():
            raise PipelineValidationError(
                f"Workspace inexistente: {workspace}."
            )


__all__ = ["PipelineComponents", "PipelineValidator"]
