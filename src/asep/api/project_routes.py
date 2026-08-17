from typing import Annotated

from fastapi import APIRouter, Depends, Path as PathParameter, Query
from collections.abc import Callable
from asep.access.models import LEGACY_ADMIN_USER_ID, LEGACY_ORGANIZATION_ID, OrganizationRole, RequestPrincipal

from asep.api.project_schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectAIRuntimeExecutionRequestBody,
    ProjectAIRuntimeExecutionResponse,
    ProjectEngineeringPreparationResponse,
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


def _runtime_response(result) -> ProjectAIRuntimeExecutionResponse:
    runtime_result = result.runtime_result
    public = {
        "execution_id": result.execution.execution_id,
        "output": runtime_result.output,
        "runtime_id": runtime_result.identity.runtime_id,
        "model_id": runtime_result.identity.model_id,
        "usage": None if runtime_result.usage is None else runtime_result.usage.model_dump(mode="json"),
        "metadata": runtime_result.model_dump(mode="json")["metadata"],
        "execution_mode": result.execution_mode,
        "changes": tuple(change.model_dump(mode="json") for change in result.changes),
        "context_entry_count": result.execution.context_entry_count,
        "context_truncated": result.execution.context_truncated,
        "context_char_count": result.execution.context_char_count,
        "context_omitted_execution_count": result.execution.context_omitted_execution_count,
        "memory_entry_count": result.execution.memory_entry_count,
        "memory_char_count": result.execution.memory_char_count,
        "memory_truncated": result.execution.memory_truncated,
    }
    if result.execution.operational_plan is not None:
        public.update({
            "status": result.execution.status,
            "instruction": result.execution.instruction,
            "operational_plan": OperationalPlanResponse.from_domain(result.execution.operational_plan),
            "validations": tuple(ValidationResponse.from_domain(item) for item in result.execution.validations),
            "repair": RepairResponse.from_domain(result.execution.repair),
            "quality_gate": ProjectQualityGateResponse.from_domain(result.execution.quality_gate),
            "step_results": tuple(item.model_dump(mode="json") for item in result.execution.step_results),
            "error_code": result.execution.error_code,
            "created_at": result.execution.created_at,
            "completed_at": result.execution.completed_at,
            "idempotent_noop_evidence": (
                None
                if result.execution.idempotent_noop_evidence is None
                else result.execution.idempotent_noop_evidence.model_dump(mode="json")
            ),
        })
    return ProjectAIRuntimeExecutionResponse.model_validate(public)


