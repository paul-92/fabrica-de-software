from datetime import UTC, datetime, timedelta
import json
import sqlite3
import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from asep.access import AccessDeniedError, AccessService, InMemoryAccessRepository
from asep.access.models import Membership, Organization, OrganizationRole, User, UserStatus
from asep.api import create_app
from asep.application import ProjectService, ProjectSessionService, ProjectSessionMemoryService, ProjectWorkspaceService
from asep.metrics import MetricsService
from asep.projects import InMemoryProjectExecutionRepository, InMemoryProjectRepository, InMemoryProjectSessionRepository, InMemorySessionMemoryRepository, WorkspaceProject
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository
from asep.application import RunQueryService
from asep.projects import SQLiteProjectRepository
from asep.configuration import ApplicationSettings
from asep.configuration.errors import ConfigurationValidationError

NOW = datetime(2026, 8, 13, tzinfo=UTC)
pytestmark = pytest.mark.no_legacy_access


def access_fixture():
    repository = InMemoryAccessRepository()
    for org in ("tenant-a", "tenant-b"):
        repository.save_organization(Organization(organization_id=org, name=org, created_at=NOW))
        user = User(user_id=f"user-{org[-1]}", email=f"{org}@example.test", status=UserStatus.ACTIVE, created_at=NOW, updated_at=NOW)
        repository.save_user(user, AccessService.password_hash("private-beta-password"))
        repository.save_membership(Membership(organization_id=org, user_id=user.user_id, role=OrganizationRole.ADMIN, created_at=NOW))
    return repository, AccessService(repository, clock=lambda: NOW)


def app_fixture(tmp_path: Path):
    access_repository, access = access_fixture()
    projects_repository = InMemoryProjectRepository()
    for org in ("tenant-a", "tenant-b"):
        root = tmp_path / org; root.mkdir(); (root / "visible.txt").write_text(org)
        projects_repository.save(WorkspaceProject(project_id=f"project-{org[-1]}", organization_id=org, created_by_user_id=f"user-{org[-1]}", name=org, workspace_path=root, created_at=NOW, updated_at=NOW))
    projects = ProjectService(projects_repository)
    sessions_repository = InMemoryProjectSessionRepository(); executions = InMemoryProjectExecutionRepository()
    sessions = ProjectSessionService(projects, sessions_repository, executions, clock=lambda: NOW)
    memory = ProjectSessionMemoryService(projects, sessions, InMemorySessionMemoryRepository())
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    app = create_app(query, MetricsService(query), project_service=projects, project_session_service=sessions,
                     project_session_memory_service=memory, project_workspace_service=ProjectWorkspaceService(projects),
                     project_ai_runtime_execution_service=object(), project_engineering_execution_service=object(),
                     access_service=access)
    return TestClient(app), access_repository


def login(client: TestClient, tenant: str = "tenant-a"):
    response = client.post("/api/v1/access/login", json={"email": f"{tenant}@example.test", "password": "private-beta-password"})
    assert response.status_code == 200


def test_anonymous_and_cross_tenant_project_resources_are_fail_closed(tmp_path: Path):
    client, _ = app_fixture(tmp_path)
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/runs").status_code == 401
    login(client)
    assert [item["project_id"] for item in client.get("/api/v1/projects").json()["items"]] == ["project-a"]
    paths = [
        "/api/v1/projects/project-b", "/api/v1/projects/project-b/sessions",
        "/api/v1/projects/project-b/executions", "/api/v1/projects/project-b/executions/unknown",
        "/api/v1/projects/project-b/workspace", "/api/v1/projects/project-b/workspace/file?path=visible.txt",
        "/api/v1/projects/project-b/sessions/unknown/memory",
    ]
    for path in paths:
        assert client.get(path).status_code == 404, path


def test_cross_tenant_mutation_boundaries_are_not_reached(tmp_path: Path):
    client, _ = app_fixture(tmp_path); login(client)
    body = {"session_id": "unknown", "runtime_id": "codex", "instruction": "x", "execution_mode": "workspace_write"}
    for path in (
        "/api/v1/projects/project-b/engineering/prepare",
        "/api/v1/projects/project-b/engineering/prepared/approve",
        "/api/v1/projects/project-b/engineering/prepared/cancel",
    ):
        assert client.post(path, json=body).status_code == 404


def test_logout_invalid_session_and_suspension_revoke_access(tmp_path: Path):
    client, repository = app_fixture(tmp_path); login(client)
    assert client.post("/api/v1/access/logout").status_code == 200
    assert client.get("/api/v1/access/session").status_code == 401
    client.cookies.set("asep_session", "invalid")
    assert client.get("/api/v1/access/session").status_code == 401
    client.cookies.clear(); login(client)
    user, _password = repository.users["user-a"]
    repository.update_user(user.model_copy(update={"status": UserStatus.SUSPENDED, "updated_at": NOW}))
    assert client.get("/api/v1/projects").status_code == 401


def test_admin_invites_lists_and_reactivates_users(tmp_path: Path):
    client, _ = app_fixture(tmp_path); login(client)
    invited = client.post("/api/v1/access/users", json={"email": " Member@Example.Test ", "password": "member-beta-password", "role": "member"})
    assert invited.status_code == 201
    assert invited.json()["email"] == "member@example.test"
    user_id = invited.json()["user_id"]
    assert len(client.get("/api/v1/access/users").json()["items"]) == 2
    assert client.patch(f"/api/v1/access/users/{user_id}/status", json={"status": "suspended"}).json()["status"] == "suspended"
    assert client.patch(f"/api/v1/access/users/{user_id}/status", json={"status": "active"}).json()["status"] == "active"


def test_expired_session_is_rejected_and_removed():
    repository, access = access_fixture()
    token, _ = access.login("tenant-a@example.test", "private-beta-password")
    stored = repository.get_session_by_hash(access.token_hash(token))
    assert stored is not None
    repository.sessions[stored.token_hash] = stored.model_copy(update={"expires_at": NOW - timedelta(seconds=1)})
    with pytest.raises(AccessDeniedError):
        access.authenticate(token)
    assert repository.get_session_by_hash(access.token_hash(token)) is None


def test_sqlite_legacy_project_migrates_with_explicit_ownership(tmp_path: Path):
    database = tmp_path / "legacy.db"
    payload = {"project_id": "old", "name": "Old", "workspace_path": str(tmp_path), "created_at": NOW.isoformat(), "updated_at": NOW.isoformat()}
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
        connection.execute("INSERT INTO projects VALUES (?,?,?)", ("old", NOW.isoformat(), json.dumps(payload)))
    project = SQLiteProjectRepository(database).get_for_organization("legacy-local", "old")
    assert project.organization_id == "legacy-local"
    assert project.created_by_user_id == "legacy-local-admin"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM schema_metadata WHERE key='schema_version'").fetchone()[0] == "4"


def test_secure_cookie_configuration_rejects_default_admin_password():
    with pytest.raises(ConfigurationValidationError):
        ApplicationSettings(access_cookie_secure=True)
    configured = ApplicationSettings(access_cookie_secure=True, legacy_admin_password="explicit-private-beta-password")
    assert configured.access_cookie_secure is True
