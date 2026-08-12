"""Read-only query contract for project session memory."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.errors import AsepError
from asep.projects.session_memory_models import (
    SessionMemoryEntry,
    SessionMemoryKind,
)

DEFAULT_SESSION_MEMORY_PAGE_SIZE = 25
MAX_SESSION_MEMORY_PAGE_SIZE = 100


class SessionMemoryOrder(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"


class SessionMemoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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
            raise ValueError("session memory query identifier must not be blank")
        return normalized

    @field_validator("text")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_session_memory_text(value)
        if not normalized:
            raise ValueError("session memory query text must not be blank")
        return normalized

    @field_validator("cursor")
    @classmethod
    def cursor_is_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("session memory query cursor must not be blank")
        return value


class SessionMemoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[SessionMemoryEntry, ...] = ()
    next_cursor: str | None = None


class InvalidSessionMemoryCursorError(AsepError):
    code = "SESSION_MEMORY_CURSOR_INVALID"
    category = "validation"
    exit_code = 2


@runtime_checkable
class SessionMemoryQuerySource(Protocol):
    def query(self, query: SessionMemoryQuery) -> SessionMemoryPage: ...


class SessionMemoryCursor(BaseModel):
    """Internal payload encoded as canonical URL-safe base64 JSON."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int = Field(alias="v")
    created_at: datetime = Field(alias="t")
    memory_id: str = Field(alias="i")
    order: SessionMemoryOrder = Field(alias="o")
    project_id: str = Field(alias="p")
    session_id: str = Field(alias="s")
    text: str | None = Field(alias="q")
    kind: SessionMemoryKind | None = Field(alias="k")

    @field_validator("created_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session memory cursor timestamp must be aware")
        return value

    @field_validator("memory_id", "project_id", "session_id")
    @classmethod
    def cursor_identifier_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("session memory cursor identifier must not be blank")
        return value


def normalize_session_memory_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def encode_session_memory_cursor(
    entry: SessionMemoryEntry,
    query: SessionMemoryQuery,
) -> str:
    payload = SessionMemoryCursor(
        v=1,
        t=entry.created_at,
        i=entry.memory_id,
        o=query.order,
        p=query.project_id,
        s=query.session_id,
        q=query.text,
        k=query.kind,
    ).model_dump_json(by_alias=True)
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def decode_session_memory_cursor(
    value: str,
    query: SessionMemoryQuery,
) -> SessionMemoryCursor:
    try:
        padding = "=" * (-len(value) % 4)
        raw = base64.b64decode(
            value + padding,
            altchars=b"-_",
            validate=True,
        )
        document = json.loads(raw.decode("utf-8"))
        cursor = SessionMemoryCursor.model_validate(document)
        if cursor.version != 1 or (
            cursor.order,
            cursor.project_id,
            cursor.session_id,
            cursor.text,
            cursor.kind,
        ) != (
            query.order,
            query.project_id,
            query.session_id,
            query.text,
            query.kind,
        ):
            raise ValueError
        return cursor
    except (binascii.Error, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise InvalidSessionMemoryCursorError(
            "Session memory cursor is invalid."
        ) from exc


__all__ = [
    "DEFAULT_SESSION_MEMORY_PAGE_SIZE",
    "InvalidSessionMemoryCursorError",
    "MAX_SESSION_MEMORY_PAGE_SIZE",
    "SessionMemoryOrder",
    "SessionMemoryPage",
    "SessionMemoryQuery",
    "SessionMemoryQuerySource",
]