def create_projects_router(
    service: ProjectService,
    runtime_execution: ProjectAIRuntimeExecutionService | None = None,
    session_service: ProjectSessionService | None = None,
    memory_service: ProjectSessionMemoryService | None = None,
    workspace_service: ProjectWorkspaceService | None = None,
    memory_search_service: SessionMemorySearchService | None = None,
    engineering_execution: ProjectEngineeringExecutionService | None = None,
    principal_dependency: Callable[..., RequestPrincipal] | None = None,
) -> APIRouter:
    if principal_dependency is None:
        def principal_dependency() -> RequestPrincipal:
            # Explicitly injected applications without an access service are a
            # trusted embedding boundary (used by unit compositions), never the
            # configured HTTP composition.
            return RequestPrincipal(user_id=LEGACY_ADMIN_USER_ID, organization_id=LEGACY_ORGANIZATION_ID, role=OrganizationRole.ADMIN)
    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    @router.post("", response_model=ProjectResponse, status_code=201)
    def create_project(body: CreateProjectRequest, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectResponse:
        return ProjectResponse.from_domain(
            service.create_hosted(body.name, current)
        )

    @router.get("", response_model=ProjectListResponse)
    def list_projects(current: RequestPrincipal = Depends(principal_dependency)) -> ProjectListResponse:
        return ProjectListResponse(
            items=tuple(ProjectResponse.from_domain(item) for item in service.list(current))
        )

    @router.get("/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectResponse:
        return ProjectResponse.from_domain(service.get(project_id, current))

    if workspace_service is not None:
        @router.get("/{project_id}/workspace", response_model=WorkspaceDirectoryResponse)
        def list_workspace(project_id: str, path: str = Query(default=""), current: RequestPrincipal = Depends(principal_dependency)) -> WorkspaceDirectoryResponse:
            service.get(project_id, current)
            return WorkspaceDirectoryResponse.from_domain(workspace_service.list_directory(project_id, path))

        @router.get("/{project_id}/workspace/file", response_model=WorkspaceFileContentResponse)
        def read_workspace_file(project_id: str, path: str = Query(..., min_length=1), current: RequestPrincipal = Depends(principal_dependency)) -> WorkspaceFileContentResponse:
            service.get(project_id, current)
            return WorkspaceFileContentResponse.from_domain(workspace_service.read_file(project_id, path))

    if session_service is not None:
        @router.post("/{project_id}/sessions", response_model=ProjectSessionResponse, status_code=201)
        def create_session(project_id: str, body: CreateProjectSessionRequest, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectSessionResponse:
            service.get(project_id, current)
            return ProjectSessionResponse.from_domain(session_service.create(project_id, body.title))

        @router.get("/{project_id}/sessions", response_model=ProjectSessionListResponse)
        def list_sessions(project_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectSessionListResponse:
            service.get(project_id, current)
            return ProjectSessionListResponse(items=tuple(
                ProjectSessionResponse.from_domain(item) for item in session_service.list(project_id)
            ))

        @router.get("/{project_id}/sessions/{session_id}", response_model=ProjectSessionResponse)
        def get_session(project_id: str, session_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectSessionResponse:
            service.get(project_id, current)
            return ProjectSessionResponse.from_domain(session_service.get(project_id, session_id))

        @router.get("/{project_id}/executions", response_model=ProjectExecutionListResponse)
        def list_executions(project_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectExecutionListResponse:
            service.get(project_id, current)
            return ProjectExecutionListResponse(items=tuple(
                ProjectExecutionResponse.from_domain(item) for item in session_service.list_executions(project_id)
            ))

        @router.get("/{project_id}/sessions/{session_id}/executions", response_model=ProjectExecutionListResponse)
        def list_session_executions(project_id: str, session_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectExecutionListResponse:
            service.get(project_id, current)
            return ProjectExecutionListResponse(items=tuple(
                ProjectExecutionResponse.from_domain(item)
                for item in session_service.list_session_executions(project_id, session_id)
            ))

        @router.get("/{project_id}/executions/{execution_id}", response_model=ProjectExecutionResponse)
        def get_execution(project_id: str, execution_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> ProjectExecutionResponse:
            service.get(project_id, current)
            return ProjectExecutionResponse.from_domain(session_service.get_execution(project_id, execution_id))

    if runtime_execution is not None:
        if engineering_execution is not None:
            @router.post(
                "/{project_id}/engineering/prepare",
                response_model=ProjectEngineeringPreparationResponse,
                status_code=201,
            )
            def prepare_engineering(
                project_id: str,
                body: ProjectAIRuntimeExecutionRequestBody,
                current: RequestPrincipal = Depends(principal_dependency),
            ) -> ProjectEngineeringPreparationResponse:
                service.get(project_id, current)
                request = ProjectAIRuntimeExecutionRequest(
                    project_id=project_id,
                    session_id=body.session_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                    execution_mode=body.execution_mode,
                    principal=current,
                )
                prepared = engineering_execution.prepare(request)
                return ProjectEngineeringPreparationResponse(
                    execution_id=prepared.execution_id,
                    project_id=prepared.project_id,
                    session_id=prepared.session_id,
                    runtime_id=prepared.runtime_id,
                    instruction=prepared.instruction,
                    status=prepared.status,
                    analysis=prepared.preparation_analysis,
                    operational_plan=OperationalPlanResponse.from_domain(
                        prepared.operational_plan
                    ),
                    created_at=prepared.created_at,
                )

            @router.post(
                "/{project_id}/engineering/{preparation_id}/approve",
                response_model=ProjectAIRuntimeExecutionResponse,
                response_model_exclude_unset=True,
            )
            def approve_engineering(
                project_id: str,
                preparation_id: str,
                body: ProjectAIRuntimeExecutionRequestBody,
                current: RequestPrincipal = Depends(principal_dependency),
            ) -> ProjectAIRuntimeExecutionResponse:
                service.get(project_id, current)
                if session_service is not None:
                    session_service.get_execution(project_id, preparation_id)
                request = ProjectAIRuntimeExecutionRequest(
                    project_id=project_id,
                    session_id=body.session_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                    execution_mode=body.execution_mode,
                    principal=current,
                )
                result = engineering_execution.approve(preparation_id, request)
                return _runtime_response(result)

            @router.post(
                "/{project_id}/engineering/{preparation_id}/cancel",
                response_model=ProjectExecutionResponse,
            )
            def cancel_engineering(
                project_id: str,
                preparation_id: str,
                body: ProjectAIRuntimeExecutionRequestBody,
                current: RequestPrincipal = Depends(principal_dependency),
            ) -> ProjectExecutionResponse:
                service.get(project_id, current)
                if session_service is not None:
                    session_service.get_execution(project_id, preparation_id)
                request = ProjectAIRuntimeExecutionRequest(
                    project_id=project_id,
                    session_id=body.session_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                    execution_mode=body.execution_mode,
                    principal=current,
                )
                return ProjectExecutionResponse.from_domain(
                    engineering_execution.cancel(preparation_id, request)
                )

        @router.post(
            "/{project_id}/ai-runtime/execute",
            response_model=ProjectAIRuntimeExecutionResponse,
            response_model_exclude_unset=True,
        )
        def execute_runtime(
            project_id: str,
            body: ProjectAIRuntimeExecutionRequestBody,
            current: RequestPrincipal = Depends(principal_dependency),
        ) -> ProjectAIRuntimeExecutionResponse:
            service.get(project_id, current)
            request = ProjectAIRuntimeExecutionRequest(
                    project_id=project_id,
                    session_id=body.session_id,
                    runtime_id=body.runtime_id,
                    instruction=body.instruction,
                    metadata=body.metadata,
                    execution_mode=body.execution_mode,
                    principal=current,
                )
            result = (
                engineering_execution.execute(request)
                if (
                    engineering_execution is not None
                    and body.execution_mode.value == "workspace_write"
                )
                else runtime_execution.execute(request)
            )
            return _runtime_response(result)

    if memory_service is not None:
        @router.get(
            "/{project_id}/sessions/{session_id}/memory",
            response_model=SessionMemoryListResponse,
        )
        def list_memory(project_id: str, session_id: str, current: RequestPrincipal = Depends(principal_dependency)) -> SessionMemoryListResponse:
            service.get(project_id, current)
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
            current: RequestPrincipal = Depends(principal_dependency),
        ) -> SessionMemoryResponse:
            service.get(project_id, current)
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
            current: RequestPrincipal = Depends(principal_dependency),
        ) -> SessionMemorySearchResponse:
            service.get(project_id, current)
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
