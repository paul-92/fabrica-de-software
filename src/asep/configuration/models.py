"""Modelos imutáveis da configuração da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePath

from asep.configuration.errors import ConfigurationValidationError

_DEFAULT_STORAGE_DIRECTORY = Path("storage")
_DEFAULT_SQLITE_DATABASE = _DEFAULT_STORAGE_DIRECTORY / "asep.db"


class StorageBackend(StrEnum):
    """Backends de persistência suportados pela aplicação."""

    MEMORY = "memory"
    FILE = "file"
    SQLITE = "sqlite"


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    """Snapshot validado de toda configuração atualmente suportada."""

    storage_backend: StorageBackend | str = StorageBackend.MEMORY
    storage_directory: Path | str | None = _DEFAULT_STORAGE_DIRECTORY
    runs_filename: str = "runs.json"
    timeline_filename: str = "timeline-events.json"
    sqlite_database: Path | str = _DEFAULT_SQLITE_DATABASE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "storage_backend",
            self._validate_backend(self.storage_backend),
        )
        object.__setattr__(
            self,
            "storage_directory",
            self._validate_directory(self.storage_directory),
        )
        self._validate_filename("runs_filename", self.runs_filename)
        self._validate_filename(
            "timeline_filename",
            self.timeline_filename,
        )
        object.__setattr__(
            self,
            "sqlite_database",
            self._validate_path(
                "sqlite_database",
                self.sqlite_database,
            ),
        )

    @staticmethod
    def _validate_backend(
        value: StorageBackend | str,
    ) -> StorageBackend:
        try:
            return StorageBackend(value)
        except (TypeError, ValueError) as exc:
            raise ConfigurationValidationError(
                f"Backend de armazenamento não suportado: {value}"
            ) from exc

    @staticmethod
    def _validate_directory(value: Path | str | None) -> Path:
        if value is None:
            return _DEFAULT_STORAGE_DIRECTORY
        return ApplicationSettings._validate_path(
            "storage_directory",
            value,
        )

    @staticmethod
    def _validate_path(field: str, value: Path | str) -> Path:
        if not isinstance(value, (str, PurePath)):
            raise ConfigurationValidationError(
                f"{field} deve ser um caminho válido."
            )
        if isinstance(value, str) and not value.strip():
            raise ConfigurationValidationError(
                f"{field} não pode ser vazio."
            )
        return Path(value)

    @staticmethod
    def _validate_filename(field: str, value: str) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value in {".", ".."}
            or Path(value).name != value
            or "/" in value
            or "\\" in value
        ):
            raise ConfigurationValidationError(
                f"{field} deve conter somente um nome de arquivo válido."
            )
