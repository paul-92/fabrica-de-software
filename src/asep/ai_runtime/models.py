"""Modelos provider-agnostic da fronteira de AI Runtime."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from asep._json_values import freeze_json, json_value


class _FrozenRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AIRuntimeCapability(_FrozenRuntimeModel):
    """Capacidade extensível declarada por um runtime."""

    id: str

    @field_validator("id")
    @classmethod
    def id_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("id da capability não pode ser vazio")
        return normalized


class AIRuntimeIdentity(_FrozenRuntimeModel):
    """Identidade neutra e extensível de runtime e modelo."""

    runtime_id: str
    model_id: str
    capabilities: tuple[AIRuntimeCapability, ...] = ()

    @field_validator("runtime_id", "model_id")
    @classmethod
    def identity_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("identidade do runtime não pode ser vazia")
        return normalized

    @model_validator(mode="after")
    def capabilities_are_unique(self) -> AIRuntimeIdentity:
        ids = tuple(capability.id for capability in self.capabilities)
        if len(ids) != len(set(ids)):
            raise ValueError("runtime possui capabilities duplicadas")
        return self


class AIRuntimeRequest(_FrozenRuntimeModel):
    """Intenção da ASEP entregue a um AI Runtime."""

    instruction: str
    context: Mapping[str, Any] = Field(default_factory=dict, repr=False)
    metadata: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @field_validator("instruction")
    @classmethod
    def instruction_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("instruction não pode ser vazia")
        return normalized

    @field_validator("context", "metadata")
    @classmethod
    def mappings_are_json(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return freeze_json(value, location="AI Runtime request")

    @field_serializer("context", "metadata")
    def serialize_mappings(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return json_value(value)


class AIRuntimeUsage(_FrozenRuntimeModel):
    """Consumo genérico reportado pelo runtime, quando conhecido."""

    input_units: int | None = Field(default=None, ge=0)
    output_units: int | None = Field(default=None, ge=0)
    total_units: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def total_is_consistent(self) -> AIRuntimeUsage:
        if (
            self.input_units is not None
            and self.output_units is not None
            and self.total_units is not None
            and self.total_units != self.input_units + self.output_units
        ):
            raise ValueError("total_units deve somar input_units e output_units")
        return self


class AIRuntimeResult(_FrozenRuntimeModel):
    """Saída normalizada de qualquer AI Runtime."""

    output: str
    identity: AIRuntimeIdentity
    usage: AIRuntimeUsage | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @field_validator("output")
    @classmethod
    def output_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("output do runtime não pode ser vazio")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_is_json(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return freeze_json(value, location="AI Runtime result")

    @field_serializer("metadata")
    def serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return json_value(value)


__all__ = [
    "AIRuntimeCapability",
    "AIRuntimeIdentity",
    "AIRuntimeRequest",
    "AIRuntimeResult",
    "AIRuntimeUsage",
]
