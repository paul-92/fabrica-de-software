"""Execução read-only de AI Runtime no workspace de um projeto."""

from __future__ import annotations

from typing import Any, Mapping
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep._json_values import freeze_json
from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeRegistry,
    AIRuntimeRequest,
    AIRuntimeResult,
)
from asep.application.projects import ProjectService
from asep.application.workspace_changes import WorkspaceChange, WorkspaceSnapshotter


class ProjectAIRuntimeExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    runtime_id: str
    instruction: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY

    @field_validator("project_id", "runtime_id", "instruction")
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


class ProjectAIRuntimeExecutionService:
    def __init__(
        self,
        projects: ProjectService,
        runtimes: AIRuntimeRegistry,
        snapshotter: WorkspaceSnapshotter | None = None,
    ) -> None:
        self._projects = projects
        self._runtimes = runtimes
        self._snapshotter = snapshotter or WorkspaceSnapshotter()
        self._locks_guard = Lock()
        self._write_locks: dict[str, Lock] = {}

    def execute(
        self,
        request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult:
        project = self._projects.get(request.project_id)
        runtime = self._runtimes.get(request.runtime_id)
        runtime_request = AIRuntimeRequest(
            instruction=request.instruction,
            metadata=request.metadata,
            workspace=project.workspace_path,
            execution_mode=request.execution_mode,
        )
        if request.execution_mode is AIRuntimeExecutionMode.READ_ONLY:
            return ProjectAIRuntimeExecutionResult(
                runtime_result=runtime.execute(runtime_request),
                execution_mode=request.execution_mode,
            )

        lock = self._write_lock(request.project_id)
        if not lock.acquire(blocking=False):
            raise RuntimeError("workspace write já está em execução")
        try:
            before = self._snapshotter.capture(project.workspace_path)
            try:
                runtime_result = runtime.execute(runtime_request)
            except Exception as error:
                try:
                    after = self._snapshotter.capture(project.workspace_path)
                    error.workspace_changes = self._snapshotter.changes(  # type: ignore[attr-defined]
                        before, after
                    )
                except Exception:
                    error.add_note("Workspace change evidence could not be completed.")
                raise
            after = self._snapshotter.capture(project.workspace_path)
            return ProjectAIRuntimeExecutionResult(
                runtime_result=runtime_result,
                changes=self._snapshotter.changes(before, after),
                execution_mode=request.execution_mode,
            )
        finally:
            lock.release()

    def _write_lock(self, project_id: str) -> Lock:
        with self._locks_guard:
            return self._write_locks.setdefault(project_id, Lock())


__all__ = [
    "ProjectAIRuntimeExecutionRequest",
    "ProjectAIRuntimeExecutionResult",
    "ProjectAIRuntimeExecutionService",
]
