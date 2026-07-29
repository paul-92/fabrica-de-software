"""Modelo canônico e imutável de grafos de execução."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from asep.execution.models import (
    AgentResultStatus,
    ExecutionStatus,
    GateDecision,
)
from asep.providers.models import AgentExecutionStatus


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class EdgeType(StrEnum):
    DEPENDENCY = "dependency"


class GraphMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    workflow_id: str
    workflow_name: str
    workflow_version: str
    run_id: str | None = None
    project_id: str | None = None
    execution_status: ExecutionStatus | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ExecutionNode(BaseModel):
    """Snapshot de uma etapa, sem incorporar modelos mutáveis de runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    mode: str
    workflow_reference: str | None = None
    workflow_references: tuple[str, ...] = ()
    status: NodeStatus = NodeStatus.PENDING
    agent_ids: tuple[str, ...] = ()
    quality_gate_id: str | None = None
    agent_result_status: AgentResultStatus | None = None
    provider_result_status: AgentExecutionStatus | None = None
    gate_decision: GateDecision | None = None
    artifact_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class ExecutionEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    target: str
    type: EdgeType = EdgeType.DEPENDENCY


class ExecutionGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: GraphMetadata
    nodes: tuple[ExecutionNode, ...]
    edges: tuple[ExecutionEdge, ...] = ()

    @model_validator(mode="after")
    def graph_is_consistent(self) -> ExecutionGraph:
        node_ids = tuple(node.id for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("grafo contém nós duplicados")

        known_nodes = set(node_ids)
        edge_keys = tuple(
            (edge.source, edge.target, edge.type) for edge in self.edges
        )
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("grafo contém arestas duplicadas")
        for edge in self.edges:
            if edge.source not in known_nodes or edge.target not in known_nodes:
                raise ValueError("aresta referencia nó inexistente")
            if edge.source == edge.target:
                raise ValueError("auto dependência não é permitida")
        return self
