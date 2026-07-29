"""Modelo canônico, imutável e independente de visualização."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from asep.execution.models import (
    AgentResultStatus,
    ArtifactReference,
    GateDecision,
)
from asep.providers.models import AgentExecutionStatus

EXECUTION_GRAPH_SCHEMA_VERSION = "1.0.0"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return deepcopy(value)


def _serialize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _serialize(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (tuple, frozenset)):
        return [_serialize(item) for item in value]
    return value


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class EdgeType(StrEnum):
    DEPENDENCY = "dependency"


class NodeExecutionDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_result_status: AgentResultStatus | None = None
    provider_result_status: AgentExecutionStatus | None = None
    provider_name: str | None = None
    provider_version: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    attempt: int = Field(default=0, ge=0)
    exit_code: int | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def times_and_status_are_consistent(self) -> NodeExecutionDetails:
        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at não pode preceder started_at")
        return self


class QualityGateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_id: str
    decision: GateDecision
    satisfied_criteria: tuple[str, ...] = ()
    unsatisfied_criteria: tuple[str, ...] = ()
    evaluated_at: datetime | None = None


class ExecutionNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    stage_id: str
    label: str
    description: str | None = None
    mode: str
    workflow_reference: str | None = None
    workflow_references: tuple[str, ...] = ()
    status: NodeStatus = NodeStatus.PENDING
    agent_ids: tuple[str, ...] = ()
    execution: NodeExecutionDetails = Field(
        default_factory=NodeExecutionDetails
    )
    artifacts: tuple[ArtifactReference, ...] = ()
    quality_gate: QualityGateSummary | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("node_id", "stage_id", "label")
    @classmethod
    def identity_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identidade do nó não pode ser vazia")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_is_immutable(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return _freeze(value)

    @field_serializer("metadata")
    def serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _serialize(value)


class ExecutionEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEPENDENCY
    label: str | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("source", "target")
    @classmethod
    def endpoint_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("extremidade da aresta não pode ser vazia")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_is_immutable(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return _freeze(value)

    @field_serializer("metadata")
    def serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _serialize(value)


class GraphMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    generator: str = "asep"
    generator_version: str = "0.1.0"
    schema_version: str = EXECUTION_GRAPH_SCHEMA_VERSION
    project_name: str | None = None
    workflow_name: str
    created_from: str
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    status_counts: Mapping[str, int] = Field(default_factory=dict)

    @field_validator("status_counts")
    @classmethod
    def counts_are_immutable(
        cls, value: Mapping[str, int]
    ) -> Mapping[str, int]:
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("status_counts")
    def serialize_counts(
        self, value: Mapping[str, int]
    ) -> dict[str, int]:
        return dict(sorted(value.items()))


class ExecutionGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    graph_id: str
    project_id: str | None = None
    workflow_id: str
    run_id: str | None = None
    schema_version: str = EXECUTION_GRAPH_SCHEMA_VERSION
    nodes: tuple[ExecutionNode, ...]
    edges: tuple[ExecutionEdge, ...] = ()
    metadata: GraphMetadata

    @field_validator("graph_id", "workflow_id", "schema_version")
    @classmethod
    def graph_identity_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identidade do grafo não pode ser vazia")
        return value

    @model_validator(mode="after")
    def graph_is_consistent(self) -> ExecutionGraph:
        node_ids = tuple(node.node_id for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("grafo contém nós duplicados")

        known_nodes = set(node_ids)
        edge_keys = tuple(
            (edge.source, edge.target, edge.edge_type)
            for edge in self.edges
        )
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("grafo contém arestas duplicadas")
        for edge in self.edges:
            if edge.source not in known_nodes or edge.target not in known_nodes:
                raise ValueError("aresta referencia nó inexistente")
            if edge.source == edge.target:
                raise ValueError("self-loop não é permitido")
        if self.metadata.total_nodes != len(self.nodes):
            raise ValueError("total_nodes diverge dos nós")
        if self.metadata.total_edges != len(self.edges):
            raise ValueError("total_edges diverge das arestas")
        expected_counts: dict[str, int] = {}
        for node in self.nodes:
            key = node.status.value
            expected_counts[key] = expected_counts.get(key, 0) + 1
        if dict(self.metadata.status_counts) != dict(
            sorted(expected_counts.items())
        ):
            raise ValueError("status_counts diverge dos nós")
        if self.metadata.schema_version != self.schema_version:
            raise ValueError("schema_version divergente nos metadados")
        return self
