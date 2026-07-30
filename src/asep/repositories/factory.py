"""Factory central das implementações de repositories."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from asep.configuration import ApplicationSettings, StorageBackend
from asep.repositories.errors import RepositoryConfigurationError
from asep.runs import (
    FileRunRepository,
    InMemoryRunRepository,
    RunRepository,
    SQLiteRunRepository,
)
from asep.timeline import (
    FileTimelineRepository,
    InMemoryTimelineRepository,
    SQLiteTimelineRepository,
    TimelineRepository,
)
from asep.workflow_persistence import (
    FileWorkflowRepository,
    InMemoryWorkflowRepository,
    SQLiteWorkflowRepository,
    WorkflowRepository,
)


RepositorySettings = ApplicationSettings


@dataclass(frozen=True, slots=True)
class RepositoryBundle:
    run_repository: RunRepository
    timeline_repository: TimelineRepository
    workflow_repository: WorkflowRepository


class RepositoryFactory:
    """Seleciona repositories concretos sem expô-los aos consumidores."""

    def __init__(self, configuration: ApplicationSettings) -> None:
        self._configuration = configuration

    def create(self) -> RepositoryBundle:
        builders: dict[
            StorageBackend,
            Callable[[], RepositoryBundle],
        ] = {
            StorageBackend.MEMORY: self._create_memory,
            StorageBackend.FILE: self._create_file,
            StorageBackend.SQLITE: self._create_sqlite,
        }
        try:
            builder = builders[self._configuration.storage_backend]
        except KeyError as exc:  # pragma: no cover - proteção futura
            raise RepositoryConfigurationError(
                "Backend de armazenamento não registrado."
            ) from exc
        return builder()

    @staticmethod
    def _create_memory() -> RepositoryBundle:
        return RepositoryBundle(
            run_repository=InMemoryRunRepository(),
            timeline_repository=InMemoryTimelineRepository(),
            workflow_repository=InMemoryWorkflowRepository(),
        )

    def _create_file(self) -> RepositoryBundle:
        storage_directory = self._configuration.storage_directory
        return RepositoryBundle(
            run_repository=FileRunRepository(
                storage_directory / self._configuration.runs_filename
            ),
            timeline_repository=FileTimelineRepository(
                storage_directory / self._configuration.timeline_filename
            ),
            workflow_repository=FileWorkflowRepository(
                storage_directory / self._configuration.workflows_filename
            ),
        )

    def _create_sqlite(self) -> RepositoryBundle:
        database = self._configuration.sqlite_database
        return RepositoryBundle(
            run_repository=SQLiteRunRepository(database),
            timeline_repository=SQLiteTimelineRepository(database),
            workflow_repository=SQLiteWorkflowRepository(database),
        )
