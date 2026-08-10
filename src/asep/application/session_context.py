"""Projeção e compactação determinística de contexto de ProjectSession."""

import json
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.projects import ProjectExecution, ProjectExecutionRepository, ProjectExecutionStatus
from asep.workspace_changes import WorkspaceChangeType


class SessionContextPolicy(BaseModel):
    """Budget único, backend-owned, medido em caracteres do JSON canônico."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_entries: int = Field(default=8, ge=0, le=50)
    max_instruction_chars_per_entry: int = Field(default=2_000, ge=1, le=20_000)
    max_summary_chars_per_entry: int = Field(default=4_000, ge=1, le=40_000)
    max_total_chars: int = Field(default=20_000, ge=256, le=100_000)
    max_changes_per_entry: int = Field(default=50, ge=0, le=500)
    max_change_path_chars: int = Field(default=500, ge=1, le=2_000)


class SessionContextChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    change_type: WorkspaceChangeType

    @field_validator("path")
    @classmethod
    def path_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("session context change path must not be blank")
        return value


class SessionContextEntry(BaseModel):
    """Projeção segura; deliberadamente não é ProjectExecution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    instruction: str
    status: ProjectExecutionStatus
    summary: str | None = None
    error_code: str | None = None
    changes: tuple[SessionContextChange, ...] = ()
    omitted_change_count: int = Field(default=0, ge=0)
    instruction_truncated: bool = False
    summary_truncated: bool = False
    changes_truncated: bool = False

    @field_validator("execution_id", "instruction")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("session context entry text must not be blank")
        return value


