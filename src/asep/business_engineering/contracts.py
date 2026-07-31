"""Contratos da Business Engineering."""

from __future__ import annotations

from abc import ABC, abstractmethod

from asep.business_engineering.models import ProjectBlueprint
from asep.planning import PlanningResult


class PlanningAdapter(ABC):
    """Contrato para integração com o Planning Engine."""

    @abstractmethod
    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> PlanningResult:
        """Cria um PlanningResult a partir de um ProjectBlueprint."""


__all__ = [
    "PlanningAdapter",
]