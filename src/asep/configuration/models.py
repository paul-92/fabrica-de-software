"""Modelos imutáveis da configuração da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePath
from urllib.parse import urlsplit

from asep.configuration.errors import ConfigurationValidationError

_DEFAULT_STORAGE_DIRECTORY = Path("storage")
_DEFAULT_SQLITE_DATABASE = _DEFAULT_STORAGE_DIRECTORY / "asep.db"
_DEFAULT_AGENT_CATALOG_DIRECTORY = Path("registry")
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


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
    workflows_filename: str = "workflow-snapshots.json"
    quality_gate_results_filename: str = "quality-gate-results.json"
    branding_filename: str = "branding.json"
    sqlite_database: Path | str = _DEFAULT_SQLITE_DATABASE
    cors_origins: tuple[str, ...] | str = DEFAULT_CORS_ORIGINS
    repair_workspace: Path | str | None = None
    agent_catalog_directory: Path | str = _DEFAULT_AGENT_CATALOG_DIRECTORY
    access_cookie_secure: bool | str = False
    legacy_admin_email: str = "admin@legacy.local"
    legacy_admin_password: str = "change-me-local-admin"
    hosted_root: Path | str = _DEFAULT_STORAGE_DIRECTORY / "hosted-workspaces"

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
        self._validate_filename(
            "workflows_filename",
            self.workflows_filename,
        )
        self._validate_filename(
            "quality_gate_results_filename",
            self.quality_gate_results_filename,
        )
        self._validate_filename("branding_filename", self.branding_filename)
        object.__setattr__(
            self,
            "sqlite_database",
            self._validate_path(
                "sqlite_database",
                self.sqlite_database,
            ),
        )
        object.__setattr__(
            self,
            "cors_origins",
            self._validate_cors_origins(self.cors_origins),
        )
        object.__setattr__(
            self,
            "repair_workspace",
            self._validate_repair_workspace(self.repair_workspace),
        )
        object.__setattr__(
            self,
            "agent_catalog_directory",
            self._validate_path(
                "agent_catalog_directory", self.agent_catalog_directory
            ),
        )
        object.__setattr__(self, "access_cookie_secure", str(self.access_cookie_secure).casefold() in {"1", "true", "yes"})
        object.__setattr__(self, "hosted_root", self._validate_path("hosted_root", self.hosted_root))
        if len(self.legacy_admin_password) < 12:
            raise ConfigurationValidationError("legacy_admin_password deve conter ao menos 12 caracteres.")
        if self.access_cookie_secure and self.legacy_admin_password == "change-me-local-admin":
            raise ConfigurationValidationError("produção exige uma senha administrativa explícita.")

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
    def _validate_cors_origins(
        value: tuple[str, ...] | str,
    ) -> tuple[str, ...]:
        origins = value.split(",") if isinstance(value, str) else value
        if not isinstance(origins, tuple | list):
            raise ConfigurationValidationError(
                "cors_origins deve conter origens HTTP validas."
            )

        normalized: list[str] = []
        for raw_origin in origins:
            if not isinstance(raw_origin, str) or not raw_origin.strip():
                raise ConfigurationValidationError(
                    "cors_origins nao pode conter origens vazias."
                )
            parsed = urlsplit(raw_origin.strip())
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ConfigurationValidationError(
                    f"Origem CORS invalida: {raw_origin}"
                )
            origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
            if origin not in normalized:
                normalized.append(origin)
        return tuple(normalized)

    @staticmethod
    def _validate_repair_workspace(value: Path | str | None) -> Path | None:
        if value is None:
            return None
        if not isinstance(value, (str, PurePath)):
            raise ConfigurationValidationError(
                "repair_workspace deve ser um caminho válido."
            )
        if isinstance(value, str) and not value.strip():
            raise ConfigurationValidationError(
                "repair_workspace não pode ser vazio."
            )
        workspace = Path(value).expanduser().resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise ConfigurationValidationError(
                "repair_workspace deve existir e ser um diretório."
            )
        return workspace

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
