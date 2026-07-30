from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

import pytest

from asep.agents import AgentId
from asep.memory import (
    InMemoryMemoryStore,
    MemoryAlreadyExistsError,
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
    MemoryNotFoundError,
    MemoryQuery,
    MemoryRetentionPolicy,
    SQLiteMemoryStore,
)

NOW = datetime(2026, 7, 30, 14, 0, tzinfo=UTC)


def entry(
    identifier: str = "memory-1",
    *,
    agent: str = "analyst",
    execution: str = "execution-1",
    workflow: str | None = "run-1",
    category: MemoryCategory = MemoryCategory.FACT,
    importance: MemoryImportance = MemoryImportance.NORMAL,
    content: str = "Confirmed requirement",
    metadata=None,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
) -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(value=identifier),
        agent_id=AgentId(value=agent),
        execution_id=execution,
        workflow_execution_id=workflow,
        category=category,
        importance=importance,
        content=content,
        metadata=metadata or {},
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
    )


def stores(tmp_path: Path):
    return (
        InMemoryMemoryStore(),
        SQLiteMemoryStore(tmp_path / "memory.db"),
    )


def test_memory_entry_is_immutable_serializable_and_validated() -> None:
    model = entry()

    assert model.model_dump(mode="json")["importance"] == 2
    assert "Confirmed requirement" not in repr(model)
    with pytest.raises(ValueError):
        model.content = "changed"
    with pytest.raises(ValueError):
        entry(created_at=datetime(2026, 7, 30))
    with pytest.raises(ValueError):
        entry(expires_at=NOW)


def test_memory_enums_and_policy_contract() -> None:
    assert {item.value for item in MemoryCategory} == {
        "fact",
        "decision",
        "observation",
        "plan",
        "task",
        "error",
        "result",
        "system",
        "custom",
    }
    assert MemoryImportance.CRITICAL > MemoryImportance.HIGH
    with pytest.raises(ValueError):
        MemoryRetentionPolicy(max_entries=0)
    with pytest.raises(ValueError):
        MemoryRetentionPolicy(max_context_size=0)


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_store_crud_and_persistence(
    backend: str, tmp_path: Path
) -> None:
    store = (
        InMemoryMemoryStore()
        if backend == "memory"
        else SQLiteMemoryStore(tmp_path / "memory.db")
    )
    original = entry()
    store.save(original)

    assert store.get(original.memory_id) == original
    assert store.count() == store.count(original.agent_id) == 1

    updated = original.model_copy(
        update={"content": "Updated", "updated_at": NOW + timedelta(seconds=1)}
    )
    store.update(updated)
    assert store.get(original.memory_id).content == "Updated"

    if backend == "sqlite":
        reopened = SQLiteMemoryStore(tmp_path / "memory.db")
        assert reopened.get(original.memory_id).content == "Updated"

    store.delete(original.memory_id)
    assert store.count() == 0
    with pytest.raises(MemoryNotFoundError):
        store.get(original.memory_id)


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_store_rejects_duplicates_and_missing_mutations(
    backend: str, tmp_path: Path
) -> None:
    store = (
        InMemoryMemoryStore()
        if backend == "memory"
        else SQLiteMemoryStore(tmp_path / "memory.db")
    )
    store.save(entry())
    with pytest.raises(MemoryAlreadyExistsError):
        store.save(entry())
    with pytest.raises(MemoryNotFoundError):
        store.update(entry("missing"))
    with pytest.raises(MemoryNotFoundError):
        store.delete(MemoryId(value="missing"))


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_store_queries_and_clear(backend: str, tmp_path: Path) -> None:
    store = (
        InMemoryMemoryStore()
        if backend == "memory"
        else SQLiteMemoryStore(tmp_path / "memory.db")
    )
    first = entry(
        "a",
        category=MemoryCategory.DECISION,
        content="Use SQLite locally",
        metadata={"domain": "storage"},
    )
    second = entry(
        "b",
        agent="reviewer",
        execution="execution-2",
        workflow="run-2",
        content="Review passed",
    )
    store.save(second)
    store.save(first)

    assert store.find_by_agent(first.agent_id) == (first,)
    assert store.find_by_execution("execution-2") == (second,)
    assert store.search(
        MemoryQuery(
            category=MemoryCategory.DECISION,
            text="sqlite",
            execution_id="execution-1",
            workflow_execution_id="run-1",
            metadata={"domain": "storage"},
        )
    ) == (first,)
    assert store.clear(first.agent_id) == 1
    assert store.count() == 1
    assert store.clear() == 1


def test_sqlite_schema_contains_memory_indexes(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "memory.db"
    SQLiteMemoryStore(path)
    connection = sqlite3.connect(path)
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
            )
        }
    finally:
        connection.close()
    assert {
        "memory_entries",
        "idx_memory_entries_agent",
        "idx_memory_entries_execution",
        "idx_memory_entries_workflow",
    } <= names


def test_basic_in_memory_search_performance() -> None:
    store = InMemoryMemoryStore()
    started = perf_counter()
    for index in range(250):
        store.save(entry(f"memory-{index}", content=f"item {index}"))
    results = store.search(MemoryQuery(text="item 24"))

    assert len(results) == 11
    assert perf_counter() - started < 5
