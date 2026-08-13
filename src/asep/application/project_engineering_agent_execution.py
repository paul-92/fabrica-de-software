"""Controlled DeveloperAgent execution for bounded engineering plan steps."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Mapping, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import JsonValue

from asep.agents import AgentCapability, AgentId
from asep.agents.runtime_models import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.application.project_engineering_planning import BoundedProjectAnalysis
from asep.projects import (
    ProjectExecution,
    ProjectEngineeringStepResult,
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
)


class EngineeringFileChangeOperation(StrEnum):
    CREATE_OR_REPLACE = "create_or_replace"


class EngineeringFileChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    content: str
    operation: EngineeringFileChangeOperation = (
        EngineeringFileChangeOperation.CREATE_OR_REPLACE
    )

    @field_validator("relative_path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or ".." in path.parts
            or (path.parts and ":" in path.parts[0])
        ):
            raise ValueError("engineering change path must be safe and relative")
        return normalized


class ProjectEngineeringStepExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    step_id: str
    capability: str
    tool_id: str
    options: Mapping[str, JsonValue] = Field(default_factory=dict)


class EngineeringImplementationProvider(Protocol):
    def supports(self, step: ProjectOperationalPlanStep) -> bool: ...

    def changes_for(
        self,
        context: EngineeringImplementationContext,
    ) -> tuple[EngineeringFileChange, ...]: ...


class EngineeringImplementationContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    task: str
    analysis: BoundedProjectAnalysis
    plan: ProjectOperationalPlan
    step: ProjectOperationalPlanStep
    dependency_results: tuple[ProjectEngineeringStepResult, ...] = ()


class AgentExecutionCapability(Protocol):
    def execute(self, request: AgentExecutionRequest) -> AgentExecutionResult: ...


class ProjectEngineeringAgentExecutor:
    """Executes a whole supported implementation plan or declines it."""

    def __init__(
        self,
        agents: AgentExecutionCapability,
        provider: EngineeringImplementationProvider,
    ) -> None:
        self._agents = agents
        self._provider = provider

    def execute_supported_plan(
        self,
        execution: ProjectExecution,
        plan: ProjectOperationalPlan,
        workspace: Path,
        analysis: BoundedProjectAnalysis,
    ) -> tuple[ProjectEngineeringStepResult, ...] | None:
        implement_steps = tuple(
            step for step in plan.steps
            if step.operation is ProjectOperationalPlanOperation.IMPLEMENT
        )
        if not implement_steps or any(
            not self._provider.supports(step) for step in implement_steps
        ):
            return None
        results: list[ProjectEngineeringStepResult] = []
        completed_steps: set[str] = set()
        for step in self._dependency_order(plan):
            if not set(step.dependencies) <= completed_steps:
                raise RuntimeError("engineering step dependency was not completed")
            if step.operation is not ProjectOperationalPlanOperation.IMPLEMENT:
                completed_steps.add(step.step_id)
                continue
            dependency_results = tuple(
                item for item in results if item.step_id in step.dependencies
            )
            changes = self._provider.changes_for(EngineeringImplementationContext(
                execution_id=execution.execution_id,
                task=execution.instruction,
                analysis=analysis,
                plan=plan,
                step=step,
                dependency_results=dependency_results,
            ))
            if not changes:
                raise RuntimeError("implementation provider returned no changes")
            for index, change in enumerate(changes, start=1):
                request = AgentExecutionRequest(
                    execution_id=f"{execution.execution_id}:{step.step_id}:{index}",
                    agent_id=AgentId(value="developer"),
                    capability=AgentCapability(id="write_file"),
                    input={"plan_step": {
                        "step_id": step.step_id,
                        "required_capability": "write_file",
                        "tool_id": "write-file",
                        "metadata": {
                            "write_path": change.relative_path,
                            "content": change.content,
                            "overwrite": True,
                        },
                    }},
                    context={
                        "project_id": execution.project_id,
                        "objective": step.description,
                    },
                    metadata={
                        "workspace": str(workspace),
                        "options": {},
                    },
                    workflow_execution_id=execution.execution_id,
                    workflow_step_id=step.step_id,
                )
                result = self._agents.execute(request)
                succeeded = result.status is AgentExecutionStatus.SUCCEEDED
                bounded_output = str(result.output)[:4_000]
                results.append(ProjectEngineeringStepResult(
                    execution_id=execution.execution_id,
                    step_id=step.step_id,
                    tool_id="write-file",
                    succeeded=succeeded,
                    output=bounded_output,
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                ))
                if not succeeded:
                    return tuple(results)
            completed_steps.add(step.step_id)
        return tuple(results)

    @staticmethod
    def _dependency_order(
        plan: ProjectOperationalPlan,
    ) -> tuple[ProjectOperationalPlanStep, ...]:
        indexed = {step.step_id: (index, step) for index, step in enumerate(plan.steps)}
        remaining = set(indexed)
        completed: set[str] = set()
        ordered: list[ProjectOperationalPlanStep] = []
        while remaining:
            ready = sorted(
                (
                    indexed[step_id]
                    for step_id in remaining
                    if set(indexed[step_id][1].dependencies) <= completed
                ),
                key=lambda item: (item[0], item[1].step_id),
            )
            if not ready:
                raise RuntimeError("engineering plan dependency order is invalid")
            for _, step in ready:
                ordered.append(step)
                completed.add(step.step_id)
                remaining.remove(step.step_id)
        return tuple(ordered)


__all__ = [
    "EngineeringFileChange",
    "EngineeringFileChangeOperation",
    "EngineeringImplementationProvider",
    "EngineeringImplementationContext",
    "ProjectEngineeringAgentExecutor",
    "ProjectEngineeringStepExecution",
    "ProjectEngineeringStepResult",
]
