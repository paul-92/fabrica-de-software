from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from asep.errors import ProjectValidationError
from asep.projects import HostedWorkspaceManager, ProjectRepository, WorkspaceProject
from asep.access.models import LEGACY_ADMIN_USER_ID, LEGACY_ORGANIZATION_ID, RequestPrincipal


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_generator: Callable[[], str] | None = None,
        hosted_workspaces: HostedWorkspaceManager | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))
        self._hosted_workspaces = hosted_workspaces

    def create_hosted(self, name: str, principal: RequestPrincipal) -> WorkspaceProject:
        if not name.strip():
            raise ProjectValidationError("Nome do projeto não pode ser vazio.")
        if self._hosted_workspaces is None:
            raise ProjectValidationError("Hosted workspace não configurado.")
        project_id = self._id_generator()
        hosted = self._hosted_workspaces.provision(principal.organization_id, project_id)
        now = self._clock()
        project = WorkspaceProject(
            project_id=project_id, organization_id=principal.organization_id,
            created_by_user_id=principal.user_id, name=name.strip(),
            workspace_id=hosted.workspace_id, workspace_kind="hosted",
            workspace_path=hosted.path, created_at=now, updated_at=now,
        )
        self._repository.save(project)
        return project

    def create(self, name: str, workspace_path: Path, principal: RequestPrincipal | None = None) -> WorkspaceProject:
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
            organization_id=(principal.organization_id if principal else LEGACY_ORGANIZATION_ID),
            created_by_user_id=(principal.user_id if principal else LEGACY_ADMIN_USER_ID),
            name=name.strip(),
            workspace_path=workspace,
            created_at=now,
            updated_at=now,
        )
        self._repository.save(project)
        return project

    def list(self, principal: RequestPrincipal | None = None) -> tuple[WorkspaceProject, ...]:
        return self._repository.list_for_organization(principal.organization_id) if principal else self._repository.list()

    def get(self, project_id: str, principal: RequestPrincipal | None = None) -> WorkspaceProject:
        project = self._repository.get_for_organization(principal.organization_id, project_id) if principal else self._repository.get(project_id)
        if self._hosted_workspaces is not None and project.workspace_kind == "hosted":
            self._hosted_workspaces.resolve(project)
        return project
