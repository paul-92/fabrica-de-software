"""Persistence boundary for immutable Quality Gate results."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.quality_results.models import StoredQualityGateResult


@runtime_checkable
class QualityGateResultRepository(Protocol):
    def record(self, result: StoredQualityGateResult) -> None: ...

    def list_by_run(self, run_id: str) -> tuple[StoredQualityGateResult, ...]: ...


__all__ = ["QualityGateResultRepository"]
