from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.application import (
    ProjectService,
    ProjectSessionMemoryService,
    ProjectSessionService,
    SessionMemorySearchItem,
    SessionMemorySearchPage,
    SessionMemorySearchRequest,
    SessionMemorySearchService,
)
from asep.configuration import ApplicationSettings, StorageBackend
from asep.errors import ProjectNotFoundError, ProjectSessionNotFoundError
from asep.projects import (
    DEFAULT_SESSION_MEMORY_PAGE_SIZE,
    MAX_SESSION_MEMORY_PAGE_SIZE,
    InvalidSessionMemoryCursorError,
    SessionMemoryEntry,
    SessionMemoryKind,
    SessionMemoryOrder,
    SessionMemoryQuerySource,
)
from asep.repositories import RepositoryFactory

NOW = datetime(2026, 8, 12, 12, tzinfo=UTC)


def composition(tmp_path: Path, backend: StorageBackend = StorageBackend.MEMORY):
    tmp_path.mkdir(parents=True, exist_ok=True)
    settings = ApplicationSettings(
        storage_backend=backend,
        storage_directory=tmp_path / backend.value,
        sqlite_database=tmp_path / f"{backend.value}.db",
    )
    bundle = RepositoryFactory(settings).create()
    projects = ProjectService(
        bundle.project_repository,
        clock=lambda: NOW,
        id_generator=iter(("project-1", "project-2")).__next__,
    )
    sessions = ProjectSessionService(
        projects,
        bundle.project_session_repository,
        bundle.project_execution_repository,
        clock=lambda: NOW,
        id_generator=iter(("session-1", "session-2", "foreign-session")).__next__,
    )
    project_one = projects.create("One", tmp_path)
    project_two = projects.create("Two", tmp_path)
    session_one = sessions.create(project_one.project_id, "One")
    session_two = sessions.create(project_one.project_id, "Two")
    foreign = sessions.create(project_two.project_id, "Foreign")
    command = ProjectSessionMemoryService(
        projects,
        sessions,
        bundle.session_memory_repository,
        clock=lambda: NOW,
        id_generator=(f"memory-{index}" for index in range(100)).__next__,
    )
    search = SessionMemorySearchService(
        sessions,
        bundle.session_memory_query_source,
    )
    return bundle, projects, sessions, command, search, session_one, session_two, foreign


def request(**changes: object) -> SessionMemorySearchRequest:
    values: dict[str, object] = {
        "project_id": "project-1",
        "session_id": "session-1",
    }
    values.update(changes)
    return SessionMemorySearchRequest.model_validate(values)


def test_application_contracts_are_strict_frozen_and_bounded() -> None:
    value = request()
    assert value.page_size == DEFAULT_SESSION_MEMORY_PAGE_SIZE == 25
    assert MAX_SESSION_MEMORY_PAGE_SIZE == 100
    with pytest.raises(ValidationError):
        value.page_size = 2  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SessionMemorySearchRequest.model_validate({
            "project_id": "p", "session_id": "s", "page_size": "2",
        })
    for values in (
        {"project_id": "", "session_id": "s"},
        {"project_id": "p", "session_id": "   "},
        {"project_id": "p", "session_id": "s", "page_size": 0},
        {"project_id": "p", "session_id": "s", "page_size": 101},
    ):
        with pytest.raises(ValidationError):
            SessionMemorySearchRequest.model_validate(values)
    assert request(page_size=1).page_size == 1
    assert request(page_size=100).page_size == 100


def test_projection_contracts_are_strict_frozen_and_exact() -> None:
    item = SessionMemorySearchItem(
        memory_id="m", project_id="p", session_id="s",
        kind=SessionMemoryKind.FACT, content="fact", created_at=NOW,
    )
    page = SessionMemorySearchPage(items=(item,))
    assert set(item.model_dump()) == {
        "memory_id", "project_id", "session_id", "kind", "content",
        "source_execution_id", "created_at",
    }
    assert set(page.model_dump()) == {"items", "next_cursor"}
    with pytest.raises(ValidationError):
        item.content = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        page.next_cursor = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SessionMemorySearchPage(items=(item,), total_count=1)  # type: ignore[call-arg]


