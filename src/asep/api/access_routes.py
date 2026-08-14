from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from collections.abc import Callable

from asep.access import AccessDeniedError, AccessService, SelfSuspensionError
from asep.access.models import OrganizationRole, RequestPrincipal, UserStatus

COOKIE_NAME = "asep_session"


class AccessSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(AccessSchema):
    email: str
    password: str


class InviteRequest(AccessSchema):
    email: str
    password: str = Field(min_length=12)
    role: OrganizationRole = OrganizationRole.MEMBER


class UserStatusRequest(AccessSchema):
    status: UserStatus


def create_access_router(service: AccessService, *, secure_cookie: bool) -> tuple[APIRouter, Callable[..., RequestPrincipal]]:
    router = APIRouter(prefix="/api/v1/access", tags=["access"])

    def principal(asep_session: str | None = Cookie(default=None)) -> RequestPrincipal:
        try:
            return service.authenticate(asep_session)
        except AccessDeniedError as exc:
            raise HTTPException(status_code=401, detail="Authentication required.") from exc

    @router.post("/login")
    def login(body: LoginRequest, response: Response):
        try:
            token, current = service.login(body.email, body.password)
        except AccessDeniedError as exc:
            raise HTTPException(status_code=401, detail="Invalid credentials.") from exc
        response.set_cookie(COOKIE_NAME, token, httponly=True, secure=secure_cookie, samesite="lax", path="/")
        return current.model_dump(mode="json")

    @router.post("/logout")
    def logout(response: Response, asep_session: str | None = Cookie(default=None)):
        service.logout(asep_session)
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=secure_cookie, samesite="lax")
        return {"logged_out": True}

    @router.get("/session")
    def current(current: RequestPrincipal = Depends(principal)):
        return current.model_dump(mode="json")

    @router.post("/users", status_code=201)
    def invite(body: InviteRequest, current: RequestPrincipal = Depends(principal)):
        try:
            return service.invite(current, body.email, body.password, body.role).model_dump(mode="json")
        except AccessDeniedError as exc:
            raise HTTPException(status_code=403, detail="Administrator access required.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="User could not be invited.") from exc

    @router.get("/users")
    def users(current: RequestPrincipal = Depends(principal)):
        try:
            return {"items": [{**item.model_dump(mode="json"), "role": service.membership(current, item.user_id).role.value} for item in service.list_users(current)]}
        except AccessDeniedError as exc:
            raise HTTPException(status_code=403, detail="Administrator access required.") from exc

    @router.patch("/users/{user_id}/status")
    def status(user_id: str, body: UserStatusRequest, current: RequestPrincipal = Depends(principal)):
        try:
            return service.set_status(current, user_id, body.status).model_dump(mode="json")
        except AccessDeniedError as exc:
            raise HTTPException(status_code=403, detail="Administrator access required.") from exc
        except SelfSuspensionError as exc:
            raise HTTPException(status_code=409, detail="You cannot suspend your own account.") from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="User not found.") from exc

    return router, principal


__all__ = ["COOKIE_NAME", "create_access_router"]
