from pathlib import Path

from fastapi import APIRouter

from asep.api.project_schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
)
from asep.application import ProjectService


def create_projects_router(service: ProjectService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    @router.post("", response_model=ProjectResponse, status_code=201)
    def create_project(body: CreateProjectRequest) -> ProjectResponse:
        return ProjectResponse.from_domain(
            service.create(body.name, Path(body.workspace_path))
        )

    @router.get("", response_model=ProjectListResponse)
    def list_projects() -> ProjectListResponse:
        return ProjectListResponse(
            items=tuple(ProjectResponse.from_domain(item) for item in service.list())
        )

    @router.get("/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str) -> ProjectResponse:
        return ProjectResponse.from_domain(service.get(project_id))

    return router
