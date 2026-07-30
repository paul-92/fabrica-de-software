"""Snapshot persistível de uma execução de workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from asep._json_values import freeze_json, json_value
from asep.workflow.models import WorkflowStatus


class WorkflowSnapshot(BaseModel):
    """Estado imutável e serializável, sem objetos vivos de execução."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workflow_id: str
    run_id: str
    workflow_version: str
    name: str | None = None
    description: str | None = None
    status: WorkflowStatus
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    executed_steps: tuple[str, ...] = ()
    pending_steps: tuple[str, ...] = ()
    agent_id: str | None = None
    timeline_event_ids: tuple[str, ...] = ()
    metrics: Mapping[str, Any] = Field(default_factory=dict)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_validator("id", "workflow_id", "run_id", "workflow_version")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identificadores e versão não podem ser vazios")
        return value

    @field_validator("name", "description", "agent_id")
    @classmethod
    def optional_text_is_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("campo textual opcional não pode ser vazio")
        return value

    @field_validator("started_at", "finished_at", "created_at")
    @classmethod
    def timestamp_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp deve possuir timezone")
        return value

    @field_validator("duration_seconds")
    @classmethod
    def duration_is_not_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_seconds não pode ser negativa")
        return value

    @field_validator("metrics", "metadata")
    @classmethod
    def mappings_are_json(
        cls,
        value: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return freeze_json(value, location="workflow snapshot")

    @field_serializer("metrics", "metadata")
    def serialize_mappings(
        self,
        value: Mapping[str, Any],
    ) -> dict[str, Any]:
        return json_value(value)

    @model_validator(mode="after")
    def state_is_consistent(self) -> WorkflowSnapshot:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at não pode preceder started_at")
        if set(self.executed_steps) & set(self.pending_steps):
            raise ValueError(
                "etapa não pode estar executada e pendente simultaneamente"
            )
        if len(set(self.timeline_event_ids)) != len(
            self.timeline_event_ids
        ):
            raise ValueError("timeline_event_ids possui duplicidade")
        return self
