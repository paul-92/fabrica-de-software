"""Schemas HTTP seguros para diagnóstico de AI Runtimes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from asep.ai_runtime import AIRuntimeConnectionState, AIRuntimeConnectionStatus


class AIRuntimeStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    installed: bool
    authenticated: bool
    ready: bool
    state: AIRuntimeConnectionState
    version: str | None
    message: str
    authentication_command: str | None

    @classmethod
    def from_domain(
        cls, status: AIRuntimeConnectionStatus
    ) -> AIRuntimeStatusResponse:
        return cls.model_validate(status.model_dump(mode="json"))


class AIRuntimeListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[AIRuntimeStatusResponse, ...]


__all__ = ["AIRuntimeListResponse", "AIRuntimeStatusResponse"]
