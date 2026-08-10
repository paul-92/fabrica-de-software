from pathlib import Path

from fastapi import APIRouter

from asep.api.project_schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectAIRuntimeExecutionRequestBody,
    ProjectAIRuntimeExecutionResponse,
    CreateProjectSessionRequest,
    ProjectSessionResponse,
    ProjectSessionListResponse,
    ProjectExecutionResponse,
    ProjectExecutionListResponse,
)
from asep.application import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectService,
    ProjectSessionService,
)


def create_projects_router(
    service: ProjectService,
    runtime_execution: ProjectAIRuntimeExecutionService | None = None,
    session_service: ProjectSessionService | None = None,
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

    if session_service is not None:
        @router.post("/{project_id}/sessions", response_model=ProjectSessionResponse, status_code=201)
        def create_session(project_id: str, body: CreateProjectSessionRequest) -> ProjectSessionResponse:
            return ProjectSessionResponse.from_domain(session_service.create(project_id, body.title))

        @router.get("/{project_id}/sessions", response_model=ProjectSessionListResponse)
        def list_sessions(project_id: str) -> ProjectSessionListResponse:
            return ProjectSessionListResponse(items=tuple(
                ProjectSessionResponse.from_domain(item) for item in session_service.list(project_id)
            ))

        @router.get("/{project_id}/sessions/{session_id}", response_model=ProjectSessionResponse)
        def get_session(project_id: str, session_id: str) -> ProjectSessionResponse:
            return ProjectSessionResponse.from_domain(session_service.get(project_id, session_id))

        @router.get("/{project_id}/executions", response_model=ProjectExecutionListResponse)
        def list_executions(project_id: str) -> ProjectExecutionListResponse:
            return ProjectExecutionListResponse(items=tuple(
                ProjectExecutionResponse.from_domain(item) for item in session_service.list_executions(project_id)
            ))

        @router.get("/{project_id}/sessions/{session_id}/executions", response_model=ProjectExecutionListResponse)
        def list_session_executions(project_id: str, session_id: str) -> ProjectExecutionListResponse:
            return ProjectExecutionListResponse(items=tuple(
                ProjectExecutionResponse.from_domain(item)
                for item in session_service.list_session_executions(project_id, session_id)
            ))

        @router.get("/{project_id}/executions/{execution_id}", response_model=ProjectExecutionResponse)
        def get_execution(project_id: str, execution_id: str) -> ProjectExecutionResponse:
            return ProjectExecutionResponse.from_domain(session_service.get_execution(project_id, execution_id))

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
                    session_id=body.session_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                    execution_mode=body.execution_mode,
                )
            )
            runtime_result = result.runtime_result
            return ProjectAIRuntimeExecutionResponse(
                execution_id=result.execution.execution_id,
                output=runtime_result.output,
                runtime_id=runtime_result.identity.runtime_id,
                model_id=runtime_result.identity.model_id,
                usage=(
                    None
                    if runtime_result.usage is None
                    else runtime_result.usage.model_dump(mode="json")
                ),
                metadata=runtime_result.model_dump(mode="json")["metadata"],
                execution_mode=result.execution_mode,
                changes=tuple(
                    change.model_dump(mode="json")
                    for change in result.changes
                ),
                context_entry_count=result.execution.context_entry_count,
                context_truncated=result.execution.context_truncated,
            )

    return router
