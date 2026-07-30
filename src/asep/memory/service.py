"""Serviço de aplicação para memória operacional."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from asep.agents.contracts import AgentId
from asep.memory.contracts import MemoryStore
from asep.memory.exceptions import MemoryNotFoundError
from asep.memory.filtering import MemoryFilter
from asep.memory.metrics import MemoryMetricsRecorder
from asep.memory.models import (
    MemoryEntry,
    MemoryId,
    MemoryImportance,
    MemoryQuery,
    MemoryRetentionPolicy,
)
from asep.timeline import TimelineEventType, TimelineRecorder

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _NullMetrics:
    def entry_count(self, count: int) -> None:
        del count

    def read(self, *, hit: bool) -> None:
        del hit

    def write(self) -> None:
        pass

    def update(self) -> None:
        pass

    def delete(self) -> None:
        pass

    def context_built(self, duration_seconds: float) -> None:
        del duration_seconds


class MemoryService:
    def __init__(
        self,
        store: MemoryStore,
        *,
        timeline: TimelineRecorder,
        metrics: MemoryMetricsRecorder | None = None,
        memory_filter: MemoryFilter | None = None,
        policy: MemoryRetentionPolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._store = store
        self._timeline = timeline
        self._metrics = metrics or _NullMetrics()
        self._filter = memory_filter or MemoryFilter()
        self._policy = policy or MemoryRetentionPolicy()
        self._clock = clock or _utc_now
        self._metrics.entry_count(self._store.count())

    @property
    def policy(self) -> MemoryRetentionPolicy:
        return self._policy

    def save(self, entry: MemoryEntry) -> MemoryEntry:
        filtered = self._filtered_entry(entry)
        self._store.save(filtered)
        self._metrics.write()
        self._metrics.entry_count(self._store.count())
        self._record(filtered, TimelineEventType.MEMORY_SAVED)
        self._enforce_retention(filtered.agent_id)
        return filtered

    def update(
        self,
        entry: MemoryEntry,
        *,
        content: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        importance: MemoryImportance | None = None,
    ) -> MemoryEntry:
        current = self._store.get(entry.memory_id)
        updated = MemoryEntry.model_validate(
            {
                **current.model_dump(mode="python"),
                "content": content if content is not None else current.content,
                "metadata": (
                    metadata if metadata is not None else current.metadata
                ),
                "importance": importance or current.importance,
                "updated_at": self._clock(),
            }
        )
        filtered = self._filtered_entry(updated)
        self._store.update(filtered)
        self._metrics.update()
        self._record(filtered, TimelineEventType.MEMORY_UPDATED)
        return filtered

    def get(self, memory_id: MemoryId) -> MemoryEntry:
        self.expire()
        try:
            entry = self._store.get(memory_id)
        except MemoryNotFoundError:
            self._metrics.read(hit=False)
            raise
        self._metrics.read(hit=True)
        self._record(entry, TimelineEventType.MEMORY_LOADED)
        return entry

    def search(self, query: MemoryQuery) -> tuple[MemoryEntry, ...]:
        self.expire()
        entries = self._store.search(query)
        self._metrics.read(hit=bool(entries))
        run_id = query.workflow_execution_id or query.execution_id
        if run_id is not None:
            self._timeline.record(
                run_id,
                TimelineEventType.MEMORY_LOADED,
                message=TimelineEventType.MEMORY_LOADED.value,
                metadata={"count": len(entries)},
            )
        return entries

    def remove(self, memory_id: MemoryId) -> None:
        entry = self._store.get(memory_id)
        self._store.delete(memory_id)
        self._metrics.delete()
        self._metrics.entry_count(self._store.count())
        self._record(entry, TimelineEventType.MEMORY_DELETED)

    def clear(self, agent_id: AgentId | None = None) -> int:
        removed = self._store.clear(agent_id)
        for _ in range(removed):
            self._metrics.delete()
        self._metrics.entry_count(self._store.count())
        return removed

    def expire(self) -> int:
        if not self._policy.remove_expired:
            return 0
        now = self._clock()
        entries = self._store.search(MemoryQuery())
        expired = [
            item
            for item in entries
            if item.expires_at is not None and item.expires_at <= now
        ]
        for item in expired:
            self._store.delete(item.memory_id)
            self._metrics.delete()
            self._record(item, TimelineEventType.MEMORY_EXPIRED)
        if expired:
            self._metrics.entry_count(self._store.count())
        return len(expired)

    def find_by_agent(self, agent_id: AgentId) -> tuple[MemoryEntry, ...]:
        self.expire()
        entries = self._store.find_by_agent(agent_id)
        self._metrics.read(hit=bool(entries))
        return entries

    def summarize(self, agent_id: AgentId) -> str:
        return "\n".join(
            f"[{item.category.value}] {item.content}"
            for item in self.find_by_agent(agent_id)
        )

    def record_context_duration(self, duration_seconds: float) -> None:
        self._metrics.context_built(duration_seconds)

    def _filtered_entry(self, entry: MemoryEntry) -> MemoryEntry:
        content, metadata, was_filtered = self._filter.sanitize(
            entry.content, entry.metadata
        )
        expires_at = entry.expires_at
        if (
            expires_at is None
            and self._policy.expiration_seconds is not None
        ):
            expires_at = entry.created_at + timedelta(
                seconds=self._policy.expiration_seconds
            )
        filtered = MemoryEntry.model_validate(
            {
                **entry.model_dump(mode="python"),
                "content": content,
                "metadata": metadata,
                "expires_at": expires_at,
            }
        )
        if was_filtered:
            self._record(filtered, TimelineEventType.MEMORY_FILTERED)
        return filtered

    def _enforce_retention(self, agent_id: AgentId) -> None:
        entries = list(self._store.find_by_agent(agent_id))
        excess = len(entries) - self._policy.max_entries
        if excess <= 0:
            return
        if self._policy.remove_low_priority:
            entries.sort(
                key=lambda item: (
                    item.importance,
                    item.updated_at,
                    item.memory_id.value,
                )
            )
        else:
            entries.sort(
                key=lambda item: (
                    item.updated_at,
                    item.memory_id.value,
                )
            )
        for item in entries[:excess]:
            self._store.delete(item.memory_id)
            self._metrics.delete()
            self._record(item, TimelineEventType.MEMORY_DELETED)
        self._metrics.entry_count(self._store.count())

    def _record(
        self, entry: MemoryEntry, event_type: TimelineEventType
    ) -> None:
        self._timeline.record(
            entry.workflow_execution_id or entry.execution_id,
            event_type,
            message=event_type.value,
            metadata={
                "memory_id": entry.memory_id.value,
                "agent_id": entry.agent_id.value,
                "execution_id": entry.execution_id,
                "category": entry.category.value,
                "importance": entry.importance.name.lower(),
            },
        )


__all__ = ["MemoryService"]
