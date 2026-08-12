from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.configuration import ApplicationSettings, StorageBackend
from asep.projects import (
    DEFAULT_SESSION_MEMORY_PAGE_SIZE,
    MAX_SESSION_MEMORY_PAGE_SIZE,
    InMemorySessionMemoryRepository,
    InvalidSessionMemoryCursorError,
    ProjectSession,
    SQLiteProjectRepository,
    SQLiteProjectSessionRepository,
    SQLiteSessionMemoryRepository,
    SessionMemoryEntry,
    SessionMemoryKind,
    SessionMemoryOrder,
    SessionMemoryPage,
    SessionMemoryQuery,
    SessionMemoryQuerySource,
    WorkspaceProject,
)
from asep.repositories import RepositoryFactory

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def entry(
    memory_id: str,
    *,
    project_id: str = "project-1",
    session_id: str = "session-1",
    kind: SessionMemoryKind = SessionMemoryKind.FACT,
    content: str | None = None,
    offset: int = 0,
) -> SessionMemoryEntry:
    return SessionMemoryEntry(
        memory_id=memory_id,
        project_id=project_id,
        session_id=session_id,
        kind=kind,
        content=content or f"Confirmed architecture {memory_id}",
        created_at=NOW + timedelta(seconds=offset),
    )


def query_source(tmp_path: Path, backend: str):
    if backend == "memory":
        return InMemorySessionMemoryRepository()
    path = tmp_path / "asep.db"
    projects = SQLiteProjectRepository(path)
    sessions = SQLiteProjectSessionRepository(path)
    for project_id in ("project-1", "project-2"):
        projects.save(WorkspaceProject(
            project_id=project_id,
            name=project_id,
            workspace_path=tmp_path,
            created_at=NOW,
            updated_at=NOW,
        ))
    for session_id, project_id in (
        ("session-1", "project-1"),
        ("session-2", "project-1"),
        ("foreign-session", "project-2"),
    ):
        sessions.create(ProjectSession(
            session_id=session_id,
            project_id=project_id,
            title=session_id,
            created_at=NOW,
            updated_at=NOW,
        ))
    return SQLiteSessionMemoryRepository(path)


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
def test_contract_defaults_are_frozen_and_query_source_is_structural(
    tmp_path: Path,
    backend: str,
) -> None:
    query = SessionMemoryQuery(project_id=" project-1 ", session_id="session-1")
    assert query.project_id == "project-1"
    assert query.order is SessionMemoryOrder.NEWEST
    assert query.page_size == DEFAULT_SESSION_MEMORY_PAGE_SIZE == 25
    assert MAX_SESSION_MEMORY_PAGE_SIZE == 100
    assert isinstance(query_source(tmp_path, backend), SessionMemoryQuerySource)
    with pytest.raises(ValidationError):
        query.page_size = 2  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SessionMemoryPage().next_cursor = "x"  # type: ignore[misc]


