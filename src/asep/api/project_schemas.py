from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from asep.projects import WorkspaceProject


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
