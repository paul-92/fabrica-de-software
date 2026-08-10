from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.projects import ProjectExecution, ProjectSession, WorkspaceProject
from asep.ai_runtime import AIRuntimeExecutionMode
from asep.workspace_changes import WorkspaceChangeType


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
    session_id: str
    runtime_id: str
    instruction: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY

    @field_validator("session_id", "runtime_id", "instruction")
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
    execution_id: str
    output: str
    runtime_id: str
    model_id: str
    usage: AIRuntimeUsageResponse | None
    metadata: dict[str, Any]
    execution_mode: AIRuntimeExecutionMode
    changes: tuple[WorkspaceChangeResponse, ...] = ()
    context_entry_count: int
    context_truncated: bool
    context_char_count: int
    context_omitted_execution_count: int


class CreateProjectSessionRequest(ProjectHttpSchema):
    title: str

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized


class ProjectSessionResponse(ProjectHttpSchema):
    session_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, session: ProjectSession) -> "ProjectSessionResponse":
        return cls.model_validate(session.model_dump(mode="json"))


class ProjectSessionListResponse(ProjectHttpSchema):
    items: tuple[ProjectSessionResponse, ...]


class ProjectExecutionResponse(ProjectHttpSchema):
    execution_id: str
    session_id: str
    project_id: str
    runtime_id: str
    instruction: str
    execution_mode: AIRuntimeExecutionMode
    status: str
    output: str | None
    model: str | None
    usage: AIRuntimeUsageResponse | None
    changes: tuple[WorkspaceChangeResponse, ...]
    error_code: str | None
    context_entry_count: int
    context_truncated: bool
    context_char_count: int
    context_omitted_execution_count: int
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_domain(cls, execution: ProjectExecution) -> "ProjectExecutionResponse":
        return cls.model_validate(execution.model_dump(mode="json"))


class ProjectExecutionListResponse(ProjectHttpSchema):
    items: tuple[ProjectExecutionResponse, ...]
