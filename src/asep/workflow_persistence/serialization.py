"""Codec explícito para WorkflowSnapshot."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import ValidationError

from asep.workflow_persistence.errors import (
    InvalidWorkflowStorageFormatError,
)
from asep.workflow_persistence.models import WorkflowSnapshot


class WorkflowSnapshotCodec:
    @staticmethod
    def encode(snapshot: WorkflowSnapshot) -> dict[str, Any]:
        return snapshot.model_dump(mode="json")

    @staticmethod
    def decode(data: Mapping[str, Any]) -> WorkflowSnapshot:
        try:
            return WorkflowSnapshot.model_validate(data)
        except (TypeError, ValidationError) as exc:
            raise InvalidWorkflowStorageFormatError(
                "WorkflowSnapshot persistido possui formato inválido."
            ) from exc
