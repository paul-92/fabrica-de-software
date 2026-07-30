"""Modelos do coordenador genérico de workflows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping, Protocol, runtime_checkable

from asep.timeline import TimelineEvent


class WorkflowStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }


@dataclass(slots=True)
class WorkflowContext:
    """Estado compartilhado pelas Steps durante uma execução."""

    run_id: str
    values: dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = field(
        default=WorkflowStatus.CREATED,
        init=False,
    )
    cancellation_requested: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id do WorkflowContext não pode ser vazio")

    def request_cancellation(self) -> None:
        self.cancellation_requested = True

    def snapshot(self) -> WorkflowContext:
        snapshot = WorkflowContext(
            run_id=self.run_id,
            values=deepcopy(self.values),
        )
        snapshot.status = self.status
        snapshot.cancellation_requested = self.cancellation_requested
        return snapshot


@runtime_checkable
class WorkflowStep(Protocol):
    """Unidade síncrona de trabalho coordenada pelo Orchestrator."""

    id: str

    def execute(self, context: WorkflowContext) -> None: ...


@dataclass(frozen=True, slots=True)
class WorkflowExecutionPolicy:
    stop_on_failure: bool = True
    allow_cancellation: bool = True


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    id: str
    steps: tuple[WorkflowStep, ...]
    name: str | None = None
    description: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    policy: WorkflowExecutionPolicy = field(
        default_factory=WorkflowExecutionPolicy
    )


@dataclass(frozen=True, slots=True)
class Workflow(WorkflowDefinition):
    """Definição legada que preserva validação imediata da Sprint 8.1."""

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("id do Workflow não pode ser vazio")
        if self.name is not None and not self.name.strip():
            raise ValueError("name do Workflow não pode ser vazio")
        if not self.steps:
            raise ValueError("Workflow deve possuir ao menos uma Step")
        identifiers = tuple(step.id for step in self.steps)
        if any(not identifier.strip() for identifier in identifiers):
            raise ValueError("id da WorkflowStep não pode ser vazio")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Workflow possui IDs de Step duplicados")


@dataclass(frozen=True, slots=True)
class WorkflowFailure:
    type: str
    message: str
    step_id: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    run_id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    finished_at: datetime
    completed_steps: tuple[str, ...]
    context: WorkflowContext
    error: WorkflowFailure | None = None
    failed_steps: tuple[str, ...] = ()
    timeline: tuple[TimelineEvent, ...] = ()
    metrics: Mapping[str, int | float] = field(default_factory=dict)
    final_result: Any = None

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def executed_steps(self) -> tuple[str, ...]:
        return self.completed_steps + self.failed_steps


WorkflowExecutionContext = WorkflowContext
WorkflowResult = WorkflowExecutionResult
