"""Memória durável, limitada e explicitamente pertencente a ProjectSession."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from asep.application.project_sessions import ProjectSessionService
from asep.application.projects import ProjectService
from asep.memory.filtering import MemoryFilter
from asep.projects import (
    ProjectExecution,
    SessionMemoryEntry,
    SessionMemoryKind,
    SessionMemoryRepository,
)
from asep.workspace_changes import WorkspaceChangeType


class SessionMemoryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_memory_entries: int = Field(default=50, ge=1, le=500)
    max_memory_content_chars: int = Field(default=2_000, ge=1, le=20_000)
    max_memory_context_chars: int = Field(default=8_000, ge=128, le=50_000)


class SessionMemoryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: SessionMemoryKind
    content: str = Field(min_length=1)


class SessionMemoryContextEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str
    kind: SessionMemoryKind
    content: str
    source_execution_id: str | None = None


class SessionMemoryContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: tuple[SessionMemoryContextEntry, ...] = ()
    truncated: bool = False


def serialize_session_memory_context(context: SessionMemoryContext) -> str:
    return json.dumps(
        {"session_memory": context.model_dump(mode="json")},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class SessionMemorySelector:
    def __init__(self, policy: SessionMemoryPolicy | None = None) -> None:
        self._policy = policy or SessionMemoryPolicy()

    def select(self, entries_newest_first: tuple[SessionMemoryEntry, ...]) -> SessionMemoryContext:
        selected: list[SessionMemoryContextEntry] = []
        candidates = entries_newest_first[: self._policy.max_memory_entries]
        truncated = len(candidates) < len(entries_newest_first)
        for entry in candidates:
            projected = SessionMemoryContextEntry(
                memory_id=entry.memory_id,
                kind=entry.kind,
                content=entry.content[: self._policy.max_memory_content_chars],
                source_execution_id=entry.source_execution_id,
            )
            field_truncated = projected.content != entry.content
            candidate = SessionMemoryContext(
                entries=tuple(reversed([*selected, projected])),
                truncated=truncated or field_truncated,
            )
            if len(serialize_session_memory_context(candidate)) > self._policy.max_memory_context_chars:
                truncated = True
                break
            selected.append(projected)
            truncated = truncated or field_truncated
        return SessionMemoryContext(entries=tuple(reversed(selected)), truncated=truncated)


class SessionMemoryExtractor:
    """Extrai somente artifacts estruturados de changes created."""

    def extract(self, execution: ProjectExecution) -> tuple[SessionMemoryDraft, ...]:
        if execution.status.value != "succeeded":
            return ()
        return tuple(
            SessionMemoryDraft(
                kind=SessionMemoryKind.ARTIFACT,
                content=f"Created {change.path}",
            )
            for change in sorted(execution.changes, key=lambda item: item.path)
            if change.change_type is WorkspaceChangeType.CREATED
        )


class ProjectSessionMemoryService:
    def __init__(
        self,
        projects: ProjectService,
        sessions: ProjectSessionService,
        repository: SessionMemoryRepository,
        policy: SessionMemoryPolicy | None = None,
        extractor: SessionMemoryExtractor | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._projects = projects
        self._sessions = sessions
        self._repository = repository
        self._policy = policy or SessionMemoryPolicy()
        self._selector = SessionMemorySelector(self._policy)
        self._extractor = extractor or SessionMemoryExtractor()
        self._filter = MemoryFilter()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def add(
        self,
        project_id: str,
        session_id: str,
        kind: SessionMemoryKind,
        content: str,
        *,
        source_execution_id: str | None = None,
    ) -> SessionMemoryEntry:
        self._projects.get(project_id)
        self._sessions.get(project_id, session_id)
        normalized = _normalized(content)
        if not normalized:
            raise ValueError("session memory content must not be blank")
        if len(normalized) > self._policy.max_memory_content_chars:
            raise ValueError("session memory content exceeds backend limit")
        safe_content, _, _ = self._filter.sanitize(normalized, {})
        for current in self._repository.list_by_session(session_id):
            if (
                current.project_id == project_id
                and current.kind is kind
                and _dedup_key(current.content) == _dedup_key(safe_content)
            ):
                return current
        entry = SessionMemoryEntry(
            memory_id=self._id_generator(),
            session_id=session_id,
            project_id=project_id,
            kind=kind,
            content=safe_content,
            source_execution_id=source_execution_id,
            created_at=self._clock(),
        )
        self._repository.add(entry)
        return entry

    def list(self, project_id: str, session_id: str) -> tuple[SessionMemoryEntry, ...]:
        self._projects.get(project_id)
        self._sessions.get(project_id, session_id)
        return tuple(
            entry for entry in self._repository.list_by_session(session_id)
            if entry.project_id == project_id
        )

    def context(self, project_id: str, session_id: str) -> SessionMemoryContext:
        return self._selector.select(self.list(project_id, session_id))

    def extract_and_add(self, execution: ProjectExecution) -> tuple[SessionMemoryEntry, ...]:
        return tuple(
            self.add(
                execution.project_id,
                execution.session_id,
                draft.kind,
                draft.content,
                source_execution_id=execution.execution_id,
            )
            for draft in self._extractor.extract(execution)
        )


def _normalized(value: str) -> str:
    return " ".join(value.split())


def _dedup_key(value: str) -> str:
    return _normalized(value).casefold()


__all__ = [
    "ProjectSessionMemoryService",
    "SessionMemoryContext",
    "SessionMemoryContextEntry",
    "SessionMemoryDraft",
    "SessionMemoryExtractor",
    "SessionMemoryPolicy",
    "SessionMemorySelector",
    "serialize_session_memory_context",
]
