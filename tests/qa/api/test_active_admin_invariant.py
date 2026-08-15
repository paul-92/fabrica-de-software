from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asep.access import (
    AccessService, InMemoryAccessRepository, LastActiveAdminError, Membership,
    Organization, OrganizationRole, RequestPrincipal, SQLiteAccessRepository,
    User, UserStatus,
)
from asep.api.access_routes import create_access_router


NOW = datetime(2026, 8, 15, tzinfo=UTC)


def repository(kind: str, tmp_path):
    return InMemoryAccessRepository() if kind == "memory" else SQLiteAccessRepository(tmp_path / "access.db")


def add(repo, organization_id: str, user_id: str, role: OrganizationRole, status: UserStatus = UserStatus.ACTIVE):
    repo.save_organization(Organization(organization_id=organization_id, name=organization_id, created_at=NOW))
    repo.save_user(User(user_id=user_id, email=f"{user_id}@example.test", status=status, created_at=NOW, updated_at=NOW), "bounded-hash")
    repo.save_membership(Membership(organization_id=organization_id, user_id=user_id, role=role, created_at=NOW))


@pytest.mark.parametrize("kind", ("memory", "sqlite"))
def test_only_active_admin_cannot_be_suspended_and_state_is_unchanged(kind, tmp_path):
    repo = repository(kind, tmp_path); add(repo, "org", "admin", OrganizationRole.ADMIN)
    with pytest.raises(LastActiveAdminError):
        repo.set_status_preserving_active_admin("org", "admin", UserStatus.SUSPENDED, NOW)
    assert repo.get_user("org", "admin").status is UserStatus.ACTIVE


@pytest.mark.parametrize("kind", ("memory", "sqlite"))
def test_active_admin_definition_is_tenant_scoped_and_excludes_members_and_suspended_admins(kind, tmp_path):
    repo = repository(kind, tmp_path)
    add(repo, "org-a", "target", OrganizationRole.ADMIN)
    add(repo, "org-a", "member", OrganizationRole.MEMBER)
    add(repo, "org-a", "suspended-admin", OrganizationRole.ADMIN, UserStatus.SUSPENDED)
    add(repo, "org-b", "other-tenant-admin", OrganizationRole.ADMIN)
    with pytest.raises(LastActiveAdminError):
        repo.set_status_preserving_active_admin("org-a", "target", UserStatus.SUSPENDED, NOW)
    assert repo.get_user("org-a", "target").status is UserStatus.ACTIVE


@pytest.mark.parametrize("kind", ("memory", "sqlite"))
def test_two_admins_allow_one_suspension_then_protect_the_remaining_admin(kind, tmp_path):
    repo = repository(kind, tmp_path); add(repo, "org", "admin-a", OrganizationRole.ADMIN); add(repo, "org", "admin-b", OrganizationRole.ADMIN)
    service = AccessService(repo, clock=lambda: NOW)
    principal_a = RequestPrincipal(user_id="admin-a", organization_id="org", role=OrganizationRole.ADMIN)
    principal_b = RequestPrincipal(user_id="admin-b", organization_id="org", role=OrganizationRole.ADMIN)
    assert service.set_status(principal_a, "admin-b", UserStatus.SUSPENDED).status is UserStatus.SUSPENDED
    with pytest.raises(LastActiveAdminError):
        service.set_status(principal_b, "admin-a", UserStatus.SUSPENDED)
    assert repo.get_user("org", "admin-a").status is UserStatus.ACTIVE
    assert service.set_status(principal_a, "admin-b", UserStatus.ACTIVE).status is UserStatus.ACTIVE


@pytest.mark.parametrize("kind", ("memory", "sqlite"))
def test_member_status_and_idempotent_status_updates_remain_supported(kind, tmp_path):
    repo = repository(kind, tmp_path); add(repo, "org", "admin", OrganizationRole.ADMIN); add(repo, "org", "member", OrganizationRole.MEMBER)
    service = AccessService(repo, clock=lambda: NOW)
    principal = RequestPrincipal(user_id="admin", organization_id="org", role=OrganizationRole.ADMIN)
    assert service.set_status(principal, "member", UserStatus.SUSPENDED).status is UserStatus.SUSPENDED
    suspended = repo.get_user("org", "member")
    assert service.set_status(principal, "member", UserStatus.SUSPENDED) == suspended
    assert service.set_status(principal, "member", UserStatus.ACTIVE).status is UserStatus.ACTIVE
    assert service.set_status(principal, "admin", UserStatus.ACTIVE).status is UserStatus.ACTIVE


def test_sqlite_concurrent_admin_suspensions_are_serialized(tmp_path):
    repo = SQLiteAccessRepository(tmp_path / "concurrent.db")
    add(repo, "org", "admin-a", OrganizationRole.ADMIN); add(repo, "org", "admin-b", OrganizationRole.ADMIN)
    service = AccessService(repo, clock=lambda: NOW)
    requests = (
        (RequestPrincipal(user_id="admin-a", organization_id="org", role=OrganizationRole.ADMIN), "admin-b"),
        (RequestPrincipal(user_id="admin-b", organization_id="org", role=OrganizationRole.ADMIN), "admin-a"),
    )

    def suspend(item):
        principal, target = item
        try:
            return service.set_status(principal, target, UserStatus.SUSPENDED).status
        except LastActiveAdminError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(suspend, requests))
    assert sorted(str(value) for value in outcomes) == ["blocked", "suspended"]
    statuses = {repo.get_user("org", user_id).status for user_id in ("admin-a", "admin-b")}
    assert statuses == {UserStatus.ACTIVE, UserStatus.SUSPENDED}


def test_last_admin_api_error_is_bounded():
    principal = RequestPrincipal(user_id="operator", organization_id="org", role=OrganizationRole.ADMIN)

    class RejectingService:
        def authenticate(self, _token): return principal
        def set_status(self, *_args): raise LastActiveAdminError("internal count and tenant details")

    app = FastAPI(); router, _ = create_access_router(RejectingService(), secure_cookie=True); app.include_router(router)
    response = TestClient(app).patch("/api/v1/access/users/target/status", json={"status": "suspended"})
    assert response.status_code == 409
    assert response.json() == {"detail": "At least one active administrator is required."}
    assert "internal" not in response.text and "tenant" not in response.text
