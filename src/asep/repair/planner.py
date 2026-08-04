"""Planejamento determinístico de reparos."""

from __future__ import annotations

from asep.repair.models import (
    FailureAnalysis,
    RepairChange,
    RepairPlan,
)


class DeterministicRepairPlanner:
    """Produz um RepairPlan a partir de um FailureAnalysis."""

    def plan(
        self,
        analysis: FailureAnalysis,
    ) -> RepairPlan:
        changes = tuple(
            RepairChange(
                path=path,
                content="",
                reason=(
                    "Arquivo identificado durante a análise "
                    "da falha."
                ),
            )
            for path in analysis.affected_paths
        )

        if not changes:
            changes = (
                RepairChange(
                    path="<unknown>",
                    content="",
                    reason="Nenhum arquivo pôde ser identificado.",
                ),
            )

        return RepairPlan(
            analysis=analysis,
            changes=changes,
            test_paths=("tests",),
        )


__all__ = [
    "DeterministicRepairPlanner",
]