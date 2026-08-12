"""Authorized Application projection for scoped session-memory queries."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.application.project_sessions import ProjectSessionService
from asep.projects import (
    DEFAULT_SESSION_MEMORY_PAGE_SIZE,
    MAX_SESSION_MEMORY_PAGE_SIZE,
    InvalidSessionMemoryCursorError,
    SessionMemoryEntry,
    SessionMemoryKind,
    SessionMemoryOrder,
    SessionMemoryQuery,
    SessionMemoryQuerySource,
)


class SessionMemorySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    project_id: str
    session_id: str
    text: str | None = None
    kind: SessionMemoryKind | None = None
    order: SessionMemoryOrder = SessionMemoryOrder.NEWEST
    page_size: int = Field(
        default=DEFAULT_SESSION_MEMORY_PAGE_SIZE,
        ge=1,
        le=MAX_SESSION_MEMORY_PAGE_SIZE,
    )
    cursor: str | None = None

    @field_validator("project_id", "session_id")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("session memory search identifier must not be blank")
        return normalized


class SessionMemorySearchItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    memory_id: str
    project_id: str
    session_id: str
    kind: SessionMemoryKind
    content: str
    source_execution_id: str | None = None
    created_at: datetime

    @classmethod
    def from_entry(cls, entry: SessionMemoryEntry) -> "SessionMemorySearchItem":
        return cls.model_validate(entry.model_dump())


class SessionMemorySearchPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    items: tuple[SessionMemorySearchItem, ...] = ()
    next_cursor: str | None = None


class SessionMemorySearchService:
    def __init__(
        self,
        sessions: ProjectSessionService,
        source: SessionMemoryQuerySource,
    ) -> None:
        self._sessions = sessions
        self._source = source

    def search(
        self,
        request: SessionMemorySearchRequest,
    ) -> SessionMemorySearchPage:
        self._sessions.get(request.project_id, request.session_id)
        page = self._source.query(SessionMemoryQuery(
            project_id=request.project_id,
            session_id=request.session_id,
            text=request.text,
            kind=request.kind,
            order=request.order,
            page_size=request.page_size,
            cursor=request.cursor,
        ))
        return SessionMemorySearchPage(
            items=tuple(
                SessionMemorySearchItem.from_entry(entry)
                for entry in page.items
            ),
            next_cursor=page.next_cursor,
        )


__all__ = [
    "InvalidSessionMemoryCursorError",
    "SessionMemoryKind",
    "SessionMemoryOrder",
    "SessionMemorySearchItem",
    "SessionMemorySearchPage",
    "SessionMemorySearchRequest",
    "SessionMemorySearchService",
]
