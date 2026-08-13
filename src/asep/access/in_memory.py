from asep.access.models import AccessSession, Membership, Organization, User


class InMemoryAccessRepository:
    def __init__(self) -> None:
        self.organizations: dict[str, Organization] = {}
        self.users: dict[str, tuple[User, str]] = {}
        self.memberships: dict[tuple[str, str], Membership] = {}
        self.sessions: dict[str, AccessSession] = {}

    def save_organization(self, organization: Organization) -> None:
        self.organizations.setdefault(organization.organization_id, organization)

    def save_user(self, user: User, password_hash: str) -> None:
        if any(item.email == user.email for item, _ in self.users.values()):
            raise ValueError("user email already exists")
        self.users[user.user_id] = (user, password_hash)

    def update_user(self, user: User) -> None:
        _old, password = self.users[user.user_id]
        self.users[user.user_id] = (user, password)

    def get_user_by_email(self, email: str) -> tuple[User, str] | None:
        return next((value for value in self.users.values() if value[0].email == email.casefold()), None)

    def get_user(self, organization_id: str, user_id: str) -> User | None:
        value = self.users.get(user_id)
        return value[0] if value and (organization_id, user_id) in self.memberships else None

    def list_users(self, organization_id: str) -> tuple[User, ...]:
        ids = {user_id for org_id, user_id in self.memberships if org_id == organization_id}
        return tuple(sorted((self.users[item][0] for item in ids), key=lambda user: user.email))

    def save_membership(self, membership: Membership) -> None:
        self.memberships[(membership.organization_id, membership.user_id)] = membership

    def get_membership(self, organization_id: str, user_id: str) -> Membership | None:
        return self.memberships.get((organization_id, user_id))

    def save_session(self, session: AccessSession) -> None:
        self.sessions[session.token_hash] = session

    def get_session_by_hash(self, token_hash: str) -> AccessSession | None:
        return self.sessions.get(token_hash)

    def delete_session_by_hash(self, token_hash: str) -> None:
        self.sessions.pop(token_hash, None)
