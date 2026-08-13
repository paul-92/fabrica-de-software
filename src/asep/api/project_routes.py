from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Path as PathParameter, Query

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
    CreateSessionMemoryRequest,
    SessionMemoryListResponse,
    SessionMemoryResponse,
    SessionMemorySearchResponse,
    WorkspaceDirectoryResponse,
    WorkspaceFileContentResponse,
    OperationalPlanResponse,
    ProjectQualityGateResponse,
    RepairResponse,
    ValidationResponse,
)
from asep.application import (
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectEngineeringExecutionService,
    ProjectService,
    ProjectSessionService,
    ProjectSessionMemoryService,
    ProjectWorkspaceService,
    SessionMemoryKind,
    SessionMemoryOrder,
    SessionMemorySearchRequest,
    SessionMemorySearchService,
)
from asep.api.schemas import ErrorResponse


Identifier = Annotated[str, PathParameter(min_length=1, pattern=r".*\S.*")]
SignificantText = Annotated[str, Query(min_length=1, pattern=r".*\S.*")]


def create_projects_router(
    service: ProjectService,
    runtime_execution: ProjectAIRuntimeExecutionService | None = None,
    session_service: ProjectSessionService | None = None,
    memory_service: ProjectSessionMemoryService | None = None,
    workspace_service: ProjectWorkspaceService | None = None,
    memory_search_service: SessionMemorySearchService | None = None,
    engineering_execution: ProjectEngineeringExecutionService | None = None,
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

    if workspace_service is not None:
        @router.get("/{project_id}/workspace", response_model=WorkspaceDirectoryResponse)
        def list_workspace(project_id: str, path: str = Query(default="")) -> WorkspaceDirectoryResponse:
            return WorkspaceDirectoryResponse.from_domain(workspace_service.list_directory(project_id, path))

        @router.get("/{project_id}/workspace/file", response_model=WorkspaceFileContentResponse)
        def read_workspace_file(project_id: str, path: str = Query(..., min_length=1)) -> WorkspaceFileContentResponse:
            return WorkspaceFileContentResponse.from_domain(workspace_service.read_file(project_id, path))

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
            response_model_exclude_unset=True,
        )
        def execute_runtime(
            project_id: str,
            body: ProjectAIRuntimeExecutionRequestBody,
        ) -> ProjectAIRuntimeExecutionResponse:
            request = ProjectAIRuntimeExecutionRequest(
                    project_id=project_id,
                    session_id=body.session_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                    execution_mode=body.execution_mode,
                )
            result = (
                engineering_execution.execute(request)
                if (
                    engineering_execution is not None
                    and body.execution_mode.value == "workspace_write"
                )
                else runtime_execution.execute(request)
            )
            runtime_result = result.runtime_result
            public = {
                "execution_id": result.execution.execution_id,
                "output": runtime_result.output,
                "runtime_id": runtime_result.identity.runtime_id,
                "model_id": runtime_result.identity.model_id,
                "usage": (
                    None
                    if runtime_result.usage is None
                    else runtime_result.usage.model_dump(mode="json")
                ),
                "metadata": runtime_result.model_dump(mode="json")["metadata"],
                "execution_mode": result.execution_mode,
                "changes": tuple(
                    change.model_dump(mode="json")
                    for change in result.changes
                ),
                "context_entry_count": result.execution.context_entry_count,
                "context_truncated": result.execution.context_truncated,
                "context_char_count": result.execution.context_char_count,
                "context_omitted_execution_count": (
                    result.execution.context_omitted_execution_count
                ),
                "memory_entry_count": result.execution.memory_entry_count,
                "memory_char_count": result.execution.memory_char_count,
                "memory_truncated": result.execution.memory_truncated,
            }
            if result.execution.operational_plan is not None:
                public.update({
                "status": result.execution.status,
                "instruction": result.execution.instruction,
                "operational_plan": OperationalPlanResponse.from_domain(
                    result.execution.operational_plan
                ),
                "validations": tuple(
                    ValidationResponse.from_domain(item)
                    for item in result.execution.validations
                ),
                "repair": RepairResponse.from_domain(result.execution.repair),
                "quality_gate": ProjectQualityGateResponse.from_domain(
                    result.execution.quality_gate
                ),
                "step_results": tuple(
                    item.model_dump(mode="json")
                    for item in result.execution.step_results
                ),
                "error_code": result.execution.error_code,
                "created_at": result.execution.created_at,
                "completed_at": result.execution.completed_at,
                })
            return ProjectAIRuntimeExecutionResponse.model_validate(public)

    if memory_service is not None:
        @router.get(
            "/{project_id}/sessions/{session_id}/memory",
            response_model=SessionMemoryListResponse,
        )
        def list_memory(project_id: str, session_id: str) -> SessionMemoryListResponse:
            return SessionMemoryListResponse(items=tuple(
                SessionMemoryResponse.from_domain(item)
                for item in memory_service.list(project_id, session_id)
            ))

        @router.post(
            "/{project_id}/sessions/{session_id}/memory",
            response_model=SessionMemoryResponse,
            status_code=201,
        )
        def add_memory(
            project_id: str,
            session_id: str,
            body: CreateSessionMemoryRequest,
        ) -> SessionMemoryResponse:
            return SessionMemoryResponse.from_domain(memory_service.add(
                project_id, session_id, body.kind, body.content
            ))

    if memory_search_service is not None:
        @router.get(
            "/{project_id}/sessions/{session_id}/memory/search",
            response_model=SessionMemorySearchResponse,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                422: {"model": ErrorResponse},
                500: {"model": ErrorResponse},
            },
            summary="Search session memory",
        )
        def search_memory(
            project_id: Identifier,
            session_id: Identifier,
            text: SignificantText | None = None,
            kind: SessionMemoryKind | None = None,
            order: SessionMemoryOrder = SessionMemoryOrder.NEWEST,
            page_size: int = Query(default=25, ge=1, le=100),
            cursor: SignificantText | None = None,
        ) -> SessionMemorySearchResponse:
            return SessionMemorySearchResponse.from_application(
                memory_search_service.search(SessionMemorySearchRequest(
                    project_id=project_id,
                    session_id=session_id,
                    text=text,
                    kind=kind,
                    order=order,
                    page_size=page_size,
                    cursor=cursor,
                ))
            )

    return router
