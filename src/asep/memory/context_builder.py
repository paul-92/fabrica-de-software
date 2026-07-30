"""Construção limitada e serializável do contexto operacional do agente."""

from __future__ import annotations

import json
from collections.abc import Callable
from time import perf_counter
from typing import Any

from asep._json_values import json_value
from asep.memory.filtering import MemoryFilter
from asep.memory.models import (
    ContextBuildRequest,
    ContextBuildResult,
    MemoryEntry,
)
from asep.memory.service import MemoryService
from asep.timeline import TimelineEventType, TimelineRecorder

Timer = Callable[[], float]


class ContextBuilder:
    def __init__(
        self,
        memory_service: MemoryService,
        *,
        timeline: TimelineRecorder,
        memory_filter: MemoryFilter | None = None,
        timer: Timer | None = None,
    ) -> None:
        self._memory = memory_service
        self._timeline = timeline
        self._filter = memory_filter or MemoryFilter()
        self._timer = timer or perf_counter

    def build(self, request: ContextBuildRequest) -> ContextBuildResult:
        started = self._timer()
        entries = self._memory.find_by_agent(request.agent_id)
        ordered = tuple(
            sorted(
                entries,
                key=lambda item: (
                    -int(item.importance),
                    -item.updated_at.timestamp(),
                    item.memory_id.value,
                ),
            )
        )
        _, safe_metadata, _ = self._filter.sanitize("", request.metadata)
        _, safe_workflow, _ = self._filter.sanitize(
            "", request.workflow_context
        )
        selected: list[MemoryEntry] = []
        memory_payload: list[dict[str, Any]] = []
        truncated = False
        for entry in ordered:
            item = {
                "memory_id": entry.memory_id.value,
                "category": entry.category.value,
                "importance": entry.importance.name.lower(),
                "content": entry.content,
                "metadata": json_value(entry.metadata),
            }
            candidate = {
                "workflow": safe_workflow,
                "metadata": safe_metadata,
                "memories": [*memory_payload, item],
            }
            size = len(
                json.dumps(
                    candidate,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            if size > self._memory.policy.max_context_size:
                truncated = True
                continue
            selected.append(entry)
            memory_payload.append(item)

        context = {
            "workflow": safe_workflow,
            "metadata": safe_metadata,
            "memories": memory_payload,
        }
        duration = max(0.0, self._timer() - started)
        self._memory.record_context_duration(duration)
        run_id = request.workflow_execution_id or request.execution_id
        self._timeline.record(
            run_id,
            TimelineEventType.CONTEXT_BUILT,
            message=TimelineEventType.CONTEXT_BUILT.value,
            metadata={
                "agent_id": request.agent_id.value,
                "execution_id": request.execution_id,
                "memory_count": len(selected),
                "truncated": truncated,
                "duration_seconds": duration,
            },
        )
        return ContextBuildResult(
            context=context,
            memories=tuple(selected),
            truncated=truncated,
            duration_seconds=duration,
        )


__all__ = ["ContextBuilder"]

