from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceEntryKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"


class WorkspaceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    name: str
    kind: WorkspaceEntryKind
    size: int | None = Field(default=None, ge=0)


class WorkspaceDirectory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    entries: tuple[WorkspaceEntry, ...]


class WorkspaceFileContent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    name: str
    content: str
    size: int = Field(ge=0)
    language: str
    truncated: bool = False


__all__ = ["WorkspaceDirectory", "WorkspaceEntry", "WorkspaceEntryKind", "WorkspaceFileContent"]