@pytest.mark.parametrize(
    "values",
    (
        {"project_id": "", "session_id": "session"},
        {"project_id": "project", "session_id": " "},
        {"project_id": "project", "session_id": "session", "text": "  "},
        {"project_id": "project", "session_id": "session", "page_size": 0},
        {"project_id": "project", "session_id": "session", "page_size": 101},
        {"project_id": "project", "session_id": "session", "order": "random"},
        {"project_id": "project", "session_id": "session", "cursor": " "},
    ),
)
def test_contract_rejects_invalid_values(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SessionMemoryQuery.model_validate(values)


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
def test_text_search_normalization_special_characters_and_none(
    tmp_path: Path,
    backend: str,
) -> None:
    repository = query_source(tmp_path, backend)
    repository.add(entry("one", content="  Use   PostgreSQL %_';-- Safely  "))
    repository.add(entry("two", content="Unrelated"))

    found = repository.query(SessionMemoryQuery(
        project_id="project-1",
        session_id="session-1",
        text=" postgresql   %_';-- ",
    ))
    assert [item.memory_id for item in found.items] == ["one"]
    assert repository.query(SessionMemoryQuery(
        project_id="project-1", session_id="session-1", text="MISSING"
    )).items == ()
    assert len(repository.query(SessionMemoryQuery(
        project_id="project-1", session_id="session-1", text=None
    )).items) == 2


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
@pytest.mark.parametrize("kind", list(SessionMemoryKind))
def test_every_kind_and_combined_text_filter(
    tmp_path: Path,
    backend: str,
    kind: SessionMemoryKind,
) -> None:
    repository = query_source(tmp_path, backend)
    repository.add(entry(kind.value, kind=kind, content=f"Shared {kind.value}"))
    other = next(item for item in SessionMemoryKind if item is not kind)
    repository.add(entry(f"other-{kind.value}", kind=other, content="Shared"))
    result = repository.query(SessionMemoryQuery(
        project_id="project-1",
        session_id="session-1",
        kind=kind,
        text=kind.value.upper(),
    ))
    assert [item.memory_id for item in result.items] == [kind.value]


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
def test_project_session_isolation_and_orphans_do_not_cross_scope(
    tmp_path: Path,
    backend: str,
) -> None:
    repository = query_source(tmp_path, backend)
    repository.add(entry("owned"))
    repository.add(entry("other-session", session_id="session-2"))
    repository.add(entry(
        "other-project",
        project_id="project-2",
        session_id="foreign-session",
    ))
    assert [item.memory_id for item in repository.query(SessionMemoryQuery(
        project_id="project-1", session_id="session-1"
    )).items] == ["owned"]
    assert repository.query(SessionMemoryQuery(
        project_id="project-2", session_id="session-1"
    )).items == ()


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
@pytest.mark.parametrize(
    ("order", "expected"),
    (
        (SessionMemoryOrder.NEWEST, ["later", "same-b", "same-a"]),
        (SessionMemoryOrder.OLDEST, ["same-a", "same-b", "later"]),
    ),
)
def test_total_deterministic_ordering(
    tmp_path: Path,
    backend: str,
    order: SessionMemoryOrder,
    expected: list[str],
) -> None:
    repository = query_source(tmp_path, backend)
    repository.add(entry("same-b"))
    repository.add(entry("later", offset=1))
    repository.add(entry("same-a"))
    query = SessionMemoryQuery(
        project_id="project-1", session_id="session-1", order=order
    )
    assert [item.memory_id for item in repository.query(query).items] == expected
    assert repository.query(query) == repository.query(query)


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
def test_timestamp_offsets_use_instant_then_memory_id(
    tmp_path: Path,
    backend: str,
) -> None:
    repository = query_source(tmp_path, backend)
    repository.add(entry("b"))
    shifted = entry("a").model_copy(update={
        "created_at": NOW.astimezone(timezone(timedelta(hours=-3)))
    })
    repository.add(shifted)
    assert [item.memory_id for item in repository.query(SessionMemoryQuery(
        project_id="project-1", session_id="session-1"
    )).items] == ["b", "a"]


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
def test_cursor_pages_have_no_duplicates_or_omissions_and_resist_newer_insert(
    tmp_path: Path,
    backend: str,
) -> None:
    repository = query_source(tmp_path, backend)
    for index in range(4):
        repository.add(entry(f"m-{index}", offset=index))
    query = SessionMemoryQuery(
        project_id="project-1", session_id="session-1", page_size=1
    )
    first = repository.query(query)
    assert [item.memory_id for item in first.items] == ["m-3"]
    assert first.next_cursor is not None
    repository.add(entry("newer", offset=10))

    collected = list(first.items)
    cursor = first.next_cursor
    while cursor is not None:
        page = repository.query(query.model_copy(update={"cursor": cursor}))
        collected.extend(page.items)
        cursor = page.next_cursor
    assert [item.memory_id for item in collected] == ["m-3", "m-2", "m-1", "m-0"]
    assert len({item.memory_id for item in collected}) == 4


@pytest.mark.parametrize("backend", ("memory", "sqlite"))
def test_malformed_and_mismatched_cursors_are_typed(
    tmp_path: Path,
    backend: str,
) -> None:
    repository = query_source(tmp_path, backend)
    repository.add(entry("one")); repository.add(entry("two", offset=1))
    base = SessionMemoryQuery(
        project_id="project-1", session_id="session-1", page_size=1
    )
    cursor = repository.query(base).next_cursor
    assert cursor is not None
    with pytest.raises(InvalidSessionMemoryCursorError):
        repository.query(base.model_copy(update={"cursor": "not-a-cursor"}))
    with pytest.raises(InvalidSessionMemoryCursorError):
        repository.query(base.model_copy(update={
            "cursor": cursor,
            "order": SessionMemoryOrder.OLDEST,
        }))


def test_sqlite_query_survives_repository_reconstruction(tmp_path: Path) -> None:
    repository = query_source(tmp_path, "sqlite")
    repository.add(entry("one", content="Persisted query"))
    restarted = SQLiteSessionMemoryRepository(tmp_path / "asep.db")
    assert [item.memory_id for item in restarted.query(SessionMemoryQuery(
        project_id="project-1", session_id="session-1", text="QUERY"
    )).items] == ["one"]


@pytest.mark.parametrize("backend", list(StorageBackend))
def test_factory_shares_command_query_source_and_compositions_are_isolated(
    tmp_path: Path,
    backend: StorageBackend,
) -> None:
    settings = ApplicationSettings(
        storage_backend=backend,
        storage_directory=tmp_path / backend.value,
        sqlite_database=tmp_path / f"{backend.value}.db",
    )
    first = RepositoryFactory(settings).create()
    second = RepositoryFactory(settings).create()
    assert first.session_memory_query_source is first.session_memory_repository
    assert second.session_memory_query_source is second.session_memory_repository
    if backend is not StorageBackend.SQLITE:
        assert isinstance(
            first.session_memory_repository,
            InMemorySessionMemoryRepository,
        )
        assert first.session_memory_repository is not second.session_memory_repository


def test_sqlite_compositions_with_distinct_databases_are_isolated(
    tmp_path: Path,
) -> None:
    first = RepositoryFactory(ApplicationSettings(
        storage_backend=StorageBackend.SQLITE,
        sqlite_database=tmp_path / "first.db",
    )).create()
    second = RepositoryFactory(ApplicationSettings(
        storage_backend=StorageBackend.SQLITE,
        sqlite_database=tmp_path / "second.db",
    )).create()
    assert first.session_memory_repository is not second.session_memory_repository
    assert first.session_memory_query_source is first.session_memory_repository
    assert second.session_memory_query_source is second.session_memory_repository


def test_factory_command_write_is_immediately_queryable(tmp_path: Path) -> None:
    bundle = RepositoryFactory(ApplicationSettings()).create()
    bundle.session_memory_repository.add(entry("shared"))
    assert [item.memory_id for item in bundle.session_memory_query_source.query(
        SessionMemoryQuery(project_id="project-1", session_id="session-1")
    ).items] == ["shared"]
