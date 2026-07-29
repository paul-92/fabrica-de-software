"""Consultas somente leitura sobre Runs e suas Timelines."""

from __future__ import annotations

from asep.errors import RunNotFoundError
from asep.runs import Run, RunRepository, RunStatus
from asep.timeline import TimelineEvent, TimelineRepository


class RunQueryService:
    """Coordena consultas sem conhecer armazenamento ou apresentação."""

    def __init__(
        self,
        run_repository: RunRepository,
        timeline_repository: TimelineRepository,
    ) -> None:
        self._run_repository = run_repository
        self._timeline_repository = timeline_repository

    def list_runs(self) -> tuple[Run, ...]:
        """Lista Runs do mais recente para o mais antigo."""
        by_id = sorted(
            self._run_repository.list(),
            key=lambda run: run.id,
        )
        return tuple(
            sorted(
                by_id,
                key=lambda run: run.started_at,
                reverse=True,
            )
        )

    def get_run(self, run_id: str) -> Run:
        """Obtém um Run existente."""
        return self._run_repository.get(self._validated_run_id(run_id))

    def get_timeline(self, run_id: str) -> tuple[TimelineEvent, ...]:
        """Obtém a Timeline cronológica de um Run existente."""
        validated_id = self._validated_run_id(run_id)
        self._run_repository.get(validated_id)
        return tuple(
            sorted(
                self._timeline_repository.list_by_run(validated_id),
                key=lambda event: (event.timestamp, event.id),
            )
        )

    def latest_run(self) -> Run:
        """Obtém o Run com started_at mais recente."""
        runs = self.list_runs()
        if not runs:
            raise RunNotFoundError(
                "Nenhum Run está disponível no repositório."
            )
        return runs[0]

    def list_runs_by_status(
        self, status: RunStatus
    ) -> tuple[Run, ...]:
        """Filtra Runs por um RunStatus tipado, preservando a ordenação."""
        if not isinstance(status, RunStatus):
            raise TypeError("status deve ser uma instância de RunStatus")
        return tuple(
            run for run in self.list_runs() if run.status is status
        )

    @staticmethod
    def _validated_run_id(run_id: str) -> str:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id não pode ser vazio")
        return run_id
