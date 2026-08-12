"""Project-scoped ownership of a bounded engineering task."""

from __future__ import annotations

from typing import Protocol

from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application.project_ai_runtime import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionResult,
)
from asep.projects import (
    ProjectExecution,
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
)


class DeterministicProjectOperationalPlanBuilder:
    """Describes only operations that the 23.7B workflow actually performs."""

    def build(self, execution: ProjectExecution) -> ProjectOperationalPlan:
        return ProjectOperationalPlan(
            execution_id=execution.execution_id,
            created_at=execution.created_at,
            steps=(
                ProjectOperationalPlanStep(
                    step_id="analyze-context",
                    operation=ProjectOperationalPlanOperation.ANALYZE_CONTEXT,
                    description=(
                        "Use the bounded project-session context and memory "
                        "prepared for this task."
                    ),
                ),
                ProjectOperationalPlanStep(
                    step_id="execute-workspace-task",
                    operation=(
                        ProjectOperationalPlanOperation.EXECUTE_WORKSPACE_TASK
                    ),
                    description=(
                        "Send the current instruction to the selected AI "
                        "runtime with workspace writes enabled."
                    ),
                ),
                ProjectOperationalPlanStep(
                    step_id="capture-workspace-changes",
                    operation=(
                        ProjectOperationalPlanOperation.CAPTURE_WORKSPACE_CHANGES
                    ),
                    description=(
                        "Capture deterministic workspace change evidence "
                        "for this execution."
                    ),
                ),
            ),
        )


class ProjectRuntimeExecutionCapability(Protocol):
    def execute(
        self,
        request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult: ...


class ProjectEngineeringExecutionService:
    """Application boundary for one real, project-scoped engineering task."""

    def __init__(self, runtime_execution: ProjectRuntimeExecutionCapability) -> None:
        self._runtime_execution = runtime_execution

    def execute(
        self,
        request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult:
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError(
                "project engineering execution requires workspace_write mode"
            )
        return self._runtime_execution.execute(request)


__all__ = [
    "DeterministicProjectOperationalPlanBuilder",
    "ProjectEngineeringExecutionService",
    "ProjectRuntimeExecutionCapability",
]
