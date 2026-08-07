from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from asep.errors import ProjectValidationError
from asep.projects import ProjectRepository, WorkspaceProject


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))

    def create(self, name: str, workspace_path: Path) -> WorkspaceProject:
        if not name.strip():
            raise ProjectValidationError("Nome do projeto não pode ser vazio.")
        if not str(workspace_path).strip():
            raise ProjectValidationError("Workspace não pode ser vazio.")
        workspace = workspace_path.expanduser().resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise ProjectValidationError(
                "Workspace deve existir e ser um diretório.", path=workspace
            )
        now = self._clock()
        project = WorkspaceProject(
            project_id=self._id_generator(),
            name=name.strip(),
            workspace_path=workspace,
            created_at=now,
            updated_at=now,
        )
        self._repository.save(project)
        return project

    def list(self) -> tuple[WorkspaceProject, ...]:
        return self._repository.list()

    def get(self, project_id: str) -> WorkspaceProject:
        return self._repository.get(project_id)
