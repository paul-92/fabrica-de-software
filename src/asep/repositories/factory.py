"""Factory central das implementações de repositories."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from asep.configuration import ApplicationSettings, StorageBackend
from asep.repositories.errors import RepositoryConfigurationError
from asep.memory import (
    InMemoryMemoryStore,
    MemoryStore,
    SQLiteMemoryStore,
)
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
from asep.projects import (
    InMemoryProjectRepository,
    ProjectRepository,
    SQLiteProjectRepository,
    ProjectExecutionRepository,
    ProjectSessionRepository,
    InMemoryProjectExecutionRepository,
    InMemoryProjectSessionRepository,
    SQLiteProjectExecutionRepository,
    SQLiteProjectSessionRepository,
    SessionMemoryRepository,
    InMemorySessionMemoryRepository,
    SQLiteSessionMemoryRepository,
    SessionMemoryQuerySource,
)
from asep.quality_results import (
    FileQualityGateResultRepository,
    InMemoryQualityGateResultRepository,
    QualityGateResultRepository,
    SQLiteQualityGateResultRepository,
)


RepositorySettings = ApplicationSettings


@dataclass(frozen=True, slots=True)
class RepositoryBundle:
    run_repository: RunRepository
    timeline_repository: TimelineRepository
    workflow_repository: WorkflowRepository
    quality_gate_result_repository: QualityGateResultRepository = field(
        default_factory=InMemoryQualityGateResultRepository
    )
    memory_store: MemoryStore = field(default_factory=InMemoryMemoryStore)
    project_repository: ProjectRepository = field(
        default_factory=InMemoryProjectRepository
    )
    project_session_repository: ProjectSessionRepository = field(
        default_factory=InMemoryProjectSessionRepository
    )
    project_execution_repository: ProjectExecutionRepository = field(
        default_factory=InMemoryProjectExecutionRepository
    )
    session_memory_repository: SessionMemoryRepository = field(
        default_factory=InMemorySessionMemoryRepository
    )
    session_memory_query_source: SessionMemoryQuerySource = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.session_memory_repository,
            SessionMemoryQuerySource,
        ):
            raise RepositoryConfigurationError(
                "Session memory repository does not support read queries."
            )
        object.__setattr__(
            self,
            "session_memory_query_source",
            self.session_memory_repository,
        )


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
            quality_gate_result_repository=InMemoryQualityGateResultRepository(),
            memory_store=InMemoryMemoryStore(),
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
            quality_gate_result_repository=FileQualityGateResultRepository(
                storage_directory
                / self._configuration.quality_gate_results_filename
            ),
            memory_store=InMemoryMemoryStore(),
        )

    def _create_sqlite(self) -> RepositoryBundle:
        database = self._configuration.sqlite_database
        return RepositoryBundle(
            run_repository=SQLiteRunRepository(database),
            timeline_repository=SQLiteTimelineRepository(database),
            workflow_repository=SQLiteWorkflowRepository(database),
            quality_gate_result_repository=SQLiteQualityGateResultRepository(
                database
            ),
            memory_store=SQLiteMemoryStore(database),
            project_repository=SQLiteProjectRepository(database),
            project_session_repository=SQLiteProjectSessionRepository(database),
            project_execution_repository=SQLiteProjectExecutionRepository(database),
            session_memory_repository=SQLiteSessionMemoryRepository(database),
        )