class SessionRuntimeContext(BaseModel):
    """Contexto ASEP efêmero, compactado e provider-agnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    entries: tuple[SessionContextEntry, ...] = ()
    truncated: bool = False
    omitted_execution_count: int = Field(default=0, ge=0)

    @field_validator("session_id")
    @classmethod
    def session_id_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("session_id must not be blank")
        return normalized


def serialize_session_runtime_context(context: SessionRuntimeContext) -> str:
    """Serializa no formato canônico usado para medir o budget."""

    return json.dumps(
        {"project_session": context.model_dump(mode="json")},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def session_runtime_context_char_count(context: SessionRuntimeContext) -> int:
    return len(serialize_session_runtime_context(context))


class ContextCompactor:
    """Aplica budget real ao JSON final sem IA, tokens ou aleatoriedade."""

    def __init__(self, policy: SessionContextPolicy | None = None) -> None:
        self._policy = policy or SessionContextPolicy()

    def compact(
        self,
        session_id: str,
        entries_newest_first: tuple[SessionContextEntry, ...],
    ) -> SessionRuntimeContext:
        eligible_count = len(entries_newest_first)
        selected = entries_newest_first[: self._policy.max_entries]
        included_newest_first: list[SessionContextEntry] = []

        for entry in selected:
            compacted = self._fit_entry(
                session_id,
                included_newest_first,
                entry,
                eligible_count,
            )
            if compacted is None:
                break
            included_newest_first.append(compacted)

        omitted = eligible_count - len(included_newest_first)
        entries = tuple(reversed(included_newest_first))
        truncated = omitted > 0 or any(_entry_was_compacted(item) for item in entries)
        context = SessionRuntimeContext(
            session_id=session_id,
            entries=entries,
            truncated=truncated,
            omitted_execution_count=omitted,
        )
        if session_runtime_context_char_count(context) > self._policy.max_total_chars:
            # Defensive fixed-envelope fallback. Normal ASEP UUID session IDs fit comfortably.
            return SessionRuntimeContext(
                session_id=session_id,
                truncated=eligible_count > 0,
                omitted_execution_count=eligible_count,
            )
        return context

    def _fit_entry(
        self,
        session_id: str,
        included_newest_first: list[SessionContextEntry],
        entry: SessionContextEntry,
        eligible_count: int,
    ) -> SessionContextEntry | None:
        if self._fits(session_id, included_newest_first, entry, eligible_count):
            return entry

        # Secondary information is removed first.
        if entry.summary is not None:
            entry = entry.model_copy(update={"summary": None, "summary_truncated": True})
            if self._fits(session_id, included_newest_first, entry, eligible_count):
                return entry

        # Changes retain deterministic order; tail items are omitted first.
        while entry.changes:
            entry = entry.model_copy(update={
                "changes": entry.changes[:-1],
                "omitted_change_count": entry.omitted_change_count + 1,
                "changes_truncated": True,
            })
            if self._fits(session_id, included_newest_first, entry, eligible_count):
                return entry

        # Instruction is highest priority and is truncated only after optional data.
        instruction = _longest_fitting_prefix(
            entry.instruction,
            lambda value: self._fits(
                session_id,
                included_newest_first,
                entry.model_copy(update={
                    "instruction": value,
                    "instruction_truncated": value != entry.instruction,
                }),
                eligible_count,
            ),
        )
        if not instruction:
            return None
        return entry.model_copy(update={
            "instruction": instruction,
            "instruction_truncated": instruction != entry.instruction,
        })

    def _fits(
        self,
        session_id: str,
        included_newest_first: list[SessionContextEntry],
        candidate: SessionContextEntry,
        eligible_count: int,
    ) -> bool:
        included = [*included_newest_first, candidate]
        context = SessionRuntimeContext(
            session_id=session_id,
            entries=tuple(reversed(included)),
            truncated=(eligible_count > len(included))
            or any(_entry_was_compacted(item) for item in included),
            omitted_execution_count=eligible_count - len(included),
        )
        return session_runtime_context_char_count(context) <= self._policy.max_total_chars


class SessionContextBuilder:
    """Seleciona history elegível, projeta e delega budget ao compactor."""

    def __init__(
        self,
        executions: ProjectExecutionRepository,
        policy: SessionContextPolicy | None = None,
        compactor: ContextCompactor | None = None,
    ) -> None:
        self._executions = executions
        self._policy = policy or SessionContextPolicy()
        self._compactor = compactor or ContextCompactor(self._policy)

    def build(self, project_id: str, session_id: str) -> SessionRuntimeContext:
        eligible = tuple(
            execution
            for execution in self._executions.list_by_session(session_id)
            if execution.project_id == project_id
            and execution.status in {ProjectExecutionStatus.SUCCEEDED, ProjectExecutionStatus.FAILED}
        )
        projected = tuple(self._project(execution) for execution in eligible)
        return self._compactor.compact(session_id, projected)

    def _project(self, execution: ProjectExecution) -> SessionContextEntry:
        instruction_source = _safe_text(execution.instruction)
        instruction = instruction_source[: self._policy.max_instruction_chars_per_entry]
        summary_source = None if execution.output is None else _safe_text(execution.output)
        summary = None if summary_source is None else summary_source[: self._policy.max_summary_chars_per_entry]
        sorted_changes = tuple(sorted(execution.changes, key=lambda item: (item.change_type.value, item.path)))
        selected_changes = sorted_changes[: self._policy.max_changes_per_entry]
        changes = tuple(
            SessionContextChange(
                path=_safe_text(change.path)[: self._policy.max_change_path_chars],
                change_type=change.change_type,
            )
            for change in selected_changes
        )
        omitted_changes = len(sorted_changes) - len(changes)
        return SessionContextEntry(
            execution_id=execution.execution_id,
            instruction=instruction,
            status=execution.status,
            summary=summary,
            error_code=execution.error_code,
            changes=changes,
            omitted_change_count=omitted_changes,
            instruction_truncated=instruction != instruction_source,
            summary_truncated=summary != summary_source,
            changes_truncated=omitted_changes > 0 or any(
                item.path != source.path
                for item, source in zip(changes, selected_changes, strict=True)
            ),
        )


def _entry_was_compacted(entry: SessionContextEntry) -> bool:
    return entry.instruction_truncated or entry.summary_truncated or entry.changes_truncated


def _longest_fitting_prefix(value: str, fits: Callable[[str], bool]) -> str:
    low, high = 1, len(value)
    result = ""
    while low <= high:
        middle = (low + high) // 2
        candidate = value[:middle]
        if fits(candidate):
            result = candidate
            low = middle + 1
        else:
            high = middle - 1
    return result


def _safe_text(value: str) -> str:
    return value.encode("utf-8", errors="replace").decode("utf-8")


__all__ = [
    "ContextCompactor",
    "SessionContextBuilder",
    "SessionContextChange",
    "SessionContextEntry",
    "SessionContextPolicy",
    "SessionRuntimeContext",
    "serialize_session_runtime_context",
    "session_runtime_context_char_count",
]
