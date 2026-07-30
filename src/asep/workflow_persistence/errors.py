"""Erros específicos da persistência de workflows."""

from __future__ import annotations

from pathlib import Path

from asep.errors import AsepError


class WorkflowPersistenceError(AsepError):
    code = "WORKFLOW_PERSISTENCE_ERROR"
    category = "persistence"
    exit_code = 5


class WorkflowSnapshotAlreadyExistsError(WorkflowPersistenceError):
    code = "WORKFLOW_SNAPSHOT_EXISTS"
    category = "conflict"


class WorkflowSnapshotNotFoundError(WorkflowPersistenceError):
    code = "WORKFLOW_SNAPSHOT_NOT_FOUND"
    category = "not_found"


class WorkflowStorageError(WorkflowPersistenceError):
    def __init__(self, message: str, *, path: Path | None = None) -> None:
        self.path = path
        super().__init__(message)


class InvalidWorkflowStorageFormatError(WorkflowStorageError):
    code = "WORKFLOW_STORAGE_INVALID"
    category = "validation"
    exit_code = 3


class WorkflowStorageReadError(WorkflowStorageError):
    code = "WORKFLOW_STORAGE_READ_ERROR"


class WorkflowStorageWriteError(WorkflowStorageError):
    code = "WORKFLOW_STORAGE_WRITE_ERROR"
