from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.api import create_app, create_default_app
from asep.application import ProjectService, RunQueryService
from asep.configuration import ApplicationSettings, StorageBackend
from asep.metrics import MetricsService
from asep.repositories import RepositoryFactory
from asep.projects import InMemoryProjectRepository
from asep.projects import SessionMemoryEntry, SessionMemoryKind
from datetime import UTC, datetime
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository

PATH = "/api/v1/projects/{project}/sessions/{session}/memory/search"


def create_project(client: TestClient, workspace: Path, name: str = "Project") -> str:
    response = client.post("/api/v1/projects", json={
        "name": name, "workspace_path": str(workspace),
    })
    assert response.status_code == 201
    return response.json()["project_id"]


def create_session(client: TestClient, project: str, title: str = "Session") -> str:
    response = client.post(f"/api/v1/projects/{project}/sessions", json={"title": title})
    assert response.status_code == 201
    return response.json()["session_id"]


def add_memory(
    client: TestClient, project: str, session: str, kind: str, content: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/projects/{project}/sessions/{session}/memory",
        json={"kind": kind, "content": content},
    )
    assert response.status_code == 201
    return response.json()


def url(project: str, session: str) -> str:
    return PATH.format(project=project, session=session)


def populated_client(tmp_path: Path):
    client = TestClient(create_default_app(ApplicationSettings()))
    project = create_project(client, tmp_path)
    session = create_session(client, project)
    return client, project, session


def test_basic_empty_endpoint_and_legacy_contracts_remain_compatible(tmp_path: Path) -> None:
    client, project, session = populated_client(tmp_path)
    assert client.get(url(project, session)).json() == {
        "items": [], "next_cursor": None,
    }
    created = add_memory(client, project, session, "fact", "Known fact")
    legacy = client.get(f"/api/v1/projects/{project}/sessions/{session}/memory")
    assert legacy.status_code == 200
    assert legacy.json() == {"items": [created]}
    assert set(client.get(url(project, session)).json()) == {"items", "next_cursor"}


@pytest.mark.parametrize(
    ("kind", "content"),
    (
        ("decision", "Decision content"),
        ("constraint", "Constraint content"),
        ("fact", "Fact content"),
        ("artifact", "Artifact content"),
        ("goal", "Goal content"),
    ),
)
def test_every_kind_is_publicly_filterable(
    tmp_path: Path, kind: str, content: str,
) -> None:
    client, project, session = populated_client(tmp_path)
    add_memory(client, project, session, kind, content)
    response = client.get(url(project, session), params={"kind": kind})
    assert response.status_code == 200
    assert [(item["kind"], item["content"]) for item in response.json()["items"]] == [
        (kind, content),
    ]


def test_text_casefold_whitespace_special_characters_and_combined_kind(tmp_path: Path) -> None:
    client, project, session = populated_client(tmp_path)
    add_memory(client, project, session, "constraint", "Use PostgreSQL %_';-- Safely")
    add_memory(client, project, session, "fact", "Use PostgreSQL elsewhere")
    response = client.get(url(project, session), params={
        "text": " postgresql   %_';-- ", "kind": "constraint",
    })
    assert response.status_code == 200
    assert [item["content"] for item in response.json()["items"]] == [
        "Use PostgreSQL %_';-- Safely",
    ]


def test_order_and_cursor_pagination_have_no_duplicates_or_omissions(tmp_path: Path) -> None:
    client, project, session = populated_client(tmp_path)
    created = [
        add_memory(client, project, session, "fact", f"Memory {index}")
        for index in range(4)
    ]
    newest = client.get(url(project, session), params={"order": "newest"}).json()["items"]
    oldest = client.get(url(project, session), params={"order": "oldest"}).json()["items"]
    assert [item["memory_id"] for item in newest] == [
        item["memory_id"] for item in reversed(created)
    ]
    assert [item["memory_id"] for item in oldest] == [item["memory_id"] for item in created]

    identifiers: list[str] = []
    cursor = None
    while True:
        params = {"page_size": 1}
        if cursor is not None:
            params["cursor"] = cursor
        page = client.get(url(project, session), params=params)
        assert page.status_code == 200
        identifiers.extend(item["memory_id"] for item in page.json()["items"])
        cursor = page.json()["next_cursor"]
        if cursor is None:
            break
    assert identifiers == [item["memory_id"] for item in reversed(created)]
    assert len(set(identifiers)) == len(created)


