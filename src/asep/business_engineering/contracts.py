"""Contratos da Business Engineering."""

from __future__ import annotations

from abc import ABC, abstractmethod

from asep.business_engineering.models import ProjectBlueprint


class PlanningAdapter(ABC):
    """Contrato para integração com o Planning Engine."""

    @abstractmethod
    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> object:
        """Cria um plano de execução a partir de um ProjectBlueprint."""


__all__ = [
    "PlanningAdapter",
]