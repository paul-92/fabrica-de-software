"""Carregamento centralizado da configuração da aplicação."""

from __future__ import annotations

import os
from collections.abc import Mapping

from asep.configuration.models import ApplicationSettings


class Configuration:
    """Carrega um snapshot imutável a partir de defaults e ambiente."""

    _ENVIRONMENT_FIELDS = {
        "ASEP_ENVIRONMENT": "environment",
        "ASEP_STORAGE_BACKEND": "storage_backend",
        "ASEP_STORAGE_DIRECTORY": "storage_directory",
        "ASEP_RUNS_FILENAME": "runs_filename",
        "ASEP_TIMELINE_FILENAME": "timeline_filename",
        "ASEP_WORKFLOWS_FILENAME": "workflows_filename",
        "ASEP_QUALITY_GATE_RESULTS_FILENAME": "quality_gate_results_filename",
        "ASEP_SQLITE_DATABASE": "sqlite_database",
        "ASEP_CORS_ORIGINS": "cors_origins",
        "ASEP_REPAIR_WORKSPACE": "repair_workspace",
        "ASEP_AGENT_CATALOG_DIRECTORY": "agent_catalog_directory",
        "ASEP_ACCESS_COOKIE_SECURE": "access_cookie_secure",
        "ASEP_LEGACY_ADMIN_EMAIL": "legacy_admin_email",
        "ASEP_LEGACY_ADMIN_PASSWORD": "legacy_admin_password",
        "ASEP_HOSTED_ROOT": "hosted_root",
        "ASEP_MAINTENANCE_DIRECTORY": "maintenance_directory",
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
