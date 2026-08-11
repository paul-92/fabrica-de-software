"""In-memory Quality Gate result repository."""

from __future__ import annotations

from asep.quality_results.errors import DuplicateQualityGateResultError
from asep.quality_results.models import StoredQualityGateResult


def result_key(result: StoredQualityGateResult) -> tuple[str, str, str]:
    return (result.run_id, result.stage_id, result.gate_id)


def result_order(result: StoredQualityGateResult) -> tuple[object, ...]:
    return (result.stage_id, result.gate_id, result.evaluated_at)


class InMemoryQualityGateResultRepository:
    def __init__(self) -> None:
        self._results: dict[tuple[str, str, str], StoredQualityGateResult] = {}

    def record(self, result: StoredQualityGateResult) -> None:
        key = result_key(result)
        if key in self._results:
            raise DuplicateQualityGateResultError(
                "Quality Gate result duplicado: " + "/".join(key)
            )
        self._results[key] = self._copy(result)

    def list_by_run(self, run_id: str) -> tuple[StoredQualityGateResult, ...]:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id da consulta não pode ser vazio")
        return tuple(
            self._copy(result)
            for result in sorted(
                (item for item in self._results.values() if item.run_id == run_id),
                key=result_order,
            )
        )

    @staticmethod
    def _copy(result: StoredQualityGateResult) -> StoredQualityGateResult:
        return StoredQualityGateResult.model_validate(result.model_dump(mode="json"))


__all__ = ["InMemoryQualityGateResultRepository", "result_key", "result_order"]
