"""Filtragem determinística de dados sensíveis antes da persistência."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "private_key",
    "bearer",
    "cookie",
    "cookies",
    "credentials",
}
_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|secret|token|authorization|api[_-]?key|"
    r"private[_-]?key|bearer|cookie|credentials)\b"
    r"(\s*[:=]\s*)([\"'][^\"']*[\"']|[^\s,;]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
    r"-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)


class MemoryFilter:
    def sanitize(
        self, content: str, metadata: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any], bool]:
        sanitized_content, replacements = _SECRET_PATTERN.subn(
            lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
            content,
        )
        sanitized_content, bearer_replacements = _BEARER_PATTERN.subn(
            "Bearer [REDACTED]", sanitized_content
        )
        sanitized_content, key_replacements = _PRIVATE_KEY_PATTERN.subn(
            "[REDACTED PRIVATE KEY]", sanitized_content
        )
        filtered = (
            replacements > 0
            or bearer_replacements > 0
            or key_replacements > 0
        )

        def clean(value: Any) -> Any:
            nonlocal filtered
            if isinstance(value, Mapping):
                result = {}
                for key, child in value.items():
                    normalized = str(key).lower().replace("-", "_")
                    if (
                        normalized in _SENSITIVE_KEYS
                        or normalized.endswith("_token")
                        or normalized.endswith("_password")
                    ):
                        filtered = True
                        continue
                    result[str(key)] = clean(child)
                return result
            if isinstance(value, (list, tuple)):
                return [clean(child) for child in value]
            return value

        return sanitized_content, clean(metadata), filtered


__all__ = ["MemoryFilter"]
