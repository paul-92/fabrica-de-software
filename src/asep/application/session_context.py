"""Projeção segura e limitada de ProjectExecution para contexto de runtime."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.projects import (
    ProjectExecution,
    ProjectExecutionRepository,
    ProjectExecutionStatus,
)
from asep.workspace_changes import WorkspaceChangeType


class SessionContextPolicy(BaseModel):
    """Limites exclusivamente backend para continuidade de uma ProjectSession."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_entries: int = Field(default=8, ge=0, le=50)
    max_instruction_chars_per_entry: int = Field(default=2_000, ge=1, le=20_000)
    max_summary_chars_per_entry: int = Field(default=4_000, ge=1, le=40_000)
    max_total_chars: int = Field(default=20_000, ge=1, le=100_000)
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
    """Projeção mínima; deliberadamente não é ProjectExecution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    instruction: str
    status: ProjectExecutionStatus
    summary: str | None = None
    error_code: str | None = None
    changes: tuple[SessionContextChange, ...] = ()
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
    """Contexto ASEP efêmero e provider-agnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    entries: tuple[SessionContextEntry, ...] = ()
    truncated: bool = False

    @field_validator("session_id")
    @classmethod
    def session_id_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("session_id must not be blank")
        return normalized


class SessionContextBuilder:
    """Deriva contexto determinístico sem criar conversa de provider."""

    def __init__(
        self,
        executions: ProjectExecutionRepository,
        policy: SessionContextPolicy | None = None,
    ) -> None:
        self._executions = executions
        self._policy = policy or SessionContextPolicy()

    def build(self, project_id: str, session_id: str) -> SessionRuntimeContext:
        eligible = tuple(
            execution
            for execution in self._executions.list_by_session(session_id)
            if execution.project_id == project_id
            and execution.status
            in {ProjectExecutionStatus.SUCCEEDED, ProjectExecutionStatus.FAILED}
        )
        selected = eligible[: self._policy.max_entries]
        remaining = self._policy.max_total_chars
        projected: list[SessionContextEntry] = []
        truncated = len(selected) < len(eligible)

        # Repository order is newest-first, so a finite budget favors recency.
        for execution in selected:
            entry, remaining = self._project(execution, remaining)
            if entry is None:
                truncated = True
                break
            projected.append(entry)
            truncated = truncated or any(
                (
                    entry.instruction_truncated,
                    entry.summary_truncated,
                    entry.changes_truncated,
                )
            )

        return SessionRuntimeContext(
            session_id=session_id,
            entries=tuple(reversed(projected)),
            truncated=truncated,
        )

    def _project(
        self, execution: ProjectExecution, remaining: int
    ) -> tuple[SessionContextEntry | None, int]:
        instruction_source = _safe_text(execution.instruction)
        instruction = instruction_source[
            : self._policy.max_instruction_chars_per_entry
        ]
        instruction_truncated = instruction != instruction_source
        instruction = instruction[:remaining]
        instruction_truncated = instruction_truncated or instruction != instruction_source
        remaining -= len(instruction)
        if not instruction:
            return None, remaining

        summary_source = (
            None if execution.output is None else _safe_text(execution.output)
        )
        summary = summary_source
        summary_truncated = False
        if summary is not None:
            summary = summary[: self._policy.max_summary_chars_per_entry]
            summary_truncated = summary != summary_source
            summary = summary[:remaining]
            summary_truncated = summary_truncated or summary != summary_source
            remaining -= len(summary)
            if not summary:
                summary = None

        changes: list[SessionContextChange] = []
        source_changes = execution.changes[: self._policy.max_changes_per_entry]
        changes_truncated = len(source_changes) < len(execution.changes)
        for change in source_changes:
            path_source = _safe_text(change.path)
            path = path_source[: self._policy.max_change_path_chars]
            path = path[:remaining]
            if not path:
                changes_truncated = True
                break
            changes_truncated = changes_truncated or path != path_source
            remaining -= len(path)
            changes.append(
                SessionContextChange(path=path, change_type=change.change_type)
            )

        return SessionContextEntry(
            execution_id=execution.execution_id,
            instruction=instruction,
            status=execution.status,
            summary=summary,
            error_code=execution.error_code,
            changes=tuple(changes),
            instruction_truncated=instruction_truncated,
            summary_truncated=summary_truncated,
            changes_truncated=changes_truncated,
        ), remaining


def _safe_text(value: str) -> str:
    """Normaliza eventuais surrogates isolados para JSON/UTF-8 válido."""

    return value.encode("utf-8", errors="replace").decode("utf-8")


__all__ = [
    "SessionContextBuilder",
    "SessionContextChange",
    "SessionContextEntry",
    "SessionContextPolicy",
    "SessionRuntimeContext",
]
