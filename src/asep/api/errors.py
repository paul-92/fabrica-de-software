"""Mapeamento central de falhas para respostas HTTP seguras."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from asep.api.schemas import ErrorDetail, ErrorResponse
from asep.errors import (
    AsepError,
    ProjectExecutionNotFoundError,
    ProjectNotFoundError,
    ProjectSessionNotFoundError,
    RunNotFoundError,
    WorkspaceEntryNotFoundError,
    WorkspaceNotFoundError,
)
from asep.planning import PlanningValidationError
from asep.ai_runtime import (
    AIRuntimeAuthenticationError,
    AIRuntimeInvalidResponseError,
    AIRuntimeNotFoundError,
    AIRuntimeTimeoutError,
    AIRuntimeUnavailableError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AIRuntimeNotFoundError)
    async def runtime_not_found_handler(
        request: Request, error: AIRuntimeNotFoundError
    ) -> JSONResponse:
        return _error_response(
            status_code=404,
            code="AI_RUNTIME_NOT_FOUND",
            message="AI Runtime not found.",
        )

    @app.exception_handler(AIRuntimeAuthenticationError)
    async def runtime_auth_handler(
        request: Request, error: AIRuntimeAuthenticationError
    ) -> JSONResponse:
        return _error_response(
            status_code=409,
            code="AI_RUNTIME_NOT_AUTHENTICATED",
            message="AI Runtime is not connected.",
        )

    @app.exception_handler(AIRuntimeUnavailableError)
    async def runtime_unavailable_handler(
        request: Request, error: AIRuntimeUnavailableError
    ) -> JSONResponse:
        return _error_response(
            status_code=503,
            code="AI_RUNTIME_UNAVAILABLE",
            message="AI Runtime is unavailable.",
        )

    @app.exception_handler(AIRuntimeTimeoutError)
    async def runtime_timeout_handler(
        request: Request, error: AIRuntimeTimeoutError
    ) -> JSONResponse:
        return _error_response(
            status_code=504,
            code="AI_RUNTIME_TIMEOUT",
            message="AI Runtime timed out.",
        )

    @app.exception_handler(AIRuntimeInvalidResponseError)
    async def runtime_response_handler(
        request: Request, error: AIRuntimeInvalidResponseError
    ) -> JSONResponse:
        return _error_response(
            status_code=502,
            code="AI_RUNTIME_INVALID_RESPONSE",
            message="AI Runtime returned an invalid response.",
        )

    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(
        request: Request,
        error: ProjectNotFoundError,
    ) -> JSONResponse:
        return _error_response(
            status_code=404,
            code=error.code,
            message="Project not found.",
        )

    @app.exception_handler(ProjectSessionNotFoundError)
    async def project_session_not_found_handler(
        request: Request, error: ProjectSessionNotFoundError,
    ) -> JSONResponse:
        return _error_response(status_code=404, code=error.code, message="Project session not found.")

    @app.exception_handler(ProjectExecutionNotFoundError)
    async def project_execution_not_found_handler(
        request: Request, error: ProjectExecutionNotFoundError,
    ) -> JSONResponse:
        return _error_response(status_code=404, code=error.code, message="Project execution not found.")

    @app.exception_handler(RunNotFoundError)
    async def run_not_found_handler(
        request: Request,
        error: RunNotFoundError,
    ) -> JSONResponse:
        return _error_response(
            status_code=404,
            code=error.code,
            message="Run not found.",
        )

    @app.exception_handler(WorkspaceNotFoundError)
    @app.exception_handler(WorkspaceEntryNotFoundError)
    async def workspace_not_found_handler(request: Request, error: AsepError) -> JSONResponse:
        return _error_response(status_code=404, code=error.code, message="Workspace entry not found.")

    @app.exception_handler(ValueError)
    async def invalid_value_handler(
        request: Request,
        error: ValueError,
    ) -> JSONResponse:
        if str(error) != "run_id não pode ser vazio":
            return _error_response(
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                message="Internal server error.",
            )
        return _error_response(
            status_code=400,
            code="INVALID_REQUEST",
            message="Invalid request.",
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            status_code=422,
            code="REQUEST_VALIDATION_ERROR",
            message="Request validation failed.",
        )

    @app.exception_handler(PlanningValidationError)
    async def planning_validation_handler(
        request: Request,
        error: PlanningValidationError,
    ) -> JSONResponse:
        return _error_response(
            status_code=400,
            code="PLANNING_INVALID",
            message="Planning request could not produce a valid plan.",
        )

    @app.exception_handler(AsepError)
    async def asep_error_handler(
        request: Request,
        error: AsepError,
    ) -> JSONResponse:
        return _error_response(
            status_code=400,
            code=error.code,
            message="Request could not be completed.",
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        return _error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error.",
        )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )
