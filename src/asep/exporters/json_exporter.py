"""Contrato JSON público e determinístico derivado do ExecutionGraph."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from asep.execution_graph import ExecutionGraph
from asep.exporters.errors import JsonExportError

JSON_GRAPH_FORMAT_VERSION = "1.0"


class JsonExporter:
    """Serializa um grafo sem expor modelos ou referências Python."""

    def export(self, graph: ExecutionGraph) -> str:
        payload = {
            "version": JSON_GRAPH_FORMAT_VERSION,
            "generated_at": self._generated_at(graph),
            "graph": {
                "nodes": [
                    self._node(node)
                    for node in sorted(
                        graph.nodes,
                        key=lambda item: item.node_id,
                    )
                ],
                "edges": [
                    self._edge(edge)
                    for edge in sorted(
                        graph.edges,
                        key=lambda item: (
                            item.source,
                            item.target,
                            item.edge_type.value,
                            item.label or "",
                        ),
                    )
                ],
            },
        }
        try:
            return (
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )
        except (TypeError, ValueError) as exc:
            raise JsonExportError(
                "ExecutionGraph contém valor incompatível com JSON."
            ) from exc

    @classmethod
    def _node(cls, node: Any) -> dict[str, Any]:
        execution = node.execution
        quality_gate = node.quality_gate
        return {
            "id": node.node_id,
            "type": "stage",
            "status": node.status.value,
            "provider": execution.provider_name,
            "metadata": {
                "stage_id": node.stage_id,
                "label": node.label,
                "description": node.description,
                "mode": node.mode,
                "workflow_reference": node.workflow_reference,
                "workflow_references": list(node.workflow_references),
                "agent_ids": list(node.agent_ids),
                "execution": {
                    "agent_status": cls._enum_value(
                        execution.agent_result_status
                    ),
                    "provider_status": cls._enum_value(
                        execution.provider_result_status
                    ),
                    "provider_version": execution.provider_version,
                    "started_at": cls._datetime(execution.started_at),
                    "finished_at": cls._datetime(execution.finished_at),
                    "duration_ms": execution.duration_ms,
                    "attempt": execution.attempt,
                    "exit_code": execution.exit_code,
                    "warnings": list(execution.warnings),
                    "errors": list(execution.errors),
                },
                "artifacts": [
                    {
                        "id": artifact.artifact_id,
                        "path": artifact.path,
                        "type": artifact.type,
                        "checksum": artifact.checksum,
                        "producer": artifact.agent_id,
                        "created_at": cls._datetime(artifact.created_at),
                    }
                    for artifact in sorted(
                        node.artifacts,
                        key=lambda item: (item.path, item.artifact_id),
                    )
                ],
                "quality_gate": (
                    {
                        "id": quality_gate.gate_id,
                        "decision": quality_gate.decision.value,
                        "satisfied_criteria": list(
                            quality_gate.satisfied_criteria
                        ),
                        "unsatisfied_criteria": list(
                            quality_gate.unsatisfied_criteria
                        ),
                        "evaluated_at": cls._datetime(
                            quality_gate.evaluated_at
                        ),
                    }
                    if quality_gate is not None
                    else None
                ),
                "custom": cls._json_value(node.metadata),
            },
        }

    @classmethod
    def _edge(cls, edge: Any) -> dict[str, Any]:
        return {
            "from": edge.source,
            "to": edge.target,
            "kind": edge.edge_type.value,
            "label": edge.label,
            "metadata": cls._json_value(edge.metadata),
        }

    @classmethod
    def _generated_at(cls, graph: ExecutionGraph) -> str | None:
        timestamps = [
            timestamp
            for node in graph.nodes
            for timestamp in (
                node.execution.started_at,
                node.execution.finished_at,
                (
                    node.quality_gate.evaluated_at
                    if node.quality_gate is not None
                    else None
                ),
            )
            if timestamp is not None
        ]
        if not timestamps:
            return None
        latest = max(timestamps, key=cls._utc_datetime)
        return cls._datetime(latest)

    @classmethod
    def _json_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, datetime):
            return cls._datetime(value)
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Mapping):
            return {
                str(key): cls._json_value(item)
                for key, item in sorted(
                    value.items(),
                    key=lambda pair: str(pair[0]),
                )
            }
        if isinstance(value, (list, tuple)):
            return [cls._json_value(item) for item in value]
        if isinstance(value, (set, frozenset)):
            normalized = [cls._json_value(item) for item in value]
            return sorted(
                normalized,
                key=lambda item: json.dumps(
                    item,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        raise JsonExportError(
            f"Tipo não serializável no metadata: {type(value).__name__}."
        )

    @staticmethod
    def _datetime(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _enum_value(value: Enum | None) -> str | None:
        return str(value.value) if value is not None else None

    @staticmethod
    def _utc_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
