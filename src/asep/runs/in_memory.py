"""Implementação não durável do RunRepository."""

from __future__ import annotations

from asep.errors import RunNotFoundError
from asep.runs.models import Run


class InMemoryRunRepository:
    """Armazena cópias de Runs apenas durante a vida desta instância."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    def save(self, run: Run) -> None:
        self._runs[run.id] = self._copy(run)

    def get(self, run_id: str) -> Run:
        try:
            run = self._runs[run_id]
        except KeyError as exc:
            raise RunNotFoundError(
                f"Run não encontrado no repositório: {run_id}"
            ) from exc
        return self._copy(run)

    def list(self) -> tuple[Run, ...]:
        return tuple(
            self._copy(run)
            for run in sorted(
                self._runs.values(),
                key=lambda item: (item.started_at, item.id),
            )
        )

    @staticmethod
    def _copy(run: Run) -> Run:
        return Run.model_validate(run.model_dump(mode="json"))
