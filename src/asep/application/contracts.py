"""Portas públicas dos casos de uso inteligentes da aplicação."""

from __future__ import annotations

from typing import Protocol

from asep.intelligence import (
    IntelligentEngineeringRequest,
    IntelligentEngineeringResult,
)


class IntelligentEngineeringCapability(Protocol):
    """Capacidade mínima delegada pela fronteira de aplicação."""

    def execute(
        self,
        request: IntelligentEngineeringRequest,
    ) -> IntelligentEngineeringResult: ...


__all__ = ["IntelligentEngineeringCapability"]
