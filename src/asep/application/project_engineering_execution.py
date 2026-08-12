"""Project-scoped ownership of a bounded engineering task."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application.project_ai_runtime import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionResult,
)
from asep.application.project_engineering_quality import (
    ProjectQualityGateCapability,
)
from asep.application.project_engineering_repair import ProjectRepairCapability
from asep.application.project_engineering_validation import (
    ProjectValidationCapability,
)
from asep.application.projects import ProjectService
from asep.application.session_memory import ProjectSessionMemoryService
from asep.execution.models import GateDecision
from asep.projects import (
    ProjectExecution,
    ProjectExecutionRepository,
    ProjectExecutionStatus,
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
    ProjectRepairResult,
    ProjectValidationStatus,
)
from asep.repair import RepairStatus


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

    def __init__(
        self,
        runtime_execution: ProjectRuntimeExecutionCapability,
        projects: ProjectService,
        executions: ProjectExecutionRepository,
        memory: ProjectSessionMemoryService,
        validation: ProjectValidationCapability,
        repair: ProjectRepairCapability,
        quality: ProjectQualityGateCapability,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._runtime_execution = runtime_execution
        self._projects = projects
        self._executions = executions
        self._memory = memory
        self._validation = validation
        self._repair = repair
        self._quality = quality
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult:
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError(
                "project engineering execution requires workspace_write mode"
            )
        runtime_result = self._runtime_execution.execute(request)
        execution = runtime_result.execution
        if execution.status is not ProjectExecutionStatus.RUNNING:
            raise RuntimeError(
                "project engineering runtime completed before validation"
            )
        workspace = self._projects.get(execution.project_id).workspace_path
        validations = [
            self._validation.validate(
                execution.execution_id,
                workspace,
                sequence=1,
            )
        ]
        repair_result = None
        if validations[0].status is ProjectValidationStatus.FAILED:
            analysis = self._repair.analyze(validations[0].output)
            repaired = self._repair.repair(
                execution.execution_id,
                workspace,
                analysis,
            )
            repair_result = ProjectRepairResult(
                execution_id=execution.execution_id,
                result=repaired,
            )
            validations.append(self._validation.validate(
                execution.execution_id,
                workspace,
                sequence=2,
            ))

        final_validation = validations[-1]
        gate = self._quality.evaluate_and_record(
            execution,
            final_validation,
            workspace,
        )
        validation_passed = (
            final_validation.status is ProjectValidationStatus.PASSED
        )
        gate_passed = gate.decision is not GateDecision.BLOCKED
        succeeded = validation_passed and gate_passed
        error_code = None
        if not succeeded:
            if (
                repair_result is not None
                and repair_result.result.status is RepairStatus.EXHAUSTED
            ):
                error_code = "REPAIR_EXHAUSTED"
            elif not validation_passed:
                error_code = "VALIDATION_FAILED"
            else:
                error_code = "QUALITY_GATE_BLOCKED"
        completed = ProjectExecution.model_validate({
            **execution.model_dump(mode="python"),
            "status": (
                ProjectExecutionStatus.SUCCEEDED
                if succeeded
                else ProjectExecutionStatus.FAILED
            ),
            "validations": tuple(validations),
            "repair": repair_result,
            "quality_gate": gate,
            "error_code": error_code,
            "completed_at": self._clock(),
        })
        self._executions.update(completed)
        if succeeded:
            self._memory.extract_and_add(completed)
        return ProjectAIRuntimeExecutionResult(
            runtime_result=runtime_result.runtime_result,
            changes=runtime_result.changes,
            execution_mode=runtime_result.execution_mode,
            execution=completed,
        )


__all__ = [
    "DeterministicProjectOperationalPlanBuilder",
    "ProjectEngineeringExecutionService",
    "ProjectRuntimeExecutionCapability",
]
