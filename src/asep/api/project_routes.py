from pathlib import Path

from fastapi import APIRouter

from asep.api.project_schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectAIRuntimeExecutionRequestBody,
    ProjectAIRuntimeExecutionResponse,
)
from asep.application import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectService,
)


def create_projects_router(
    service: ProjectService,
    runtime_execution: ProjectAIRuntimeExecutionService | None = None,
) -> APIRouter:
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

    if runtime_execution is not None:
        @router.post(
            "/{project_id}/ai-runtime/execute",
            response_model=ProjectAIRuntimeExecutionResponse,
        )
        def execute_runtime(
            project_id: str,
            body: ProjectAIRuntimeExecutionRequestBody,
        ) -> ProjectAIRuntimeExecutionResponse:
            result = runtime_execution.execute(
                ProjectAIRuntimeExecutionRequest(
                    project_id=project_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                )
            )
            return ProjectAIRuntimeExecutionResponse(
                output=result.output,
                runtime_id=result.identity.runtime_id,
                model_id=result.identity.model_id,
                usage=(
                    None
                    if result.usage is None
                    else result.usage.model_dump(mode="json")
                ),
                metadata=result.model_dump(mode="json")["metadata"],
            )

    return router
