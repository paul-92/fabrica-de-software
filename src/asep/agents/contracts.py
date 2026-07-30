"""Contratos públicos e independentes de provider para agentes ASEP."""

from __future__ import annotations

from typing import Mapping, Protocol, runtime_checkable

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from asep.execution.models import (
    AgentContext,
    AgentResult,
    AgentResultStatus,
)


class _FrozenContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentId(_FrozenContract):
    """Identificador estável e validado de um agente."""

    value: str

    @field_validator("value")
    @classmethod
    def value_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("AgentId não pode ser vazio")
        return value

    def __str__(self) -> str:
        return self.value


class AgentCapability(_FrozenContract):
    """Capacidade declarada por um agente."""

    id: str
    description: str | None = None

    @field_validator("id")
    @classmethod
    def id_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id da AgentCapability não pode ser vazio")
        return value

    @field_validator("description")
    @classmethod
    def description_is_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError(
                "description da AgentCapability não pode ser vazia"
            )
        return value


class AgentMetadata(_FrozenContract):
    """Identidade e descrição imutáveis publicadas por um agente."""

    id: AgentId
    name: str
    description: str
    version: str
    capabilities: tuple[AgentCapability, ...] = ()
    attributes: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("name", "description", "version")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("valor do AgentMetadata não pode ser vazio")
        return value

    @model_validator(mode="after")
    def capabilities_are_unique(self) -> AgentMetadata:
        capability_ids = tuple(item.id for item in self.capabilities)
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("AgentMetadata possui capacidades duplicadas")
        return self


class AgentRequest(_FrozenContract):
    """Solicitação imutável entregue a um agente."""

    request_id: str
    objective: str
    inputs: Mapping[str, JsonValue] = Field(default_factory=dict)
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("request_id", "objective")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("valor não pode ser vazio")
        return value


class AgentError(_FrozenContract):
    """Erro estruturado que pode ser associado a uma execução."""

    code: str
    message: str
    retryable: bool = False
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)

    @field_validator("code", "message")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code e message do AgentError são obrigatórios")
        return value


@runtime_checkable
class Agent(Protocol):
    """Contrato síncrono mínimo de um agente ASEP."""

    @property
    def metadata(self) -> AgentMetadata: ...

    def execute(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> AgentResult: ...


AgentStatus = AgentResultStatus


__all__ = [
    "Agent",
    "AgentCapability",
    "AgentContext",
    "AgentError",
    "AgentId",
    "AgentMetadata",
    "AgentRequest",
    "AgentResult",
    "AgentStatus",
]
