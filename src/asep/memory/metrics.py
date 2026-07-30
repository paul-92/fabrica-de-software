"""Métricas locais e injetáveis de memória operacional."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class MemoryMetricsSnapshot:
    entries_total: int
    reads_total: int
    writes_total: int
    updates_total: int
    deletes_total: int
    hits_total: int
    misses_total: int
    context_build_duration: tuple[float, ...]


@runtime_checkable
class MemoryMetricsRecorder(Protocol):
    def entry_count(self, count: int) -> None: ...
    def read(self, *, hit: bool) -> None: ...
    def write(self) -> None: ...
    def update(self) -> None: ...
    def delete(self) -> None: ...
    def context_built(self, duration_seconds: float) -> None: ...


class InMemoryMemoryMetrics:
    def __init__(self) -> None:
        self._entries = 0
        self._reads = 0
        self._writes = 0
        self._updates = 0
        self._deletes = 0
        self._hits = 0
        self._misses = 0
        self._context_durations: list[float] = []

    def entry_count(self, count: int) -> None:
        self._entries = count

    def read(self, *, hit: bool) -> None:
        self._reads += 1
        if hit:
            self._hits += 1
        else:
            self._misses += 1

    def write(self) -> None:
        self._writes += 1

    def update(self) -> None:
        self._updates += 1

    def delete(self) -> None:
        self._deletes += 1

    def context_built(self, duration_seconds: float) -> None:
        self._context_durations.append(duration_seconds)

    def snapshot(self) -> MemoryMetricsSnapshot:
        return MemoryMetricsSnapshot(
            entries_total=self._entries,
            reads_total=self._reads,
            writes_total=self._writes,
            updates_total=self._updates,
            deletes_total=self._deletes,
            hits_total=self._hits,
            misses_total=self._misses,
            context_build_duration=tuple(self._context_durations),
        )


__all__ = [
    "InMemoryMemoryMetrics",
    "MemoryMetricsRecorder",
    "MemoryMetricsSnapshot",
]

