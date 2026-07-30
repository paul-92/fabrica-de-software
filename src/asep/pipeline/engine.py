"""Fachada pública da execução ponta a ponta."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from asep.pipeline.models import GoalRequest, GoalResult
from asep.pipeline.pipeline import ExecutionPipeline


class ASEPEngine:
    def __init__(self, pipeline: ExecutionPipeline) -> None:
        self._pipeline = pipeline

    @property
    def pipeline(self) -> ExecutionPipeline:
        return self._pipeline

    def execute(
        self,
        goal: str,
        *,
        workspace: str | Path = ".",
        metadata: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> GoalResult:
        return self._pipeline.execute(
            GoalRequest(
                goal=goal,
                metadata=metadata or {},
                workspace=Path(workspace),
                options=options or {},
                created_at=datetime.now(UTC),
            )
        )


__all__ = ["ASEPEngine"]
