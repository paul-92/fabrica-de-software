from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.projects import WorkspaceProject
from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application.workspace_changes import WorkspaceChangeType


class ProjectHttpSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateProjectRequest(ProjectHttpSchema):
    name: str
    workspace_path: str

    @field_validator("name", "workspace_path")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value


class ProjectResponse(ProjectHttpSchema):
    project_id: str
    name: str
    workspace_path: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: WorkspaceProject) -> "ProjectResponse":
        return cls(
            project_id=project.project_id,
            name=project.name,
            workspace_path=str(project.workspace_path),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectListResponse(ProjectHttpSchema):
    items: tuple[ProjectResponse, ...]


class ProjectAIRuntimeExecutionRequestBody(ProjectHttpSchema):
    runtime_id: str
    instruction: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY

    @field_validator("runtime_id", "instruction")
    @classmethod
    def execution_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value.strip()


class AIRuntimeUsageResponse(ProjectHttpSchema):
    input_units: int | None
    output_units: int | None
    total_units: int | None
    cost: float | None


class WorkspaceChangeResponse(ProjectHttpSchema):
    path: str
    change_type: WorkspaceChangeType
    size_before: int | None
    size_after: int | None


class ProjectAIRuntimeExecutionResponse(ProjectHttpSchema):
    output: str
    runtime_id: str
    model_id: str
    usage: AIRuntimeUsageResponse | None
    metadata: dict[str, Any]
    execution_mode: AIRuntimeExecutionMode
    changes: tuple[WorkspaceChangeResponse, ...] = ()
