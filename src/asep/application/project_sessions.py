from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from asep.application.projects import ProjectService
from asep.errors import ProjectExecutionNotFoundError, ProjectSessionNotFoundError
from asep.projects import ProjectExecution, ProjectExecutionRepository, ProjectSession, ProjectSessionRepository


class ProjectSessionService:
    def __init__(self, projects: ProjectService, sessions: ProjectSessionRepository,
                 executions: ProjectExecutionRepository, *,
                 clock: Callable[[], datetime] | None = None,
                 id_generator: Callable[[], str] | None = None) -> None:
        self._projects = projects
        self._sessions = sessions
        self._executions = executions
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def create(self, project_id: str, title: str) -> ProjectSession:
        self._projects.get(project_id)
        now = self._clock()
        session = ProjectSession(session_id=self._id_generator(), project_id=project_id,
                                 title=title, created_at=now, updated_at=now)
        self._sessions.create(session)
        return session

    def get(self, project_id: str, session_id: str) -> ProjectSession:
        self._projects.get(project_id)
        return self._sessions.get_by_project(project_id, session_id)

    def list(self, project_id: str) -> tuple[ProjectSession, ...]:
        self._projects.get(project_id)
        return self._sessions.list_by_project(project_id)

    def get_execution(self, project_id: str, execution_id: str) -> ProjectExecution:
        self._projects.get(project_id)
        return self._executions.get_by_project(project_id, execution_id)

    def list_executions(self, project_id: str) -> tuple[ProjectExecution, ...]:
        self._projects.get(project_id)
        return self._executions.list_by_project(project_id)

    def list_session_executions(self, project_id: str, session_id: str) -> tuple[ProjectExecution, ...]:
        self.get(project_id, session_id)
        return self._executions.list_by_session(session_id)


__all__ = ["ProjectSessionService"]
