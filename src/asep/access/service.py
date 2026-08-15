from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from asep.access.models import (
    AccessSession, Membership, OrganizationRole, RequestPrincipal, User,
    UserStatus,
)
from asep.access.repository import AccessRepository, LastActiveAdminError


class AccessDeniedError(Exception):
    pass


class SelfSuspensionError(Exception):
    pass


class AccessService:
    def __init__(self, repository: AccessRepository, *, session_ttl: timedelta = timedelta(hours=12),
                 clock: Callable[[], datetime] | None = None) -> None:
        self._repository = repository
        self._session_ttl = session_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def password_hash(password: str, *, salt: bytes | None = None) -> str:
        if len(password) < 12:
            raise ValueError("password must contain at least 12 characters")
        actual_salt = salt or secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=actual_salt, n=2**14, r=8, p=1)
        return f"scrypt${actual_salt.hex()}${digest.hex()}"

    @classmethod
    def verify_password(cls, password: str, encoded: str) -> bool:
        try:
            _kind, salt, expected = encoded.split("$", 2)
            actual = cls.password_hash(password, salt=bytes.fromhex(salt)).split("$", 2)[2]
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def login(self, email: str, password: str) -> tuple[str, RequestPrincipal]:
        found = self._repository.get_user_by_email(email.strip().casefold())
        if found is None or not self.verify_password(password, found[1]):
            raise AccessDeniedError("invalid credentials")
        user = found[0]
        if user.status is not UserStatus.ACTIVE:
            raise AccessDeniedError("access denied")
        memberships = [item for org in self._organization_ids(user.user_id)
                       if (item := self._repository.get_membership(org, user.user_id))]
        if len(memberships) != 1:
            raise AccessDeniedError("access denied")
        membership = memberships[0]
        token = secrets.token_urlsafe(32)
        now = self._clock()
        self._repository.save_session(AccessSession(
            session_id=str(uuid4()), user_id=user.user_id, token_hash=self.token_hash(token),
            created_at=now, expires_at=now + self._session_ttl,
        ))
        return token, RequestPrincipal(user_id=user.user_id, organization_id=membership.organization_id, role=membership.role)

    def _organization_ids(self, user_id: str):
        # Beta users belong to one organization. Repository implementations expose
        # memberships without allowing an organization choice from the client.
        if hasattr(self._repository, "organization_ids_for_user"):
            return self._repository.organization_ids_for_user(user_id)
        return tuple(org for org, candidate in getattr(self._repository, "memberships", {}) if candidate == user_id)

    def authenticate(self, token: str | None) -> RequestPrincipal:
        if not token:
            raise AccessDeniedError("authentication required")
        session = self._repository.get_session_by_hash(self.token_hash(token))
        if session is None or session.expires_at <= self._clock():
            if session is not None:
                self._repository.delete_session_by_hash(session.token_hash)
            raise AccessDeniedError("authentication required")
        memberships = [item for org in self._organization_ids(session.user_id)
                       if (item := self._repository.get_membership(org, session.user_id))]
        if len(memberships) != 1:
            raise AccessDeniedError("access denied")
        membership = memberships[0]
        user = self._repository.get_user(membership.organization_id, session.user_id)
        if user is None or user.status is not UserStatus.ACTIVE:
            raise AccessDeniedError("access denied")
        return RequestPrincipal(user_id=user.user_id, organization_id=membership.organization_id, role=membership.role)

    def logout(self, token: str | None) -> None:
        if token:
            self._repository.delete_session_by_hash(self.token_hash(token))

    def invite(self, principal: RequestPrincipal, email: str, password: str,
               role: OrganizationRole = OrganizationRole.MEMBER) -> User:
        self._require_admin(principal)
        now = self._clock()
        user = User(user_id=str(uuid4()), email=email, status=UserStatus.ACTIVE, created_at=now, updated_at=now)
        self._repository.save_user(user, self.password_hash(password))
        self._repository.save_membership(Membership(
            organization_id=principal.organization_id, user_id=user.user_id, role=role, created_at=now,
        ))
        return user

    def list_users(self, principal: RequestPrincipal) -> tuple[User, ...]:
        self._require_admin(principal)
        return self._repository.list_users(principal.organization_id)

    def membership(self, principal: RequestPrincipal, user_id: str) -> Membership:
        self._require_admin(principal)
        item = self._repository.get_membership(principal.organization_id, user_id)
        if item is None:
            raise KeyError(user_id)
        return item

    def set_status(self, principal: RequestPrincipal, user_id: str, status: UserStatus) -> User:
        self._require_admin(principal)
        if user_id == principal.user_id and status is UserStatus.SUSPENDED:
            raise SelfSuspensionError("an administrator cannot suspend its own account")
        return self._repository.set_status_preserving_active_admin(
            principal.organization_id, user_id, status, self._clock()
        )

    @staticmethod
    def _require_admin(principal: RequestPrincipal) -> None:
        if principal.role is not OrganizationRole.ADMIN:
            raise AccessDeniedError("administrator access required")


__all__ = ["AccessDeniedError", "AccessService", "LastActiveAdminError", "SelfSuspensionError"]
