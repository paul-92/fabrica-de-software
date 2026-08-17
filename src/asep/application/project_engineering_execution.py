"""Project-scoped ownership of a bounded engineering task."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import re
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
    ProjectIdempotentNoOpEvidence,
    ProjectExecutionRepository,
    ProjectExecutionStatus,
    ProjectOperationalPlan,
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanStep,
    ProjectRepairResult,
    ProjectValidationStatus,
    ProjectValidationFailureAnalysis,
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

    def prepare(self, request: ProjectAIRuntimeExecutionRequest) -> ProjectExecution: ...

    def execute_prepared(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult: ...

    def cancel_prepared(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectExecution: ...


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
        try:
            return self._complete_execution(runtime_result, execution)
        except Exception as error:
            self._persist_unexpected_failure(execution.execution_id, error)
            raise

    def prepare(self, request: ProjectAIRuntimeExecutionRequest) -> ProjectExecution:
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError("project engineering preparation requires workspace_write mode")
        return self._runtime_execution.prepare(request)

    def approve(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult:
        runtime_result = self._runtime_execution.execute_prepared(
            preparation_id, request,
        )
        execution = runtime_result.execution
        if execution.execution_id != preparation_id:
            raise RuntimeError("prepared execution identity changed")
        if execution.status is not ProjectExecutionStatus.RUNNING:
            raise RuntimeError("prepared runtime completed before validation")
        try:
            return self._complete_execution(runtime_result, execution)
        except Exception as error:
            self._persist_unexpected_failure(execution.execution_id, error)
            raise

    def cancel(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectExecution:
        return self._runtime_execution.cancel_prepared(preparation_id, request)

    def _complete_execution(
        self,
        runtime_result: ProjectAIRuntimeExecutionResult,
        execution: ProjectExecution,
    ) -> ProjectAIRuntimeExecutionResult:
        workspace = self._projects.get(execution.project_id).workspace_path
        captured_changes = runtime_result.changes or execution.changes
        if execution.changes != captured_changes:
            execution = ProjectExecution.model_validate({
                **execution.model_dump(mode="python"),
                "changes": captured_changes,
            })
        if not captured_changes:
            noop_evidence = self._verified_noop_evidence(execution)
            if noop_evidence is not None:
                execution = ProjectExecution.model_validate({
                    **execution.model_dump(mode="python"),
                    "idempotent_noop_evidence": noop_evidence,
                })
        self._executions.update(execution)
        runtime_result = runtime_result.model_copy(update={
            "changes": captured_changes,
            "execution": execution,
        })
        strategy_builder = getattr(self._validation, "strategy", None)
        strategy_runner = getattr(self._validation, "validate_strategy", None)
        strategy = None
        if strategy_builder is not None and execution.operational_plan is not None:
            strategy = strategy_builder(
                execution.execution_id,
                workspace,
                execution.operational_plan,
                analysis=runtime_result.bounded_analysis,
                changed_paths=tuple(item.path for item in execution.changes),
                idempotent_noop=execution.idempotent_noop_evidence is not None,
                evidence_paths=(
                    execution.idempotent_noop_evidence.artifact_paths
                    if execution.idempotent_noop_evidence is not None else ()
                ),
            )
            execution = ProjectExecution.model_validate({
                **execution.model_dump(mode="python"),
                "validation_strategy": strategy,
            })
            self._executions.update(execution)
            validations = list(strategy_runner(
                strategy, workspace, start_sequence=1,
            ))
        else:
            validations = list(self._validate_strategy(
                execution.execution_id,
                workspace,
                execution.operational_plan,
                start_sequence=1,
            ))
        execution = self._persist_progress(
            execution, validations=tuple(validations),
        )
        repair_result = None
        failure_analyses: list[ProjectValidationFailureAnalysis] = []
        failed = next(
            (item for item in validations if item.status is ProjectValidationStatus.FAILED),
            None,
        )
        if failed is not None:
            bounded_analyzer = getattr(self._validation, "analyze_failure", None)
            if bounded_analyzer is not None:
                bounded = bounded_analyzer(failed)
                failure_analyses.append(bounded)
                execution = self._persist_progress(
                    execution,
                    validations=tuple(validations),
                    failure_analyses=tuple(failure_analyses),
                )
                repair_evidence = (
                    f"task={execution.instruction}\n"
                    f"validator={bounded.validator_id}\n"
                    f"category={bounded.category.value}\n"
                    f"summary={bounded.summary}\n"
                    f"project_analysis={runtime_result.bounded_analysis.model_dump(mode='json') if runtime_result.bounded_analysis else {}}\n"
                    f"diff_paths={tuple(item.path for item in execution.changes)}\n"
                    f"plan_steps={tuple(item.step_id for item in execution.operational_plan.steps) if execution.operational_plan else ()}\n"
                    f"step_results={tuple(item.step_id for item in execution.step_results)}\n"
                    f"evidence={bounded.evidence}"
                )
            else:
                repair_evidence = f"[{failed.validator}] {failed.output}"
            analysis = self._repair.analyze(repair_evidence)
            repaired = self._repair.repair(
                execution.execution_id,
                workspace,
                analysis,
            )
            repair_result = ProjectRepairResult(
                execution_id=execution.execution_id,
                result=repaired,
            )
            execution = self._persist_progress(
                execution,
                validations=tuple(validations),
                failure_analyses=tuple(failure_analyses),
                repair=repair_result,
            )
            if strategy is not None and strategy_runner is not None:
                validations.extend(strategy_runner(
                    strategy,
                    workspace,
                    start_sequence=len(validations) + 1,
                    validators=(failed.validator,),
                ))
                latest_failed = validations[-1]
                if latest_failed.status is ProjectValidationStatus.PASSED:
                    failed_index = strategy.validators.index(failed.validator)
                    remaining = strategy.validators[failed_index + 1:]
                    if remaining:
                        validations.extend(strategy_runner(
                            strategy,
                            workspace,
                            start_sequence=len(validations) + 1,
                            validators=remaining,
                        ))
            else:
                validations.extend(self._validate_strategy(
                    execution.execution_id,
                    workspace,
                    execution.operational_plan,
                    start_sequence=len(validations) + 1,
                ))
            execution = self._persist_progress(
                execution,
                validations=tuple(validations),
                failure_analyses=tuple(failure_analyses),
                repair=repair_result,
            )

        final_by_validator = {item.validator: item for item in validations}
        required = strategy.validators if strategy is not None else tuple(final_by_validator)
        final_validations = tuple(final_by_validator[item] for item in required if item in final_by_validator)
        final_validation = final_validations[-1]
        gate = self._quality.evaluate_and_record(
            execution,
            final_validations,
            workspace,
        )
        execution = self._persist_progress(
            execution,
            validations=tuple(validations),
            failure_analyses=tuple(failure_analyses),
            repair=repair_result,
            quality_gate=gate,
        )
        validation_passed = (
            len(final_validations) == len(required)
            and any(item.status is ProjectValidationStatus.PASSED for item in final_validations)
            and all(item.status is not ProjectValidationStatus.FAILED for item in final_validations)
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
            "failure_analyses": tuple(failure_analyses),
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

    def _verified_noop_evidence(
        self, execution: ProjectExecution,
    ) -> ProjectIdempotentNoOpEvidence | None:
        fingerprint = execution.completion_workspace_fingerprint
        if fingerprint is None:
            return None
        candidates = reversed(self._executions.list_by_session(execution.session_id))
        for prior in candidates:
            if (
                prior.execution_id == execution.execution_id
                or prior.project_id != execution.project_id
                or prior.instruction != execution.instruction
                or prior.runtime_id != execution.runtime_id
                or prior.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE
                or prior.status is not ProjectExecutionStatus.SUCCEEDED
                or prior.completion_workspace_fingerprint != fingerprint
                or prior.quality_gate is None
                or prior.quality_gate.decision is GateDecision.BLOCKED
            ):
                continue
            paths = tuple(
                item.path for item in prior.changes
                if item.change_type.value != "deleted"
            ) or (
                prior.idempotent_noop_evidence.artifact_paths
                if prior.idempotent_noop_evidence is not None else ()
            )
            if paths:
                return ProjectIdempotentNoOpEvidence(
                    prior_execution_id=prior.execution_id,
                    workspace_fingerprint=fingerprint,
                    artifact_paths=paths,
                )
        return None

    def _persist_progress(self, execution: ProjectExecution, **updates) -> ProjectExecution:
        current = self._executions.get(execution.execution_id)
        if current.status is not ProjectExecutionStatus.RUNNING:
            return current
        updated = ProjectExecution.model_validate({
            **current.model_dump(mode="python"),
            **updates,
        })
        self._executions.update(updated)
        return updated

    def _persist_unexpected_failure(
        self, execution_id: str, error: Exception,
    ) -> None:
        current = self._executions.get(execution_id)
        if current.status is not ProjectExecutionStatus.RUNNING:
            return
        failed = ProjectExecution.model_validate({
            **current.model_dump(mode="python"),
            "status": ProjectExecutionStatus.FAILED,
            "error_code": self._public_error_code(error),
            "completed_at": self._clock(),
        })
        self._executions.update(failed)

    @staticmethod
    def _public_error_code(error: Exception) -> str:
        raw = getattr(error, "code", None) or type(error).__name__
        separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(raw))
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", separated).strip("_").upper()
        return (normalized or "UNEXPECTED_ERROR")[:100]

    def _validate_strategy(
        self,
        execution_id: str,
        workspace,
        plan,
        *,
        start_sequence: int,
    ):
        validate_plan = getattr(self._validation, "validate_plan", None)
        if validate_plan is not None and plan is not None:
            return validate_plan(
                execution_id,
                workspace,
                plan,
                start_sequence=start_sequence,
            )
        return (
            self._validation.validate(
                execution_id,
                workspace,
                sequence=start_sequence,
            ),
        )


__all__ = [
    "DeterministicProjectOperationalPlanBuilder",
    "ProjectEngineeringExecutionService",
    "ProjectRuntimeExecutionCapability",
]
