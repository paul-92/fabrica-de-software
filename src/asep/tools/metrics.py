"""Métricas locais e injetáveis para execução de Tools."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from asep.tools.models import (
    ToolCapability,
    ToolExecutionStatus,
    ToolResult,
)


@dataclass(frozen=True, slots=True)
class ToolMetricsSnapshot:
    total: int
    succeeded: int
    failed: int
    rejected: int
    timed_out: int
    retries: int
    duration_seconds: tuple[float, ...]
    by_tool: dict[str, int]
    by_capability: dict[str, int]


@runtime_checkable
class ToolMetricsRecorder(Protocol):
    def record(
        self,
        result: ToolResult,
        capability: ToolCapability,
        *,
        retries: int,
    ) -> None: ...


class InMemoryToolMetrics:
    def __init__(self) -> None:
        self._counts = {status: 0 for status in ToolExecutionStatus}
        self._total = 0
        self._retries = 0
        self._durations: list[float] = []
        self._by_tool: dict[str, int] = {}
        self._by_capability: dict[str, int] = {}

    def record(
        self,
        result: ToolResult,
        capability: ToolCapability,
        *,
        retries: int,
    ) -> None:
        self._total += 1
        self._counts[result.status] += 1
        self._retries += retries
        self._durations.append(result.duration_seconds)
        tool_id = result.tool_id.value
        self._by_tool[tool_id] = self._by_tool.get(tool_id, 0) + 1
        self._by_capability[capability.id] = (
            self._by_capability.get(capability.id, 0) + 1
        )

    def snapshot(self) -> ToolMetricsSnapshot:
        return ToolMetricsSnapshot(
            total=self._total,
            succeeded=self._counts[ToolExecutionStatus.SUCCEEDED],
            failed=self._counts[ToolExecutionStatus.FAILED],
            rejected=self._counts[ToolExecutionStatus.REJECTED],
            timed_out=self._counts[ToolExecutionStatus.TIMED_OUT],
            retries=self._retries,
            duration_seconds=tuple(self._durations),
            by_tool=dict(sorted(self._by_tool.items())),
            by_capability=dict(sorted(self._by_capability.items())),
        )


__all__ = [
    "InMemoryToolMetrics",
    "ToolMetricsRecorder",
    "ToolMetricsSnapshot",
]

