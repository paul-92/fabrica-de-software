from datetime import datetime
from pathlib import Path

from asep.access.models import AccessSession, Membership, Organization, OrganizationRole, User, UserStatus
from asep.access.repository import LastActiveAdminError
from asep.sqlite import SQLiteDatabase


class SQLiteAccessRepository:
    def __init__(self, path: Path) -> None:
        self._database = SQLiteDatabase(path)

    def save_organization(self, organization: Organization) -> None:
        with self._database.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO organizations (id, created_at, payload) VALUES (?, ?, ?)", (organization.organization_id, organization.created_at.isoformat(), organization.model_dump_json()))

    def save_user(self, user: User, password_hash: str) -> None:
        with self._database.connect() as connection:
            connection.execute("INSERT INTO users (id, email, status, password_hash, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)", (user.user_id, user.email, user.status.value, password_hash, user.created_at.isoformat(), user.model_dump_json()))

    def update_user(self, user: User) -> None:
        with self._database.connect() as connection:
            connection.execute("UPDATE users SET status=?, payload=? WHERE id=?", (user.status.value, user.model_dump_json(), user.user_id))

    def set_status_preserving_active_admin(self, organization_id: str, user_id: str, status: UserStatus, updated_at: datetime) -> User:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT u.payload,m.role FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.organization_id=? AND u.id=?",
                (organization_id, user_id),
            ).fetchone()
            if row is None:
                raise KeyError(user_id)
            user = User.model_validate_json(row["payload"])
            if user.status is status:
                return user
            if status is UserStatus.SUSPENDED and row["role"] == OrganizationRole.ADMIN.value:
                active_admins = connection.execute(
                    "SELECT COUNT(*) FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.organization_id=? AND m.role=? AND u.status=?",
                    (organization_id, OrganizationRole.ADMIN.value, UserStatus.ACTIVE.value),
                ).fetchone()[0]
                if active_admins <= 1:
                    raise LastActiveAdminError("organization requires an active administrator")
            updated = user.model_copy(update={"status": status, "updated_at": updated_at})
            connection.execute("UPDATE users SET status=?, payload=? WHERE id=?", (updated.status.value, updated.model_dump_json(), user_id))
            return updated

    def get_user_by_email(self, email: str) -> tuple[User, str] | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT payload,password_hash FROM users WHERE email=?", (email,)).fetchone()
        return None if row is None else (User.model_validate_json(row["payload"]), row["password_hash"])

    def get_user(self, organization_id: str, user_id: str) -> User | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT u.payload FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.organization_id=? AND u.id=?", (organization_id, user_id)).fetchone()
        return None if row is None else User.model_validate_json(row["payload"])

    def list_users(self, organization_id: str) -> tuple[User, ...]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT u.payload FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.organization_id=? ORDER BY u.email", (organization_id,)).fetchall()
        return tuple(User.model_validate_json(row["payload"]) for row in rows)

    def save_membership(self, membership: Membership) -> None:
        with self._database.connect() as connection:
            connection.execute("INSERT OR REPLACE INTO memberships (organization_id,user_id,role,created_at,payload) VALUES (?,?,?,?,?)", (membership.organization_id, membership.user_id, membership.role.value, membership.created_at.isoformat(), membership.model_dump_json()))

    def get_membership(self, organization_id: str, user_id: str) -> Membership | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT payload FROM memberships WHERE organization_id=? AND user_id=?", (organization_id, user_id)).fetchone()
        return None if row is None else Membership.model_validate_json(row["payload"])

    def organization_ids_for_user(self, user_id: str) -> tuple[str, ...]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT organization_id FROM memberships WHERE user_id=?", (user_id,)).fetchall()
        return tuple(row["organization_id"] for row in rows)

    def save_session(self, session: AccessSession) -> None:
        with self._database.connect() as connection:
            connection.execute("INSERT INTO access_sessions (id,user_id,token_hash,expires_at,payload) VALUES (?,?,?,?,?)", (session.session_id, session.user_id, session.token_hash, session.expires_at.isoformat(), session.model_dump_json()))

    def get_session_by_hash(self, token_hash: str) -> AccessSession | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT payload FROM access_sessions WHERE token_hash=?", (token_hash,)).fetchone()
        return None if row is None else AccessSession.model_validate_json(row["payload"])

    def delete_session_by_hash(self, token_hash: str) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM access_sessions WHERE token_hash=?", (token_hash,))


__all__ = ["SQLiteAccessRepository"]
