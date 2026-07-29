"""API pública do modelo canônico de grafos de execução."""

from asep.execution_graph.builder import ExecutionGraphBuilder
from asep.execution_graph.errors import (
    ExecutionGraphError,
    InvalidGraphError,
)
from asep.execution_graph.models import (
    EXECUTION_GRAPH_SCHEMA_VERSION,
    EdgeType,
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    GraphMetadata,
    NodeExecutionDetails,
    NodeStatus,
    QualityGateSummary,
)
from asep.execution_graph.serializer import ExecutionGraphSerializer

__all__ = [
    "EdgeType",
    "EXECUTION_GRAPH_SCHEMA_VERSION",
    "ExecutionEdge",
    "ExecutionGraph",
    "ExecutionGraphBuilder",
    "ExecutionGraphError",
    "ExecutionGraphSerializer",
    "ExecutionNode",
    "GraphMetadata",
    "InvalidGraphError",
    "NodeExecutionDetails",
    "NodeStatus",
    "QualityGateSummary",
]
