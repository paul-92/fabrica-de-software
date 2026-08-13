from fastapi import APIRouter, Depends, HTTPException
from collections.abc import Callable
from asep.access import OrganizationRole, RequestPrincipal
from asep.ai_usage import AIUsageService
from asep.application import ProjectService

def create_ai_usage_router(service: AIUsageService, projects: ProjectService,
                           principal_dependency: Callable[..., RequestPrincipal]) -> APIRouter:
    router=APIRouter(tags=["ai-usage"])
    def response(current:RequestPrincipal, **filters):
        items=service.query(current.organization_id,**filters)
        aggregate=service.aggregate(current.organization_id,**filters)
        return {"items":[x.model_dump(mode="json") for x in items],"aggregate":aggregate.model_dump(mode="json")}
    @router.get("/api/v1/ai-usage/me")
    def mine(current:RequestPrincipal=Depends(principal_dependency)): return response(current,user_id=current.user_id)
    @router.get("/api/v1/projects/{project_id}/ai-usage")
    def project(project_id:str,current:RequestPrincipal=Depends(principal_dependency)):
        projects.get(project_id,current); return response(current,project_id=project_id)
    @router.get("/api/v1/projects/{project_id}/executions/{execution_id}/ai-usage")
    def execution(project_id:str,execution_id:str,current:RequestPrincipal=Depends(principal_dependency)):
        projects.get(project_id,current); return response(current,project_id=project_id,execution_id=execution_id)
    @router.get("/api/v1/ai-usage/organization")
    def organization(current:RequestPrincipal=Depends(principal_dependency)):
        if current.role is not OrganizationRole.ADMIN: raise HTTPException(status_code=404,detail="Resource not found.")
        return response(current)
    return router