class RecordingSource:
    def __init__(self, delegate: SessionMemoryQuerySource) -> None:
        self.delegate = delegate
        self.calls = 0

    def query(self, query):
        self.calls += 1
        return self.delegate.query(query)


@pytest.mark.parametrize(
    ("project_id", "session_id", "error"),
    (
        ("missing", "session-1", ProjectNotFoundError),
        ("project-1", "missing", ProjectSessionNotFoundError),
        ("project-1", "foreign-session", ProjectSessionNotFoundError),
    ),
)
def test_ownership_failure_happens_before_query(
    tmp_path: Path, project_id: str, session_id: str, error: type[Exception],
) -> None:
    bundle, _, sessions, _, _, *_ = composition(tmp_path)
    source = RecordingSource(bundle.session_memory_query_source)
    service = SessionMemorySearchService(sessions, source)
    with pytest.raises(error):
        service.search(request(project_id=project_id, session_id=session_id))
    assert source.calls == 0


@pytest.mark.parametrize("backend", list(StorageBackend))
def test_owned_empty_session_and_shared_command_query_identity(
    tmp_path: Path, backend: StorageBackend,
) -> None:
    bundle, _, _, command, search, *_ = composition(tmp_path, backend)
    assert bundle.session_memory_repository is bundle.session_memory_query_source
    assert search.search(request()).items == ()
    created = command.add(
        "project-1", "session-1", SessionMemoryKind.FACT, "Known fact",
    )
    result = search.search(request())
    assert [item.memory_id for item in result.items] == [created.memory_id]
    assert isinstance(result.items[0], SessionMemorySearchItem)
    assert result.items[0] is not created


@pytest.mark.parametrize("backend", (StorageBackend.MEMORY, StorageBackend.SQLITE))
def test_text_kind_special_characters_and_backend_parity(
    tmp_path: Path, backend: StorageBackend,
) -> None:
    _, _, _, command, search, *_ = composition(tmp_path, backend)
    command.add(
        "project-1", "session-1", SessionMemoryKind.CONSTRAINT,
        "Use PostgreSQL %_';-- safely",
    )
    command.add(
        "project-1", "session-1", SessionMemoryKind.FACT,
        "Use PostgreSQL for reporting",
    )
    result = search.search(request(
        text=" postgresql   %_';-- ",
        kind=SessionMemoryKind.CONSTRAINT,
    ))
    assert [(item.kind, item.content) for item in result.items] == [(
        SessionMemoryKind.CONSTRAINT, "Use PostgreSQL %_';-- safely",
    )]


@pytest.mark.parametrize("backend", (StorageBackend.MEMORY, StorageBackend.SQLITE))
@pytest.mark.parametrize("kind", list(SessionMemoryKind))
def test_each_memory_kind(tmp_path: Path, backend: StorageBackend, kind: SessionMemoryKind) -> None:
    _, _, _, command, search, *_ = composition(tmp_path, backend)
    command.add("project-1", "session-1", kind, f"Content {kind.value}")
    assert [item.kind for item in search.search(request(kind=kind)).items] == [kind]


@pytest.mark.parametrize("backend", (StorageBackend.MEMORY, StorageBackend.SQLITE))
def test_total_order_and_cursor_pagination(tmp_path: Path, backend: StorageBackend) -> None:
    bundle, _, _, _, search, *_ = composition(tmp_path, backend)
    for memory_id, offset in (("a", 0), ("b", 0), ("c", 1), ("d", 2)):
        bundle.session_memory_repository.add(SessionMemoryEntry(
            memory_id=memory_id, project_id="project-1", session_id="session-1",
            kind=SessionMemoryKind.FACT, content=f"Content {memory_id}",
            created_at=NOW + timedelta(seconds=offset),
        ))
    newest = search.search(request(order=SessionMemoryOrder.NEWEST))
    oldest = search.search(request(order=SessionMemoryOrder.OLDEST))
    assert [item.memory_id for item in newest.items] == ["d", "c", "b", "a"]
    assert [item.memory_id for item in oldest.items] == ["a", "b", "c", "d"]

    page_request = request(page_size=1)
    identifiers: list[str] = []
    cursor = None
    while True:
        page = search.search(page_request.model_copy(update={"cursor": cursor}))
        identifiers.extend(item.memory_id for item in page.items)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert identifiers == ["d", "c", "b", "a"]
    assert len(set(identifiers)) == len(identifiers)


