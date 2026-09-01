"""Política central de isolamento de paths para Tools."""

from __future__ import annotations

from pathlib import Path

from asep.tools.exceptions import ToolSecurityError, ToolValidationError

_BLOCKED_PARTS = {".git", ".ssh"}
_BLOCKED_NAMES = {".env", ".netrc", "credentials", "credentials.json"}
_ALLOWED_ENV_TEMPLATES = {".env.example"}


def _is_blocked_part(part: str) -> bool:
    normalized = part.lower()
    return (
        normalized in _BLOCKED_PARTS
        or normalized in _BLOCKED_NAMES
        or (
            normalized.startswith(".env.")
            and normalized not in _ALLOWED_ENV_TEMPLATES
        )
    )


def validated_workspace(workspace: Path) -> Path:
    resolved = workspace.resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ToolValidationError("workspace deve existir e ser diretório.")
    return resolved


def resolve_workspace_path(
    workspace: Path,
    relative_path: str,
    *,
    must_exist: bool = True,
) -> Path:
    root = validated_workspace(workspace)
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ToolValidationError("path relativo é obrigatório.")
    candidate_input = Path(relative_path)
    if candidate_input.is_absolute():
        raise ToolSecurityError("paths absolutos não são permitidos.")
    if any(_is_blocked_part(part) for part in candidate_input.parts):
        raise ToolSecurityError("path crítico ou oculto não é permitido.")
    candidate = (root / candidate_input).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ToolSecurityError("path fora do workspace.") from exc
    if must_exist and not candidate.exists():
        raise ToolValidationError("path não existe no workspace.")
    return candidate


def is_safe_discovered_path(workspace: Path, candidate: Path) -> bool:
    try:
        relative = candidate.relative_to(workspace)
        if any(_is_blocked_part(part) for part in relative.parts):
            return False
        candidate.resolve().relative_to(workspace)
        return True
    except (OSError, ValueError):
        return False


__all__ = [
    "is_safe_discovered_path",
    "resolve_workspace_path",
    "validated_workspace",
]
