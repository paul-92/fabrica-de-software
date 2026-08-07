from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceChangeType(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


class WorkspaceChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    change_type: WorkspaceChangeType
    size_before: int | None = Field(default=None, ge=0)
    size_after: int | None = Field(default=None, ge=0)


__all__ = ["WorkspaceChange", "WorkspaceChangeType"]
