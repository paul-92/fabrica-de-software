"""Leitura segura de YAML com contexto de erro."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from asep.errors import ConfigurationError


def load_yaml(path: Path) -> dict[str, Any]:
    """Carrega um mapping YAML, rejeitando arquivo ausente ou raiz não-mapping."""
    if not path.is_file():
        raise ConfigurationError("Arquivo YAML não encontrado.", path=path)
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Não foi possível ler YAML: {exc}", path=path) from exc
    if not isinstance(content, dict):
        raise ConfigurationError("A raiz do YAML deve ser um objeto.", path=path)
    return content
