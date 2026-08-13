from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


LEGACY_ORGANIZATION_ID = "legacy-local"
LEGACY_ADMIN_USER_ID = "legacy-local-admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrganizationRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class Organization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    organization_id: str
    name: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class User(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    user_id: str
    email: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not normalized or "@" not in normalized:
            raise ValueError("email must be valid")
        return normalized

    @field_validator("created_at", "updated_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class Membership(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    organization_id: str
    user_id: str
    role: OrganizationRole
    created_at: datetime


class RequestPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    user_id: str
    organization_id: str
    role: OrganizationRole


class AccessSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    session_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime


__all__ = [
    "AccessSession", "LEGACY_ADMIN_USER_ID", "LEGACY_ORGANIZATION_ID",
    "Membership", "Organization", "OrganizationRole", "RequestPrincipal",
    "User", "UserStatus",
]
