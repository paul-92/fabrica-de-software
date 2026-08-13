from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.access import OrganizationRole, RequestPrincipal
from asep.application import ProjectService
from asep.errors import ProjectValidationError
from asep.projects import HostedWorkspaceManager, InMemoryProjectRepository, WorkspaceProject

NOW = datetime.now(UTC)

def principal(organization_id: str = "org-a") -> RequestPrincipal:
    return RequestPrincipal(user_id="user-a", organization_id=organization_id, role=OrganizationRole.ADMIN)

def test_hosted_project_is_provisioned_at_backend_owned_path(tmp_path: Path) -> None:
    manager = HostedWorkspaceManager(tmp_path / "hosted")
    service = ProjectService(InMemoryProjectRepository(), hosted_workspaces=manager, id_generator=lambda: "project-a")
    project = service.create_hosted("Project", principal())
    assert project.workspace_path == (tmp_path / "hosted/org-a/project-a/workspace").resolve()
    assert project.workspace_path.is_dir()
    assert project.workspace_id and project.workspace_kind == "hosted"

@pytest.mark.parametrize("organization_id,project_id", [("../org", "p"), ("org", "C:/outside"), ("org", "..")])
def test_hosted_identity_cannot_inject_paths(tmp_path: Path, organization_id: str, project_id: str) -> None:
    with pytest.raises(ProjectValidationError):
        HostedWorkspaceManager(tmp_path / "hosted").provision(organization_id, project_id)

def test_workspace_id_mismatch_and_neighbor_path_fail_closed(tmp_path: Path) -> None:
    manager = HostedWorkspaceManager(tmp_path / "hosted")
    hosted = manager.provision("org-a", "project-a")
    project = WorkspaceProject(project_id="project-a", organization_id="org-a", created_by_user_id="user-a", name="P", workspace_id=hosted.workspace_id, workspace_kind="hosted", workspace_path=hosted.path, created_at=NOW, updated_at=NOW)
    with pytest.raises(ProjectValidationError):
        manager.resolve(project, "workspace-from-project-b")
    neighbor = tmp_path / "hosted/org-b/project-a/workspace"; neighbor.mkdir(parents=True)
    with pytest.raises(ProjectValidationError):
        manager.resolve(project.model_copy(update={"workspace_path": neighbor}))

def test_symlink_or_reparse_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    manager = HostedWorkspaceManager(tmp_path / "hosted")
    outside = tmp_path / "outside"; outside.mkdir()
    project_root = tmp_path / "hosted/org-a/project-a"; project_root.mkdir(parents=True)
    link = project_root / "workspace"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("host does not permit an unprivileged directory link")
    project = WorkspaceProject(project_id="project-a", organization_id="org-a", created_by_user_id="user-a", name="P", workspace_id="w", workspace_kind="hosted", workspace_path=link, created_at=NOW, updated_at=NOW)
    with pytest.raises(ProjectValidationError):
        manager.resolve(project)
