"""Execução controlada de AI Runtime e histórico de projeto."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep._json_values import freeze_json
from asep.access.models import RequestPrincipal
from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeRegistry,
    AIRuntimeRequest,
    AIRuntimeResult,
)
from asep.application.project_sessions import ProjectSessionService
from asep.application.session_context import (
    SessionContextBuilder,
    SessionRuntimeContext,
    session_runtime_context_char_count,
)
from asep.application.projects import ProjectService
from asep.application.session_memory import (
    ProjectSessionMemoryService,
    SessionMemoryContext,
    serialize_session_memory_context,
)
from asep.application.workspace_changes import WorkspaceChange, WorkspaceSnapshotter
from asep.application.project_engineering_planning import BoundedProjectAnalysis
from asep.projects import (
    ProjectExecution,
    ProjectExecutionRepository,
    ProjectExecutionStatus,
    ProjectOperationalPlan,
    ProjectEngineeringStepResult,
)


class ProjectOperationalPlanBuilder(Protocol):
    def build(self, execution: ProjectExecution) -> ProjectOperationalPlan: ...


class ProjectEngineeringPlanningCapability(Protocol):
    def analyze(self, workspace: Path) -> BoundedProjectAnalysis: ...

    def plan_from_analysis(
        self,
        execution: ProjectExecution,
        analysis: BoundedProjectAnalysis,
        session_context: SessionRuntimeContext,
        memory_context: SessionMemoryContext,
    ) -> ProjectOperationalPlan: ...


class ProjectEngineeringInternalExecutionCapability(Protocol):
    def execute_supported_plan(
        self,
        execution: ProjectExecution,
        plan: ProjectOperationalPlan,
        workspace: Path,
        analysis: BoundedProjectAnalysis,
    ) -> tuple[ProjectEngineeringStepResult, ...] | None: ...


class ProjectAIRuntimeExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    session_id: str
    runtime_id: str
    instruction: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY
    principal: RequestPrincipal | None = None

    @field_validator("project_id", "session_id", "runtime_id", "instruction")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("campo obrigatório não pode ser vazio")
        return normalized

    @field_validator("metadata")
    @classmethod
    def metadata_is_json(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return freeze_json(value, location="project runtime metadata")


class ProjectAIRuntimeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    runtime_result: AIRuntimeResult
    changes: tuple[WorkspaceChange, ...] = ()
    execution_mode: AIRuntimeExecutionMode
    execution: ProjectExecution
    bounded_analysis: BoundedProjectAnalysis | None = None


class ProjectAIRuntimeExecutionService:
    def __init__(self, projects: ProjectService, runtimes: AIRuntimeRegistry,
                 sessions: ProjectSessionService, executions: ProjectExecutionRepository,
                 snapshotter: WorkspaceSnapshotter | None = None,
                 context_builder: SessionContextBuilder | None = None, *,
                 memory_service: ProjectSessionMemoryService | None = None,
                 operational_plan_builder: ProjectOperationalPlanBuilder | None = None,
                 engineering_planning: ProjectEngineeringPlanningCapability | None = None,
                 internal_execution: ProjectEngineeringInternalExecutionCapability | None = None,
                 defer_completion: bool = False,
                 clock: Callable[[], datetime] | None = None,
                 id_generator: Callable[[], str] | None = None) -> None:
        self._projects = projects
        self._runtimes = runtimes
        self._sessions = sessions
        self._executions = executions
        self._snapshotter = snapshotter or WorkspaceSnapshotter()
        self._context_builder = context_builder or SessionContextBuilder(executions)
        self._memory = memory_service
        self._operational_plan_builder = operational_plan_builder
        self._engineering_planning = engineering_planning
        self._internal_execution = internal_execution
        self._defer_completion = defer_completion
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))
        self._locks_guard = Lock()
        self._write_locks: dict[str, Lock] = {}

    def prepare(
        self, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectExecution:
        """Persist a real plan without crossing the workspace mutation boundary."""
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError("project engineering preparation requires workspace_write mode")
        if self._engineering_planning is None:
            raise RuntimeError("project engineering planning is unavailable")
        project = self._projects.get(request.project_id, request.principal)
        self._sessions.get(request.project_id, request.session_id)
        session_context = self._context_builder.build(request.project_id, request.session_id)
        memory_context = (
            self._memory.context(request.project_id, request.session_id)
            if self._memory is not None else SessionMemoryContext()
        )
        before = self._snapshotter.capture(project.workspace_path)
        execution = ProjectExecution(
            execution_id=self._id_generator(), session_id=request.session_id,
            project_id=request.project_id, runtime_id=request.runtime_id,
            instruction=request.instruction, execution_mode=request.execution_mode,
            status=ProjectExecutionStatus.PENDING,
            context_entry_count=len(session_context.entries),
            context_truncated=session_context.truncated,
            context_char_count=session_runtime_context_char_count(session_context),
            context_omitted_execution_count=session_context.omitted_execution_count,
            memory_entry_count=len(memory_context.entries),
            memory_char_count=len(serialize_session_memory_context(memory_context)),
            memory_truncated=memory_context.truncated,
            created_at=self._clock(),
        )
        analysis = self._engineering_planning.analyze(project.workspace_path)
        plan = self._engineering_planning.plan_from_analysis(
            execution, analysis, session_context, memory_context,
        )
        after = self._snapshotter.capture(project.workspace_path)
        if self._snapshotter.changes(before, after):
            raise RuntimeError("planning mutated the workspace")
        prepared = ProjectExecution.model_validate({
            **execution.model_dump(mode="python"),
            "operational_plan": plan,
            "preparation_analysis": analysis.model_dump(mode="json"),
            "preparation_workspace_fingerprint": self._snapshot_fingerprint(after),
            "preparation_context_fingerprint": self._context_fingerprint(
                session_context, memory_context,
            ),
        })
        self._executions.create(prepared)
        return prepared

    def execute_prepared(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult:
        """Execute exactly one persisted preparation after fail-closed checks."""
        prepared = self._executions.get(preparation_id)
        if prepared.status is not ProjectExecutionStatus.PENDING:
            raise ValueError("preparation is not available for approval")
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError("prepared execution requires workspace_write mode")
        if (
            prepared.project_id != request.project_id
            or prepared.session_id != request.session_id
            or prepared.runtime_id != request.runtime_id
            or prepared.instruction != request.instruction
        ):
            raise ValueError("preparation identity does not match approval")
        if prepared.operational_plan is None or not prepared.preparation_analysis:
            raise ValueError("prepared plan is invalid")
        project = self._projects.get(request.project_id, request.principal)
        self._sessions.get(request.project_id, request.session_id)
        session_context = self._context_builder.build(request.project_id, request.session_id)
        memory_context = (
            self._memory.context(request.project_id, request.session_id)
            if self._memory is not None else SessionMemoryContext()
        )
        current_snapshot = self._snapshotter.capture(project.workspace_path)
        if (
            self._snapshot_fingerprint(current_snapshot)
            != prepared.preparation_workspace_fingerprint
            or self._context_fingerprint(session_context, memory_context)
            != prepared.preparation_context_fingerprint
        ):
            raise ValueError("preparation context is stale")
        analysis = BoundedProjectAnalysis.model_validate(prepared.preparation_analysis)
        execution = ProjectExecution.model_validate({
            **prepared.model_dump(mode="python"), "status": ProjectExecutionStatus.RUNNING,
        })
        self._executions.update(execution)
        return self._execute_prepared_runtime(
            request, execution, project.workspace_path, analysis,
            session_context, memory_context, current_snapshot,
        )

    def cancel_prepared(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectExecution:
        prepared = self._executions.get(preparation_id)
        if prepared.status is not ProjectExecutionStatus.PENDING:
            raise ValueError("preparation is not available for cancellation")
        if (
            prepared.project_id != request.project_id
            or prepared.session_id != request.session_id
            or prepared.runtime_id != request.runtime_id
            or prepared.instruction != request.instruction
        ):
            raise ValueError("preparation identity does not match cancellation")
        cancelled = ProjectExecution.model_validate({
            **prepared.model_dump(mode="python"),
            "status": ProjectExecutionStatus.FAILED,
            "error_code": "PREPARATION_CANCELLED",
            "completed_at": self._clock(),
        })
        self._executions.update(cancelled)
        return cancelled

    def _execute_prepared_runtime(
        self, request, execution, workspace, analysis, session_context,
        memory_context, before,
    ) -> ProjectAIRuntimeExecutionResult:
        try:
            runtime = self._runtimes.get(request.runtime_id)
            execution = ProjectExecution.model_validate({
                **execution.model_dump(mode="python"), "model": runtime.identity.model_id,
            })
            self._executions.update(execution)
            runtime_request = AIRuntimeRequest(
                instruction=request.instruction,
                metadata=request.metadata,
                context={
                    "project_session": session_context.model_dump(mode="json"),
                    "session_memory": memory_context.model_dump(mode="json"),
                    "project_engineering": {
                        "task": execution.instruction,
                        "project_analysis": analysis.model_dump(mode="json"),
                        "ordered_steps": tuple(
                            step.model_dump(mode="json")
                            for step in execution.operational_plan.steps
                        ),
                        "guidance": (
                            "Follow the validated step order and dependencies.",
                            "Treat target_hints as candidate areas and inspect before assuming files exist.",
                            "Respect the supplied workspace and sandbox boundaries.",
                            "Produce an implementation compatible with the current task.",
                        ),
                    },
                },
                workspace=workspace,
                execution_mode=request.execution_mode,
            )
            lock = self._write_lock(request.project_id)
            if not lock.acquire(blocking=False):
                raise RuntimeError("workspace write já está em execução")
            try:
                step_results = (
                    self._internal_execution.execute_supported_plan(
                        execution, execution.operational_plan, workspace, analysis,
                    ) if self._internal_execution is not None else None
                )
                if step_results is None:
                    result = runtime.execute(runtime_request)
                else:
                    execution = ProjectExecution.model_validate({
                        **execution.model_dump(mode="python"), "step_results": step_results,
                    })
                    self._executions.update(execution)
                    if any(not item.succeeded for item in step_results):
                        raise RuntimeError("DeveloperAgent step execution failed")
                    result = AIRuntimeResult(
                        output="Project plan executed by DeveloperAgent.",
                        identity=AIRuntimeIdentity(runtime_id="developer-agent", model_id="controlled-tools"),
                        metadata={"executor": "developer_agent"},
                    )
                changes = self._snapshotter.changes(before, self._snapshotter.capture(workspace))
                return self._persist_success(execution, result, changes).model_copy(
                    update={"bounded_analysis": analysis}
                )
            finally:
                lock.release()
        except Exception as error:
            changes = ()
            try:
                changes = self._snapshotter.changes(before, self._snapshotter.capture(workspace))
            except Exception:
                error.add_note("Workspace change evidence could not be completed.")
            if self._executions.get(execution.execution_id).status is ProjectExecutionStatus.RUNNING:
                self._persist_failure(execution, error, changes)
            raise

    @staticmethod
    def _snapshot_fingerprint(snapshot) -> str:
        payload = {
            path: state.model_dump(mode="json")
            for path, state in sorted(snapshot.items())
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _context_fingerprint(session_context, memory_context) -> str:
        payload = {
            "session": session_context.model_dump(mode="json"),
            "memory": memory_context.model_dump(mode="json"),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def execute(self, request: ProjectAIRuntimeExecutionRequest) -> ProjectAIRuntimeExecutionResult:
        project = self._projects.get(request.project_id, request.principal)
        self._sessions.get(request.project_id, request.session_id)
        session_context = self._context_builder.build(
            request.project_id, request.session_id
        )
        memory_context = (
            self._memory.context(request.project_id, request.session_id)
            if self._memory is not None
            else SessionMemoryContext()
        )
        execution = ProjectExecution(
            execution_id=self._id_generator(), session_id=request.session_id,
            project_id=request.project_id, runtime_id=request.runtime_id,
            instruction=request.instruction, execution_mode=request.execution_mode,
            status=ProjectExecutionStatus.RUNNING,
            context_entry_count=len(session_context.entries),
            context_truncated=session_context.truncated,
            context_char_count=session_runtime_context_char_count(session_context),
            context_omitted_execution_count=session_context.omitted_execution_count,
            memory_entry_count=len(memory_context.entries),
            memory_char_count=len(serialize_session_memory_context(memory_context)),
            memory_truncated=memory_context.truncated,
            created_at=self._clock(),
        )
        self._executions.create(execution)
        bounded_analysis = None
        try:
            if self._engineering_planning is not None:
                bounded_analysis = self._engineering_planning.analyze(
                    project.workspace_path
                )
                plan = self._engineering_planning.plan_from_analysis(
                    execution,
                    bounded_analysis,
                    session_context,
                    memory_context,
                )
                execution = ProjectExecution.model_validate(
                    {**execution.model_dump(mode="python"), "operational_plan": plan}
                )
            elif self._operational_plan_builder is not None:
                execution = ProjectExecution.model_validate(
                    {
                        **execution.model_dump(mode="python"),
                        "operational_plan": self._operational_plan_builder.build(
                            execution
                        ),
                    }
                )
            if execution.operational_plan is not None:
                self._executions.update(execution)
        except Exception as error:
            self._persist_failure(execution, error)
            raise
        try:
            runtime = self._runtimes.get(request.runtime_id)
        except Exception as error:
            self._persist_failure(execution, error)
            raise
        execution = ProjectExecution.model_validate({
            **execution.model_dump(), "model": runtime.identity.model_id,
        })
        self._executions.update(execution)
        runtime_context = {
            "project_session": session_context.model_dump(mode="json"),
            "session_memory": memory_context.model_dump(mode="json"),
        }
        if execution.operational_plan is not None and bounded_analysis is not None:
            runtime_context["project_engineering"] = {
                "task": execution.instruction,
                "project_analysis": bounded_analysis.model_dump(mode="json"),
                "ordered_steps": tuple(
                    step.model_dump(mode="json")
                    for step in execution.operational_plan.steps
                ),
                "guidance": (
                    "Follow the validated step order and dependencies.",
                    "Treat target_hints as candidate areas and inspect before assuming files exist.",
                    "Respect the supplied workspace and sandbox boundaries.",
                    "Produce an implementation compatible with the current task.",
                ),
            }
        runtime_request = AIRuntimeRequest(
            instruction=request.instruction, metadata=request.metadata,
            context=runtime_context,
            workspace=project.workspace_path, execution_mode=request.execution_mode,
        )
        if request.execution_mode is AIRuntimeExecutionMode.READ_ONLY:
            try:
                result = runtime.execute(runtime_request)
            except Exception as error:
                self._persist_failure(execution, error)
                raise
            return self._persist_success(execution, result, ()).model_copy(
                update={"bounded_analysis": bounded_analysis}
            )

        lock = self._write_lock(request.project_id)
        if not lock.acquire(blocking=False):
            error = RuntimeError("workspace write já está em execução")
            self._persist_failure(execution, error)
            raise error
        try:
            before = self._snapshotter.capture(project.workspace_path)
            try:
                step_results = (
                    self._internal_execution.execute_supported_plan(
                        execution,
                        execution.operational_plan,
                        project.workspace_path,
                        bounded_analysis,
                    )
                    if self._internal_execution is not None
                    and execution.operational_plan is not None
                    else None
                )
                if step_results is None:
                    result = runtime.execute(runtime_request)
                else:
                    execution = ProjectExecution.model_validate({
                        **execution.model_dump(mode="python"),
                        "step_results": step_results,
                    })
                    self._executions.update(execution)
                    if any(not item.succeeded for item in step_results):
                        raise RuntimeError("DeveloperAgent step execution failed")
                    result = AIRuntimeResult(
                        output="Project plan executed by DeveloperAgent.",
                        identity=AIRuntimeIdentity(
                            runtime_id="developer-agent",
                            model_id="controlled-tools",
                        ),
                        metadata={"executor": "developer_agent"},
                    )
            except Exception as error:
                changes: tuple[WorkspaceChange, ...] = ()
                try:
                    changes = self._snapshotter.changes(before, self._snapshotter.capture(project.workspace_path))
                    error.workspace_changes = changes  # type: ignore[attr-defined]
                except Exception:
                    error.add_note("Workspace change evidence could not be completed.")
                self._persist_failure(execution, error, changes)
                raise
            changes = self._snapshotter.changes(before, self._snapshotter.capture(project.workspace_path))
            return self._persist_success(execution, result, changes).model_copy(
                update={"bounded_analysis": bounded_analysis}
            )
        except Exception as error:
            if self._executions.get(execution.execution_id).status is ProjectExecutionStatus.RUNNING:
                self._persist_failure(execution, error)
            raise
        finally:
            lock.release()

    def _persist_success(self, execution: ProjectExecution, result: AIRuntimeResult,
                         changes: tuple[WorkspaceChange, ...]) -> ProjectAIRuntimeExecutionResult:
        if self._defer_completion:
            pending_validation = ProjectExecution.model_validate({
                **execution.model_dump(),
                "output": result.output,
                "model": result.identity.model_id,
                "usage": result.usage,
                "changes": changes,
            })
            self._executions.update(pending_validation)
            return ProjectAIRuntimeExecutionResult(
                runtime_result=result,
                changes=changes,
                execution_mode=execution.execution_mode,
                execution=pending_validation,
            )
        completed = ProjectExecution.model_validate({**execution.model_dump(), **{
            "status": ProjectExecutionStatus.SUCCEEDED, "output": result.output,
            "model": result.identity.model_id, "usage": result.usage,
            "changes": changes, "completed_at": self._clock(),
        }})
        self._executions.update(completed)
        if self._memory is not None:
            self._memory.extract_and_add(completed)
        return ProjectAIRuntimeExecutionResult(runtime_result=result, changes=changes,
                                               execution_mode=execution.execution_mode,
                                               execution=completed)

    def _persist_failure(self, execution: ProjectExecution, error: Exception,
                         changes: tuple[WorkspaceChange, ...] = ()) -> None:
        explicit_code = getattr(error, "code", None)
        if explicit_code is None:
            code = re.sub(
                r"(?<!^)(?=[A-Z])", "_", type(error).__name__
            ).upper()
            if code.startswith("AI_RUNTIME_") and code.endswith("_ERROR"):
                code = code[:-6]
        else:
            code = str(explicit_code).upper()
        failed = ProjectExecution.model_validate({**execution.model_dump(), **{
            "status": ProjectExecutionStatus.FAILED, "changes": changes,
            "error_code": code, "completed_at": self._clock(),
        }})
        self._executions.update(failed)

    def _write_lock(self, project_id: str) -> Lock:
        with self._locks_guard:
            return self._write_locks.setdefault(project_id, Lock())


__all__ = [
    "ProjectAIRuntimeExecutionRequest",
    "ProjectAIRuntimeExecutionResult",
    "ProjectAIRuntimeExecutionService",
    "ProjectEngineeringPlanningCapability",
    "ProjectEngineeringInternalExecutionCapability",
    "ProjectOperationalPlanBuilder",
]
