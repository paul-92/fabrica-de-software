"""Modelos independentes de fornecedor para execuções de providers."""

from __future__ import annotations

from copy import deepcopy
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class AgentExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ProducedFileOperation(StrEnum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


class ProducedFile(BaseModel):
    """Descrição de uma alteração informada pelo provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    operation: ProducedFileOperation
    checksum: str | None = None
    size: int | None = Field(default=None, ge=0)

    @field_validator("path")
    @classmethod
    def path_is_relative_and_safe(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("path do arquivo produzido não pode ser vazio")

        posix_path = PurePosixPath(value)
        windows_path = PureWindowsPath(value)
        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or ".." in posix_path.parts
            or ".." in windows_path.parts
        ):
            raise ValueError(
                "path do arquivo produzido deve ser relativo e seguro"
            )
        return value


def _freeze_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_metadata(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_metadata(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_metadata(item) for item in value)
    return deepcopy(value)


def _serialize_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _serialize_metadata(item) for key, item in value.items()
        }
    if isinstance(value, (tuple, frozenset)):
        return [_serialize_metadata(item) for item in value]
    return value


class AgentExecutionResult(BaseModel):
    """Resultado normalizado devolvido por qualquer AgentProvider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AgentExecutionStatus
    provider_name: str
    provider_version: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    produced_files: tuple[ProducedFile, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("provider_name", "provider_version")
    @classmethod
    def provider_identity_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identidade do provider não pode ser vazia")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_is_immutable(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return _freeze_metadata(value)

    @field_serializer("metadata")
    def serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _serialize_metadata(value)

    @model_validator(mode="after")
    def result_is_consistent(self) -> AgentExecutionResult:
        has_error_detail = any(error.strip() for error in self.errors)
        has_failure_evidence = (
            has_error_detail
            or bool(self.stderr.strip())
            or (self.exit_code is not None and self.exit_code != 0)
        )
        if self.status is AgentExecutionStatus.SUCCESS and has_error_detail:
            raise ValueError("resultado SUCCESS não pode conter erros")
        if (
            self.status is AgentExecutionStatus.FAILED
            and not has_failure_evidence
        ):
            raise ValueError(
                "resultado FAILED deve conter evidência da falha"
            )
        return self
