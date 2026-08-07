from typing import Protocol, runtime_checkable

from asep.projects.models import WorkspaceProject


@runtime_checkable
class ProjectRepository(Protocol):
    def save(self, project: WorkspaceProject) -> None: ...
    def get(self, project_id: str) -> WorkspaceProject: ...
    def list(self) -> tuple[WorkspaceProject, ...]: ...
