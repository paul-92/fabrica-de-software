"""Contratos públicos do domínio de reparo de software."""

from __future__ import annotations

from typing import Protocol

from asep.repair.models import (
    FailureAnalysis,
    RepairPlan,
    RepairResult,
)


class FailureAnalyzer(Protocol):
    """Analisa uma falha funcional e produz diagnóstico estruturado."""

    def analyze(
        self,
        failure_output: str,
    ) -> FailureAnalysis:
        ...


class RepairPlanner(Protocol):
    """Produz um plano explícito de reparo a partir de um diagnóstico."""

    def plan(
        self,
        analysis: FailureAnalysis,
    ) -> RepairPlan:
        ...


class RepairExecutor(Protocol):
    """Executa um plano de reparo e devolve seu resultado."""

    def execute(
        self,
        plan: RepairPlan,
    ) -> RepairResult:
        ...


__all__ = [
    "FailureAnalyzer",
    "RepairExecutor",
    "RepairPlanner",
]