@pytest.mark.parametrize("change", ("project", "session", "text", "kind", "order"))
def test_malformed_and_incompatible_cursors(tmp_path: Path, change: str) -> None:
    bundle, _, _, _, search, *_ = composition(tmp_path)
    for memory_id, offset in (("one", 0), ("two", 1)):
        bundle.session_memory_repository.add(SessionMemoryEntry(
            memory_id=memory_id, project_id="project-1", session_id="session-1",
            kind=SessionMemoryKind.FACT, content="Shared text",
            created_at=NOW + timedelta(seconds=offset),
        ))
    base = request(text="shared", kind=SessionMemoryKind.FACT, page_size=1)
    cursor = search.search(base).next_cursor
    assert cursor is not None
    changes = {
        "project": {"project_id": "project-2", "session_id": "foreign-session"},
        "session": {"session_id": "session-2"},
        "text": {"text": "different"},
        "kind": {"kind": SessionMemoryKind.GOAL},
        "order": {"order": SessionMemoryOrder.OLDEST},
    }
    with pytest.raises(InvalidSessionMemoryCursorError):
        search.search(base.model_copy(update={"cursor": cursor, **changes[change]}))
    with pytest.raises(InvalidSessionMemoryCursorError):
        search.search(base.model_copy(update={"cursor": "malformed"}))


def test_other_scopes_and_orphan_memory_cannot_authorize_session(tmp_path: Path) -> None:
    bundle, _, _, _, search, *_ = composition(tmp_path)
    for entry in (
        SessionMemoryEntry(memory_id="owned", project_id="project-1", session_id="session-1", kind=SessionMemoryKind.FACT, content="owned", created_at=NOW),
        SessionMemoryEntry(memory_id="session", project_id="project-1", session_id="session-2", kind=SessionMemoryKind.FACT, content="other", created_at=NOW),
        SessionMemoryEntry(memory_id="project", project_id="project-2", session_id="foreign-session", kind=SessionMemoryKind.FACT, content="other", created_at=NOW),
        SessionMemoryEntry(memory_id="orphan", project_id="project-1", session_id="orphan", kind=SessionMemoryKind.FACT, content="orphan", created_at=NOW),
    ):
        bundle.session_memory_repository.add(entry)
    assert [item.memory_id for item in search.search(request()).items] == ["owned"]
    with pytest.raises(ProjectSessionNotFoundError):
        search.search(request(session_id="orphan"))


def test_independent_memory_compositions_are_isolated(tmp_path: Path) -> None:
    first = composition(tmp_path / "first")
    second = composition(tmp_path / "second")
    first[3].add("project-1", "session-1", SessionMemoryKind.FACT, "first only")
    assert len(first[4].search(request()).items) == 1
    assert second[4].search(request()).items == ()


def test_sqlite_search_survives_repository_reconstruction(tmp_path: Path) -> None:
    first = composition(tmp_path, StorageBackend.SQLITE)
    first[3].add("project-1", "session-1", SessionMemoryKind.FACT, "persisted")
    settings = ApplicationSettings(
        storage_backend=StorageBackend.SQLITE,
        sqlite_database=tmp_path / "sqlite.db",
    )
    bundle = RepositoryFactory(settings).create()
    projects = ProjectService(bundle.project_repository)
    sessions = ProjectSessionService(
        projects, bundle.project_session_repository, bundle.project_execution_repository,
    )
    search = SessionMemorySearchService(sessions, bundle.session_memory_query_source)
    assert [item.content for item in search.search(request()).items] == ["persisted"]
