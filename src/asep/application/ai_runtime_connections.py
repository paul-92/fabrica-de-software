"""Caso de uso de consulta segura das conexões de AI Runtime."""

from __future__ import annotations

from asep.ai_runtime.diagnostics import (
    AIRuntimeConnectionStatus,
    AIRuntimeDiagnostics,
)


class AIRuntimeConnectionService:
    def __init__(self, diagnostics: tuple[AIRuntimeDiagnostics, ...]) -> None:
        self._diagnostics = {
            item.runtime_id: item for item in diagnostics
        }

    def list_statuses(self) -> tuple[AIRuntimeConnectionStatus, ...]:
        return tuple(
            self._diagnostics[key].status()
            for key in sorted(self._diagnostics)
        )

    def get_status(self, runtime_id: str) -> AIRuntimeConnectionStatus:
        try:
            diagnostics = self._diagnostics[runtime_id]
        except KeyError as exc:
            raise ValueError("AI Runtime não configurado.") from exc
        return diagnostics.status()


__all__ = ["AIRuntimeConnectionService"]
