"""Carregamento centralizado da configuração da aplicação."""

from __future__ import annotations

import os
from collections.abc import Mapping

from asep.configuration.models import ApplicationSettings


class Configuration:
    """Carrega um snapshot imutável a partir de defaults e ambiente."""

    _ENVIRONMENT_FIELDS = {
        "ASEP_STORAGE_BACKEND": "storage_backend",
        "ASEP_STORAGE_DIRECTORY": "storage_directory",
        "ASEP_RUNS_FILENAME": "runs_filename",
        "ASEP_TIMELINE_FILENAME": "timeline_filename",
        "ASEP_WORKFLOWS_FILENAME": "workflows_filename",
        "ASEP_SQLITE_DATABASE": "sqlite_database",
        "ASEP_CORS_ORIGINS": "cors_origins",
        "ASEP_REPAIR_WORKSPACE": "repair_workspace",
    }

    @classmethod
    def load(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> ApplicationSettings:
        source = os.environ if environ is None else environ
        values = {
            field: source[variable]
            for variable, field in cls._ENVIRONMENT_FIELDS.items()
            if variable in source
        }
        return ApplicationSettings(**values)
