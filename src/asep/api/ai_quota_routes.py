from collections.abc import Callable
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from asep.access import AccessDeniedError, RequestPrincipal
from asep.ai_quotas import AIQuotaService

class QuotaBody(BaseModel):
    model_config=ConfigDict(extra="forbid")
    enabled: bool=True
    token_limit: int|None=Field(default=None,ge=0)
    call_limit: int|None=Field(default=None,ge=0)

def create_ai_quota_router(service:AIQuotaService, principal_dependency:Callable[...,RequestPrincipal]):
    router=APIRouter(prefix="/api/v1/ai-quotas",tags=["ai-quotas"])
    def payload(a): return a.model_dump(mode="json")
    def guarded(fn):
        try: return fn()
        except AccessDeniedError as exc: raise HTTPException(404,"Resource not found.") from exc
        except KeyError as exc: raise HTTPException(404,"Resource not found.") from exc
    @router.get("/me")
    def mine(current=Depends(principal_dependency)): return payload(service.get(current))
    @router.get("/users/{user_id}")
    def get(user_id:str,current=Depends(principal_dependency)): return guarded(lambda:payload(service.get(current,user_id)))
    @router.put("/users/{user_id}")
    def put(user_id:str,body:QuotaBody,current=Depends(principal_dependency)): return guarded(lambda:service.set(current,user_id,**body.model_dump()).model_dump(mode="json"))
    @router.delete("/users/{user_id}",status_code=204)
    def delete(user_id:str,current=Depends(principal_dependency)):
        guarded(lambda:service.remove(current,user_id)); return Response(status_code=204)
    return router
