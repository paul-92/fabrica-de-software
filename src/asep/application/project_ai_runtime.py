"""Execução controlada de AI Runtime e histórico de projeto."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import re
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep._json_values import freeze_json
from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeRegistry, AIRuntimeRequest, AIRuntimeResult
from asep.application.project_sessions import ProjectSessionService
from asep.application.session_context import (
    SessionContextBuilder,
    session_runtime_context_char_count,
)
from asep.application.projects import ProjectService
from asep.application.session_memory import (
    ProjectSessionMemoryService,
    SessionMemoryContext,
    serialize_session_memory_context,
)
from asep.application.workspace_changes import WorkspaceChange, WorkspaceSnapshotter
from asep.projects import (
    ProjectExecution,
    ProjectExecutionRepository,
    ProjectExecutionStatus,
    ProjectOperationalPlan,
)


class ProjectOperationalPlanBuilder(Protocol):
    def build(self, execution: ProjectExecution) -> ProjectOperationalPlan: ...


class ProjectAIRuntimeExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    session_id: str
    runtime_id: str
    instruction: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY

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


class ProjectAIRuntimeExecutionService:
    def __init__(self, projects: ProjectService, runtimes: AIRuntimeRegistry,
                 sessions: ProjectSessionService, executions: ProjectExecutionRepository,
                 snapshotter: WorkspaceSnapshotter | None = None,
                 context_builder: SessionContextBuilder | None = None, *,
                 memory_service: ProjectSessionMemoryService | None = None,
                 operational_plan_builder: ProjectOperationalPlanBuilder | None = None,
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
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))
        self._locks_guard = Lock()
        self._write_locks: dict[str, Lock] = {}

    def execute(self, request: ProjectAIRuntimeExecutionRequest) -> ProjectAIRuntimeExecutionResult:
        project = self._projects.get(request.project_id)
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
        if self._operational_plan_builder is not None:
            execution = ProjectExecution.model_validate(
                {
                    **execution.model_dump(mode="python"),
                    "operational_plan": self._operational_plan_builder.build(
                        execution
                    ),
                }
            )
        self._executions.create(execution)
        try:
            runtime = self._runtimes.get(request.runtime_id)
        except Exception as error:
            self._persist_failure(execution, error)
            raise
        execution = ProjectExecution.model_validate({
            **execution.model_dump(), "model": runtime.identity.model_id,
        })
        self._executions.update(execution)
        runtime_request = AIRuntimeRequest(
            instruction=request.instruction, metadata=request.metadata,
            context={
                "project_session": session_context.model_dump(mode="json"),
                "session_memory": memory_context.model_dump(mode="json"),
            },
            workspace=project.workspace_path, execution_mode=request.execution_mode,
        )
        if request.execution_mode is AIRuntimeExecutionMode.READ_ONLY:
            try:
                result = runtime.execute(runtime_request)
            except Exception as error:
                self._persist_failure(execution, error)
                raise
            return self._persist_success(execution, result, ())

        lock = self._write_lock(request.project_id)
        if not lock.acquire(blocking=False):
            error = RuntimeError("workspace write já está em execução")
            self._persist_failure(execution, error)
            raise error
        try:
            before = self._snapshotter.capture(project.workspace_path)
            try:
                result = runtime.execute(runtime_request)
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
            return self._persist_success(execution, result, changes)
        except Exception as error:
            if self._executions.get(execution.execution_id).status is ProjectExecutionStatus.RUNNING:
                self._persist_failure(execution, error)
            raise
        finally:
            lock.release()

    def _persist_success(self, execution: ProjectExecution, result: AIRuntimeResult,
                         changes: tuple[WorkspaceChange, ...]) -> ProjectAIRuntimeExecutionResult:
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
    "ProjectOperationalPlanBuilder",
]
