from datetime import UTC, datetime, timedelta

import pytest

from asep.agents import AgentId
from asep.memory import (
    ContextBuildRequest,
    ContextBuilder,
    InMemoryMemoryMetrics,
    InMemoryMemoryStore,
    MemoryCategory,
    MemoryEntry,
    MemoryFilter,
    MemoryId,
    MemoryImportance,
    MemoryNotFoundError,
    MemoryQuery,
    MemoryRetentionPolicy,
    MemoryService,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
    TimelineRecorder,
)

NOW = datetime(2026, 7, 30, 15, 0, tzinfo=UTC)


class Clock:
    def __init__(self, *values: datetime) -> None:
        self.values = iter(values)

    def __call__(self) -> datetime:
        return next(self.values)


class Timer:
    def __init__(self, *values: float) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


def memory(
    identifier: str = "memory-1",
    *,
    content: str = "safe content",
    importance: MemoryImportance = MemoryImportance.NORMAL,
    created_at: datetime = NOW,
    expires_at: datetime | None = None,
    metadata=None,
) -> MemoryEntry:
    return MemoryEntry(
        memory_id=MemoryId(value=identifier),
        agent_id=AgentId(value="analyst"),
        execution_id="execution-1",
        workflow_execution_id="run-1",
        category=MemoryCategory.FACT,
        importance=importance,
        content=content,
        metadata=metadata or {},
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
    )


def service(
    *,
    policy: MemoryRetentionPolicy | None = None,
    clock=None,
):
    store = InMemoryMemoryStore()
    repository = InMemoryTimelineRepository()
    timeline = TimelineRecorder(repository)
    metrics = InMemoryMemoryMetrics()
    instance = MemoryService(
        store,
        timeline=timeline,
        metrics=metrics,
        policy=policy,
        clock=clock,
    )
    return instance, store, repository, metrics, timeline


def test_filter_removes_sensitive_metadata_and_redacts_content() -> None:
    filtered_content, filtered_metadata, changed = MemoryFilter().sanitize(
        "password=\"hunter two\" token:abc Bearer bearer-token "
        "-----BEGIN PRIVATE KEY-----key-----END PRIVATE KEY----- safe",
        {
            "authorization": "Bearer abc",
            "headers": {
                "cookie": "session",
                "content-type": "application/json",
            },
            "nested": {"private_key": "key", "safe": "value"},
        },
    )

    assert "hunter2" not in filtered_content
    assert "hunter two" not in filtered_content
    assert "abc" not in filtered_content
    assert "bearer-token" not in filtered_content
    assert "-----BEGIN PRIVATE KEY-----" not in filtered_content
    assert filtered_metadata == {
        "headers": {"content-type": "application/json"},
        "nested": {"safe": "value"},
    }
    assert changed


def test_save_filters_before_store_and_records_events() -> None:
    instance, store, timeline, metrics, _ = service()

    saved = instance.save(
        memory(
            content="api_key=credential",
            metadata={"secret": "credential", "safe": "kept"},
        )
    )

    assert "credential" not in saved.content
    assert saved.metadata == {"safe": "kept"}
    assert store.get(saved.memory_id) == saved
    assert [event.type for event in timeline.list_by_run("run-1")] == [
        TimelineEventType.MEMORY_FILTERED,
        TimelineEventType.MEMORY_SAVED,
    ]
    snapshot = metrics.snapshot()
    assert snapshot.entries_total == snapshot.writes_total == 1


def test_update_load_remove_and_metrics() -> None:
    instance, _, timeline, metrics, _ = service(
        clock=Clock(
            NOW + timedelta(seconds=1),
            NOW + timedelta(seconds=2),
            NOW + timedelta(seconds=3),
        )
    )
    original = instance.save(memory())
    updated = instance.update(
        original,
        content="decision",
        importance=MemoryImportance.HIGH,
    )

    assert updated.content == "decision"
    assert instance.get(updated.memory_id) == updated
    instance.remove(updated.memory_id)
    with pytest.raises(MemoryNotFoundError):
        instance.get(updated.memory_id)

    snapshot = metrics.snapshot()
    assert snapshot.updates_total == snapshot.deletes_total == 1
    assert snapshot.hits_total == snapshot.misses_total == 1
    assert TimelineEventType.MEMORY_UPDATED in {
        event.type for event in timeline.list_by_run("run-1")
    }


def test_expiration_removes_entries_and_records_event() -> None:
    instance, store, timeline, metrics, _ = service(
        clock=Clock(NOW + timedelta(seconds=2))
    )
    store.save(memory(expires_at=NOW + timedelta(seconds=1)))

    assert instance.expire() == 1
    assert store.count() == 0
    assert metrics.snapshot().deletes_total == 1
    assert timeline.list_by_run("run-1")[-1].type is (
        TimelineEventType.MEMORY_EXPIRED
    )


def test_default_expiration_and_retention_remove_low_priority() -> None:
    policy = MemoryRetentionPolicy(
        max_entries=2,
        expiration_seconds=60,
        remove_low_priority=True,
    )
    instance, store, _, metrics, _ = service(policy=policy)
    low = instance.save(memory("low", importance=MemoryImportance.LOW))
    instance.save(memory("critical", importance=MemoryImportance.CRITICAL))
    instance.save(memory("normal", importance=MemoryImportance.NORMAL))

    assert low.expires_at == NOW + timedelta(seconds=60)
    assert store.count() == 2
    with pytest.raises(MemoryNotFoundError):
        store.get(low.memory_id)
    assert metrics.snapshot().deletes_total == 1


def test_search_summary_clear_and_miss_metrics() -> None:
    instance, _, _, metrics, _ = service()
    instance.save(memory("a", content="first"))
    instance.save(memory("b", content="second"))

    assert len(
        instance.search(
            MemoryQuery(agent_id=AgentId(value="analyst"), text="first")
        )
    ) == 1
    assert instance.search(MemoryQuery(text="missing")) == ()
    assert "[fact] first" in instance.summarize(AgentId(value="analyst"))
    assert instance.clear(AgentId(value="analyst")) == 2
    assert metrics.snapshot().misses_total == 1


def test_context_builder_orders_filters_limits_and_observes() -> None:
    policy = MemoryRetentionPolicy(max_context_size=230)
    instance, _, repository, metrics, timeline = service(policy=policy)
    instance.save(
        memory(
            "low",
            content="low " * 30,
            importance=MemoryImportance.LOW,
        )
    )
    instance.save(
        memory(
            "critical",
            content="critical",
            importance=MemoryImportance.CRITICAL,
        )
    )
    builder = ContextBuilder(
        instance,
        timeline=timeline,
        timer=Timer(10.0, 10.25),
    )

    result = builder.build(
        ContextBuildRequest(
            agent_id=AgentId(value="analyst"),
            execution_id="execution-2",
            workflow_execution_id="run-1",
            workflow_context={
                "objective": "review",
                "token": "workflow-secret",
            },
            metadata={"password": "metadata-secret", "safe": "kept"},
        )
    )

    assert result.memories[0].memory_id == MemoryId(value="critical")
    assert result.truncated
    assert result.context["metadata"] == {"safe": "kept"}
    assert "workflow-secret" not in repr(result.context)
    assert result.duration_seconds == 0.25
    assert metrics.snapshot().context_build_duration == (0.25,)
    assert repository.list_by_run("run-1")[-1].type is (
        TimelineEventType.CONTEXT_BUILT
    )
