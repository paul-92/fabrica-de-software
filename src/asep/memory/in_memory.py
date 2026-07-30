"""MemoryStore em memória, determinístico e isolado por instância."""

from collections.abc import Mapping

from asep.agents.contracts import AgentId
from asep.memory.exceptions import (
    MemoryAlreadyExistsError,
    MemoryNotFoundError,
)
from asep.memory.models import MemoryEntry, MemoryId, MemoryQuery


def _matches_metadata(
    actual: Mapping[str, object], expected: Mapping[str, object]
) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def _sorted(entries) -> tuple[MemoryEntry, ...]:
    return tuple(
        sorted(
            entries,
            key=lambda item: (
                item.created_at,
                item.memory_id.value,
            ),
        )
    )


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}

    def save(self, entry: MemoryEntry) -> None:
        key = entry.memory_id.value
        if key in self._entries:
            raise MemoryAlreadyExistsError(f"Memória já existe: {key}")
        self._entries[key] = entry

    def update(self, entry: MemoryEntry) -> None:
        key = entry.memory_id.value
        if key not in self._entries:
            raise MemoryNotFoundError(f"Memória não encontrada: {key}")
        self._entries[key] = entry

    def get(self, memory_id: MemoryId) -> MemoryEntry:
        try:
            return self._entries[memory_id.value]
        except KeyError as exc:
            raise MemoryNotFoundError(
                f"Memória não encontrada: {memory_id}"
            ) from exc

    def delete(self, memory_id: MemoryId) -> None:
        if memory_id.value not in self._entries:
            raise MemoryNotFoundError(
                f"Memória não encontrada: {memory_id}"
            )
        del self._entries[memory_id.value]

    def find_by_agent(self, agent_id: AgentId) -> tuple[MemoryEntry, ...]:
        return _sorted(
            item
            for item in self._entries.values()
            if item.agent_id == agent_id
        )

    def find_by_execution(
        self, execution_id: str
    ) -> tuple[MemoryEntry, ...]:
        return _sorted(
            item
            for item in self._entries.values()
            if item.execution_id == execution_id
        )

    def search(self, query: MemoryQuery) -> tuple[MemoryEntry, ...]:
        text = query.text.casefold() if query.text is not None else None
        return _sorted(
            item
            for item in self._entries.values()
            if (query.agent_id is None or item.agent_id == query.agent_id)
            and (query.category is None or item.category == query.category)
            and (text is None or text in item.content.casefold())
            and (
                query.execution_id is None
                or item.execution_id == query.execution_id
            )
            and (
                query.workflow_execution_id is None
                or item.workflow_execution_id
                == query.workflow_execution_id
            )
            and _matches_metadata(item.metadata, query.metadata)
        )

    def clear(self, agent_id: AgentId | None = None) -> int:
        keys = [
            key
            for key, item in self._entries.items()
            if agent_id is None or item.agent_id == agent_id
        ]
        for key in keys:
            del self._entries[key]
        return len(keys)

    def count(self, agent_id: AgentId | None = None) -> int:
        if agent_id is None:
            return len(self._entries)
        return sum(
            item.agent_id == agent_id for item in self._entries.values()
        )


__all__ = ["InMemoryMemoryStore"]
