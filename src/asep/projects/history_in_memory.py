from asep.errors import (
    ProjectExecutionNotFoundError,
    ProjectHistoryConflictError,
    ProjectSessionNotFoundError,
)
from asep.projects.history_models import ProjectExecution, ProjectSession


class InMemoryProjectSessionRepository:
    def __init__(self) -> None:
        self._items: dict[str, ProjectSession] = {}

    def create(self, session: ProjectSession) -> None:
        if session.session_id in self._items:
            raise ProjectHistoryConflictError("Project session already exists.")
        self._items[session.session_id] = session.model_copy(deep=True)

    def get(self, session_id: str) -> ProjectSession:
        try:
            return self._items[session_id].model_copy(deep=True)
        except KeyError as exc:
            raise ProjectSessionNotFoundError("Project session not found.") from exc

    def list_by_project(self, project_id: str) -> tuple[ProjectSession, ...]:
        items = (item for item in self._items.values() if item.project_id == project_id)
        return tuple(item.model_copy(deep=True) for item in sorted(
            items, key=lambda item: (item.created_at, item.session_id), reverse=True
        ))


class InMemoryProjectExecutionRepository:
    def __init__(self) -> None:
        self._items: dict[str, ProjectExecution] = {}

    def create(self, execution: ProjectExecution) -> None:
        if execution.execution_id in self._items:
            raise ProjectHistoryConflictError("Project execution already exists.")
        self._items[execution.execution_id] = execution.model_copy(deep=True)

    def update(self, execution: ProjectExecution) -> None:
        current = self.get(execution.execution_id)
        if (current.project_id, current.session_id) != (
            execution.project_id, execution.session_id
        ):
            raise ProjectHistoryConflictError("Project execution identity changed.")
        self._items[execution.execution_id] = execution.model_copy(deep=True)

    def get(self, execution_id: str) -> ProjectExecution:
        try:
            return self._items[execution_id].model_copy(deep=True)
        except KeyError as exc:
            raise ProjectExecutionNotFoundError("Project execution not found.") from exc

    def list_by_session(self, session_id: str) -> tuple[ProjectExecution, ...]:
        return self._list(lambda item: item.session_id == session_id)

    def list_by_project(self, project_id: str) -> tuple[ProjectExecution, ...]:
        return self._list(lambda item: item.project_id == project_id)

    def _list(self, predicate) -> tuple[ProjectExecution, ...]:
        items = (item for item in self._items.values() if predicate(item))
        return tuple(item.model_copy(deep=True) for item in sorted(
            items, key=lambda item: (item.created_at, item.execution_id), reverse=True
        ))


__all__ = ["InMemoryProjectExecutionRepository", "InMemoryProjectSessionRepository"]
