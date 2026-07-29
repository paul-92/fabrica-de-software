"""Exportação pura e determinística de ExecutionGraph para Mermaid."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from asep.execution_graph import (
    EdgeType,
    ExecutionGraph,
    NodeStatus,
)
from asep.exporters.errors import MermaidExportError


class MermaidDirection(StrEnum):
    TD = "TD"
    TB = "TB"
    LR = "LR"
    RL = "RL"
    BT = "BT"


class MermaidExportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    direction: MermaidDirection = MermaidDirection.TD
    include_status_styles: bool = True


_STATUS_STYLES: dict[NodeStatus, str] = {
    NodeStatus.PENDING: "fill:#f8f9fa,stroke:#adb5bd",
    NodeStatus.READY: "fill:#e7f1ff,stroke:#0d6efd",
    NodeStatus.RUNNING: "fill:#fff3cd,stroke:#ffc107",
    NodeStatus.AWAITING_APPROVAL: "fill:#e2d9f3,stroke:#6f42c1",
    NodeStatus.COMPLETED: "fill:#d1e7dd,stroke:#198754",
    NodeStatus.FAILED: "fill:#f8d7da,stroke:#dc3545",
    NodeStatus.BLOCKED: "fill:#e2e3e5,stroke:#6c757d",
    NodeStatus.SKIPPED: (
        "fill:#f8f9fa,stroke:#6c757d,stroke-dasharray:5 5"
    ),
    NodeStatus.CANCELLED: "fill:#e2e3e5,stroke:#343a40",
    NodeStatus.PARTIAL: "fill:#ffe5d0,stroke:#fd7e14",
}

_RESERVED_IDS = {
    "class",
    "classdef",
    "click",
    "end",
    "flowchart",
    "graph",
    "linkstyle",
    "style",
    "subgraph",
}


class MermaidExporter:
    def export(
        self,
        graph: ExecutionGraph,
        options: MermaidExportOptions | None = None,
    ) -> str:
        selected = options or MermaidExportOptions()
        identifiers = self._identifiers(
            tuple(node.node_id for node in graph.nodes)
        )
        lines = [f"flowchart {selected.direction.value}"]

        for node in graph.nodes:
            identifier = identifiers[node.node_id]
            label = self._escape_label(
                node.label or node.stage_id or node.node_id
            )
            lines.append(f'    {identifier}["{label}"]')

        if graph.edges:
            lines.append("")
            for edge in graph.edges:
                try:
                    source = identifiers[edge.source]
                    target = identifiers[edge.target]
                except KeyError as exc:
                    raise MermaidExportError(
                        "Aresta referencia nó ausente no grafo."
                    ) from exc
                connector = self._connector(edge.edge_type)
                if edge.label:
                    label = self._escape_label(edge.label)
                    lines.append(
                        f'    {source} {connector}|"{label}"| {target}'
                    )
                else:
                    lines.append(f"    {source} {connector} {target}")

        if selected.include_status_styles and graph.nodes:
            used_statuses = {
                node.status for node in graph.nodes
            }
            lines.append("")
            for status in NodeStatus:
                if status in used_statuses:
                    lines.append(
                        f"    classDef {status.value} "
                        f"{_STATUS_STYLES[status]}"
                    )
            lines.append("")
            for node in graph.nodes:
                lines.append(
                    f"    class {identifiers[node.node_id]} "
                    f"{node.status.value}"
                )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _connector(edge_type: EdgeType) -> str:
        connectors = {EdgeType.DEPENDENCY: "-->"}
        try:
            return connectors[edge_type]
        except KeyError as exc:
            raise MermaidExportError(
                f"EdgeType não suportado: {edge_type}"
            ) from exc

    @classmethod
    def _identifiers(
        cls, node_ids: tuple[str, ...]
    ) -> dict[str, str]:
        base_by_id = {
            node_id: cls._sanitize_identifier(node_id)
            for node_id in node_ids
        }
        ids_by_base: dict[str, list[str]] = {}
        for node_id, base in base_by_id.items():
            ids_by_base.setdefault(base, []).append(node_id)

        resolved: dict[str, str] = {}
        used: set[str] = set()
        for base in sorted(ids_by_base):
            colliding = sorted(ids_by_base[base])
            for index, node_id in enumerate(colliding):
                candidate = base
                if index > 0 or candidate in used:
                    digest = hashlib.sha256(
                        node_id.encode("utf-8")
                    ).hexdigest()
                    length = 8
                    candidate = f"{base}_{digest[:length]}"
                    while candidate in used and length < len(digest):
                        length += 4
                        candidate = f"{base}_{digest[:length]}"
                if candidate in used:
                    raise MermaidExportError(
                        "Não foi possível gerar identificadores únicos."
                    )
                resolved[node_id] = candidate
                used.add(candidate)
        return resolved

    @staticmethod
    def _sanitize_identifier(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", ascii_value)
        safe = re.sub(r"_+", "_", safe).strip("_")
        if not safe:
            safe = "node"
        if safe[0].isdigit():
            safe = f"node_{safe}"
        if safe.casefold() in _RESERVED_IDS:
            safe = f"node_{safe}"
        return safe

    @staticmethod
    def _escape_label(value: str) -> str:
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        escaped = html.escape(normalized, quote=True)
        return (
            escaped.replace("\\", "&#92;")
            .replace("[", "&#91;")
            .replace("]", "&#93;")
            .replace("\n", "<br/>")
        )
