from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator
from asep.access.models import LEGACY_ADMIN_USER_ID, LEGACY_ORGANIZATION_ID


class WorkspaceProject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    organization_id: str = LEGACY_ORGANIZATION_ID
    created_by_user_id: str = LEGACY_ADMIN_USER_ID
    name: str
    workspace_path: Path
    created_at: datetime
    updated_at: datetime

    @field_validator("project_id", "name")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project_id e name não podem ser vazios")
        return value