@pytest.mark.parametrize("page_size", (1, 100))
def test_valid_page_size_and_default_are_exposed(
    tmp_path: Path, page_size: int,
) -> None:
    client, project, session = populated_client(tmp_path)
    assert client.get(url(project, session), params={"page_size": page_size}).status_code == 200
    operation = client.app.openapi()["paths"][
        "/api/v1/projects/{project_id}/sessions/{session_id}/memory/search"
    ]["get"]
    parameter = next(item for item in operation["parameters"] if item["name"] == "page_size")
    assert parameter["schema"]["default"] == 25
    assert parameter["schema"]["minimum"] == 1
    assert parameter["schema"]["maximum"] == 100


@pytest.mark.parametrize(
    "params",
    ({"page_size": 0}, {"page_size": 101}, {"text": "   "}, {"cursor": "   "}),
)
def test_invalid_query_parameters_return_422(tmp_path: Path, params: dict[str, object]) -> None:
    client, project, session = populated_client(tmp_path)
    response = client.get(url(project, session), params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def cursor_fixture(tmp_path: Path):
    client, project, session = populated_client(tmp_path)
    add_memory(client, project, session, "fact", "Shared text one")
    add_memory(client, project, session, "fact", "Shared text two")
    params = {"text": "shared", "kind": "fact", "page_size": 1}
    cursor = client.get(url(project, session), params=params).json()["next_cursor"]
    assert cursor
    return client, project, session, params, cursor


def test_malformed_cursor_is_safe_400(tmp_path: Path) -> None:
    client, project, session = populated_client(tmp_path)
    response = client.get(url(project, session), params={"cursor": "malformed"})
    assert response.status_code == 400
    assert response.json() == {"error": {
        "code": "SESSION_MEMORY_CURSOR_INVALID",
        "message": "Session memory cursor is invalid.",
    }}


@pytest.mark.parametrize("change", ("project", "session", "text", "kind", "order"))
def test_incompatible_cursor_is_safe_400(tmp_path: Path, change: str) -> None:
    client, project, session, params, cursor = cursor_fixture(tmp_path)
    other_project = create_project(client, tmp_path, "Other")
    other_session = create_session(client, other_project, "Other")
    same_project_session = create_session(client, project, "Second")
    target_project, target_session = project, session
    changed = {**params, "cursor": cursor}
    if change == "project":
        target_project, target_session = other_project, other_session
    elif change == "session":
        target_session = same_project_session
    elif change == "text":
        changed["text"] = "different"
    elif change == "kind":
        changed["kind"] = "goal"
    else:
        changed["order"] = "oldest"
    response = client.get(url(target_project, target_session), params=changed)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SESSION_MEMORY_CURSOR_INVALID"


def test_project_session_and_cross_project_errors_are_safe(tmp_path: Path) -> None:
    client, project, session = populated_client(tmp_path)
    other_project = create_project(client, tmp_path, "Other")
    missing = client.get(url(project, "missing"))
    cross_project = client.get(url(other_project, session))
    unknown_project = client.get(url("missing", session))
    assert missing.status_code == cross_project.status_code == 404
    assert missing.json() == cross_project.json()
    assert unknown_project.status_code == 404
    assert unknown_project.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_project_and_session_isolation(tmp_path: Path) -> None:
    client, project, session = populated_client(tmp_path)
    second_session = create_session(client, project, "Second")
    other_project = create_project(client, tmp_path, "Other")
    other_session = create_session(client, other_project, "Other")
    owned = add_memory(client, project, session, "fact", "owned")
    add_memory(client, project, second_session, "fact", "other session")
    add_memory(client, other_project, other_session, "fact", "other project")
    assert client.get(url(project, session)).json()["items"] == [owned]


class FailingSearchService:
    def search(self, request):
        raise RuntimeError("private database detail")


def custom_client(service) -> TestClient:
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    return TestClient(create_app(
        query,
        MetricsService(query),
        project_service=ProjectService(InMemoryProjectRepository()),
        session_memory_search_service=service,
    ), raise_server_exceptions=False)


def test_unexpected_failure_is_generic_500() -> None:
    response = custom_client(FailingSearchService()).get(
        "/api/v1/projects/p/sessions/s/memory/search"
    )
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "INTERNAL_SERVER_ERROR", "message": "Internal server error.",
    }}
    assert "private" not in response.text


