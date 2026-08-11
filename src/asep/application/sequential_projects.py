"""Narrow Application contracts for authorized sequential projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from asep.errors import AsepError


class SequentialProjectResolutionError(AsepError):
    category = "validation"
    exit_code = 2


class SequentialProjectNotFoundError(SequentialProjectResolutionError):
    code = "SEQUENTIAL_PROJECT_NOT_FOUND"


class SequentialProjectPathError(SequentialProjectResolutionError):
    code = "SEQUENTIAL_PROJECT_PATH_INVALID"


class SequentialProjectIdentityMismatchError(SequentialProjectResolutionError):
    code = "SEQUENTIAL_PROJECT_IDENTITY_MISMATCH"


@dataclass(frozen=True, slots=True)
class AuthorizedSequentialProject:
    project_id: str
    project_path: Path


@runtime_checkable
class SequentialProjectResolver(Protocol):
    def resolve(self, project_id: str) -> AuthorizedSequentialProject: ...


__all__ = [
    "AuthorizedSequentialProject",
    "SequentialProjectIdentityMismatchError",
    "SequentialProjectNotFoundError",
    "SequentialProjectPathError",
    "SequentialProjectResolutionError",
    "SequentialProjectResolver",
]
