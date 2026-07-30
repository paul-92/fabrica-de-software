"""Serialização explícita de Run para armazenamento JSON."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import ValidationError

from asep.runs.errors import InvalidRunStorageFormatError
from asep.runs.models import Run


class RunCodec:
    @staticmethod
    def encode(run: Run) -> dict[str, Any]:
        serialized = run.model_dump(mode="json")
        return {
            "id": serialized["id"],
            "status": serialized["status"],
            "started_at": serialized["started_at"],
            "finished_at": serialized["finished_at"],
            "project_id": serialized["project_id"],
            "workflow_id": serialized["workflow_id"],
            "stage_id": serialized["stage_id"],
            "provider_name": serialized["provider_name"],
            "summary": serialized["summary"],
            "error": serialized["error"],
            "metadata": serialized["metadata"],
        }

    @staticmethod
    def decode(data: Mapping[str, Any]) -> Run:
        try:
            return Run.model_validate(data)
        except (TypeError, ValidationError) as exc:
            raise InvalidRunStorageFormatError(
                "Run persistido possui formato inválido."
            ) from exc