def test_openapi_and_public_dto_are_exact(tmp_path: Path) -> None:
    client, _, _ = populated_client(tmp_path)
    schema = client.app.openapi()
    path = "/api/v1/projects/{project_id}/sessions/{session_id}/memory/search"
    operation = schema["paths"][path]["get"]
    assert set(operation["responses"]) == {"200", "400", "404", "422", "500"}
    envelope = schema["components"]["schemas"]["SessionMemorySearchResponse"]["properties"]
    item = schema["components"]["schemas"]["SessionMemoryResponse"]["properties"]
    assert set(envelope) == {"items", "next_cursor"}
    assert set(item) == {
        "memory_id", "project_id", "session_id", "kind", "content",
        "source_execution_id", "created_at",
    }
    serialized = str(envelope).casefold()
    for forbidden in ("total_count", "score", "ranking", "embedding", "storage", "repository"):
        assert forbidden not in serialized
    legacy = schema["paths"][
        "/api/v1/projects/{project_id}/sessions/{session_id}/memory"
    ]["get"]
    assert legacy["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/SessionMemoryListResponse"
    )


def test_route_imports_only_api_application_and_standard_modules() -> None:
    from asep.api import project_routes

    imported = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(project_routes)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported <= {
        "pathlib", "typing", "fastapi", "asep.api.project_schemas",
        "asep.api.schemas", "asep.application",
    }
    assert not any(name.startswith((
        "asep.projects", "asep.repositories", "asep.sqlite", "asep.memory",
    )) for name in imported)


def test_default_composition_uses_one_bundle_and_shares_legacy_search_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = RepositoryFactory.create
    bundles = []

    def recorded(factory):
        bundle = original(factory)
        bundles.append(bundle)
        return bundle

    monkeypatch.setattr(RepositoryFactory, "create", recorded)
    client = TestClient(create_default_app(ApplicationSettings()))
    assert len(bundles) == 1
    assert bundles[0].session_memory_repository is bundles[0].session_memory_query_source
    project = create_project(client, tmp_path)
    session = create_session(client, project)
    created = add_memory(client, project, session, "fact", "shared")
    assert client.get(url(project, session)).json()["items"] == [created]


def test_independent_default_compositions_are_isolated(tmp_path: Path) -> None:
    first = TestClient(create_default_app(ApplicationSettings()))
    second = TestClient(create_default_app(ApplicationSettings()))
    project = create_project(first, tmp_path)
    session = create_session(first, project)
    add_memory(first, project, session, "fact", "first only")
    assert second.get(url(project, session)).status_code == 404


def test_orphan_memory_does_not_authorize_unknown_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = RepositoryFactory.create
    bundles = []

    def recorded(factory):
        bundle = original(factory)
        bundles.append(bundle)
        return bundle

    monkeypatch.setattr(RepositoryFactory, "create", recorded)
    client = TestClient(create_default_app(ApplicationSettings()))
    project = create_project(client, tmp_path)
    bundles[0].session_memory_repository.add(SessionMemoryEntry(
        memory_id="orphan",
        project_id=project,
        session_id="unknown-session",
        kind=SessionMemoryKind.FACT,
        content="orphan",
        created_at=datetime(2026, 8, 12, tzinfo=UTC),
    ))
    response = client.get(url(project, "unknown-session"))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_SESSION_NOT_FOUND"


def test_sqlite_search_survives_new_composition(tmp_path: Path) -> None:
    settings = ApplicationSettings(
        storage_backend=StorageBackend.SQLITE,
        sqlite_database=tmp_path / "asep.db",
    )
    first = TestClient(create_default_app(settings))
    project = create_project(first, tmp_path)
    session = create_session(first, project)
    created = add_memory(first, project, session, "fact", "persisted")
    second = TestClient(create_default_app(settings))
    assert second.get(url(project, session)).json()["items"] == [created]
