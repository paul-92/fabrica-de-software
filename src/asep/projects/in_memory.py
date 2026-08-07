from asep.errors import ProjectNotFoundError
from asep.projects.models import WorkspaceProject


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[str, WorkspaceProject] = {}

    def save(self, project: WorkspaceProject) -> None:
        self._projects[project.project_id] = project.model_copy(deep=True)

    def get(self, project_id: str) -> WorkspaceProject:
        try:
            return self._projects[project_id].model_copy(deep=True)
        except KeyError as exc:
            raise ProjectNotFoundError("Projeto não encontrado.") from exc

    def list(self) -> tuple[WorkspaceProject, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in sorted(
                self._projects.values(),
                key=lambda project: (project.created_at, project.project_id),
            )
        )
