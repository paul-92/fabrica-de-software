"""Execução read-only de AI Runtime no workspace de um projeto."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep._json_values import freeze_json
from asep.ai_runtime import AIRuntimeRegistry, AIRuntimeRequest, AIRuntimeResult
from asep.application.projects import ProjectService


class ProjectAIRuntimeExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    runtime_id: str
    instruction: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)

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


class ProjectAIRuntimeExecutionService:
    def __init__(
        self,
        projects: ProjectService,
        runtimes: AIRuntimeRegistry,
    ) -> None:
        self._projects = projects
        self._runtimes = runtimes

    def execute(
        self,
        request: ProjectAIRuntimeExecutionRequest,
    ) -> AIRuntimeResult:
        project = self._projects.get(request.project_id)
        runtime = self._runtimes.get(request.runtime_id)
        return runtime.execute(
            AIRuntimeRequest(
                instruction=request.instruction,
                metadata=request.metadata,
                workspace=project.workspace_path,
            )
        )


__all__ = [
    "ProjectAIRuntimeExecutionRequest",
    "ProjectAIRuntimeExecutionService",
]
