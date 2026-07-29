"""Exportação pura e determinística de ExecutionGraph para BPMN 2.0."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from xml.etree import ElementTree as ET

from pydantic import BaseModel, ConfigDict, Field

from asep.execution_graph import EdgeType, ExecutionGraph
from asep.exporters.bpmn_layout import BpmnLayoutEngine
from asep.exporters.bpmn_models import (
    BpmnFlow,
    BpmnNode,
    BpmnNodeKind,
    BpmnProcessModel,
)
from asep.exporters.errors import (
    BpmnExportError,
    UnsupportedBpmnGraphError,
)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

for _prefix, _namespace in (
    ("bpmn", BPMN_NS),
    ("bpmndi", BPMNDI_NS),
    ("dc", DC_NS),
    ("di", DI_NS),
    ("xsi", XSI_NS),
):
    ET.register_namespace(_prefix, _namespace)


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


class BpmnExportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_namespace: str = Field(
        default="https://asep.dev/schema/bpmn",
        min_length=1,
    )
    exporter: str = Field(default="ASEP", min_length=1)
    exporter_version: str = Field(default="0.1.0", min_length=1)


class _IdRegistry:
    def __init__(self) -> None:
        self._used: set[str] = set()

    def create(self, prefix: str, source: str) -> str:
        safe = self._sanitize(source)
        candidate = f"{prefix}_{safe}"
        if candidate in self._used:
            digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
            length = 8
            candidate = f"{prefix}_{safe}_{digest[:length]}"
            while candidate in self._used and length < len(digest):
                length += 4
                candidate = f"{prefix}_{safe}_{digest[:length]}"
        if candidate in self._used:
            raise BpmnExportError("Não foi possível gerar IDs BPMN únicos.")
        self._used.add(candidate)
        return candidate

    @staticmethod
    def _sanitize(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", ascii_value)
        safe = re.sub(r"_+", "_", safe).strip("_")
        if not safe:
            safe = "element"
        if not re.match(r"[A-Za-z_]", safe):
            safe = f"node_{safe}"
        return safe


class BpmnExporter:
    def export(
        self,
        graph: ExecutionGraph,
        options: BpmnExportOptions | None = None,
    ) -> str:
        selected = options or BpmnExportOptions()
        ids = _IdRegistry()
        definitions_id = ids.create("Definitions", graph.graph_id)
        process_id = ids.create("Process", graph.graph_id)
        diagram_id = ids.create("Diagram", graph.graph_id)
        plane_id = ids.create("Plane", graph.graph_id)
        model = self._process_model(graph, ids)
        layout = BpmnLayoutEngine().layout(model)

        root = ET.Element(
            _tag(BPMN_NS, "definitions"),
            {
                "id": definitions_id,
                "targetNamespace": selected.target_namespace,
                "exporter": selected.exporter,
                "exporterVersion": selected.exporter_version,
                "xmlns:xsi": XSI_NS,
            },
        )
        process = ET.SubElement(
            root,
            _tag(BPMN_NS, "process"),
            {
                "id": process_id,
                "name": (
                    graph.metadata.workflow_name
                    or graph.workflow_id
                    or graph.graph_id
                ),
                "isExecutable": "false",
            },
        )
        incoming, outgoing = self._flow_references(model)
        for node in model.nodes:
            element = ET.SubElement(
                process,
                _tag(BPMN_NS, node.kind.value),
                {
                    "id": node.element_id,
                    **({"name": node.name} if node.name else {}),
                },
            )
            for flow_id in incoming[node.element_id]:
                ET.SubElement(element, _tag(BPMN_NS, "incoming")).text = (
                    flow_id
                )
            for flow_id in outgoing[node.element_id]:
                ET.SubElement(element, _tag(BPMN_NS, "outgoing")).text = (
                    flow_id
                )
        for flow in model.flows:
            ET.SubElement(
                process,
                _tag(BPMN_NS, "sequenceFlow"),
                {
                    "id": flow.flow_id,
                    "sourceRef": flow.source_ref,
                    "targetRef": flow.target_ref,
                    **({"name": flow.name} if flow.name else {}),
                },
            )

        diagram = ET.SubElement(
            root,
            _tag(BPMNDI_NS, "BPMNDiagram"),
            {"id": diagram_id},
        )
        plane = ET.SubElement(
            diagram,
            _tag(BPMNDI_NS, "BPMNPlane"),
            {"id": plane_id, "bpmnElement": process_id},
        )
        for node in model.nodes:
            shape_id = ids.create("Shape", node.element_id)
            shape = ET.SubElement(
                plane,
                _tag(BPMNDI_NS, "BPMNShape"),
                {"id": shape_id, "bpmnElement": node.element_id},
            )
            bounds = layout.bounds[node.element_id]
            ET.SubElement(
                shape,
                _tag(DC_NS, "Bounds"),
                {
                    "x": self._number(bounds.x),
                    "y": self._number(bounds.y),
                    "width": self._number(bounds.width),
                    "height": self._number(bounds.height),
                },
            )
        for positioned in layout.flows:
            edge_id = ids.create("Edge", positioned.flow.flow_id)
            edge = ET.SubElement(
                plane,
                _tag(BPMNDI_NS, "BPMNEdge"),
                {
                    "id": edge_id,
                    "bpmnElement": positioned.flow.flow_id,
                },
            )
            for x, y in positioned.waypoints:
                ET.SubElement(
                    edge,
                    _tag(DI_NS, "waypoint"),
                    {"x": self._number(x), "y": self._number(y)},
                )

        ET.indent(root, space="  ")
        content = ET.tostring(
            root,
            encoding="unicode",
            short_empty_elements=True,
        )
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + content + "\n"

    def _process_model(
        self, graph: ExecutionGraph, ids: _IdRegistry
    ) -> BpmnProcessModel:
        for edge in graph.edges:
            if edge.edge_type is not EdgeType.DEPENDENCY:
                raise UnsupportedBpmnGraphError(
                    f"EdgeType BPMN não suportado: {edge.edge_type}"
                )

        node_ids = tuple(sorted(node.node_id for node in graph.nodes))
        task_ids = {
            node_id: ids.create("Task", node_id) for node_id in node_ids
        }
        labels = {node.node_id: node.label for node in graph.nodes}
        incoming: dict[str, list[str]] = {
            node_id: [] for node_id in node_ids
        }
        outgoing: dict[str, list[str]] = {
            node_id: [] for node_id in node_ids
        }
        edge_labels: dict[tuple[str, str], str | None] = {}
        for edge in sorted(
            graph.edges, key=lambda item: (item.source, item.target)
        ):
            outgoing[edge.source].append(edge.target)
            incoming[edge.target].append(edge.source)
            edge_labels[(edge.source, edge.target)] = edge.label

        start_id = ids.create("StartEvent", graph.graph_id)
        end_id = ids.create("EndEvent", graph.graph_id)
        nodes = [
            BpmnNode(start_id, BpmnNodeKind.START_EVENT, "Start"),
            *(
                BpmnNode(
                    task_ids[node_id],
                    BpmnNodeKind.TASK,
                    labels[node_id],
                )
                for node_id in node_ids
            ),
            BpmnNode(end_id, BpmnNodeKind.END_EVENT, "End"),
        ]
        split_ids = {
            node_id: ids.create("GatewaySplit", node_id)
            for node_id in node_ids
            if len(outgoing[node_id]) > 1
        }
        join_ids = {
            node_id: ids.create("GatewayJoin", node_id)
            for node_id in node_ids
            if len(incoming[node_id]) > 1
        }
        nodes.extend(
            BpmnNode(gateway_id, BpmnNodeKind.PARALLEL_GATEWAY)
            for gateway_id in sorted((*split_ids.values(), *join_ids.values()))
        )
        roots = tuple(
            node_id for node_id in node_ids if not incoming[node_id]
        )
        finals = tuple(
            node_id for node_id in node_ids if not outgoing[node_id]
        )
        if node_ids and (not roots or not finals):
            raise UnsupportedBpmnGraphError(
                "ExecutionGraph cíclico não pode ser exportado para BPMN."
            )
        root_gateway = (
            ids.create("GatewaySplit", f"{graph.graph_id}:roots")
            if len(roots) > 1
            else None
        )
        final_gateway = (
            ids.create("GatewayJoin", f"{graph.graph_id}:finals")
            if len(finals) > 1
            else None
        )
        if root_gateway:
            nodes.append(
                BpmnNode(root_gateway, BpmnNodeKind.PARALLEL_GATEWAY)
            )
        if final_gateway:
            nodes.append(
                BpmnNode(final_gateway, BpmnNodeKind.PARALLEL_GATEWAY)
            )

        connections: list[tuple[str, str, str | None, str]] = []
        if not node_ids:
            connections.append((start_id, end_id, None, "empty"))
        else:
            root_target = root_gateway
            if root_target:
                connections.append(
                    (start_id, root_target, None, "start_roots")
                )
                for root in roots:
                    connections.append(
                        (
                            root_target,
                            task_ids[root],
                            None,
                            f"root:{root}",
                        )
                    )
            else:
                connections.append(
                    (start_id, task_ids[roots[0]], None, "start_root")
                )

            for node_id, gateway_id in sorted(split_ids.items()):
                connections.append(
                    (
                        task_ids[node_id],
                        gateway_id,
                        None,
                        f"split:{node_id}",
                    )
                )
            for node_id, gateway_id in sorted(join_ids.items()):
                connections.append(
                    (
                        gateway_id,
                        task_ids[node_id],
                        None,
                        f"join:{node_id}",
                    )
                )
            for edge in sorted(
                graph.edges, key=lambda item: (item.source, item.target)
            ):
                connections.append(
                    (
                        split_ids.get(edge.source, task_ids[edge.source]),
                        join_ids.get(edge.target, task_ids[edge.target]),
                        edge_labels[(edge.source, edge.target)],
                        f"dependency:{edge.source}:{edge.target}",
                    )
                )

            if final_gateway:
                for final in finals:
                    connections.append(
                        (
                            task_ids[final],
                            final_gateway,
                            None,
                            f"final:{final}",
                        )
                    )
                connections.append(
                    (final_gateway, end_id, None, "finals_end")
                )
            else:
                connections.append(
                    (task_ids[finals[0]], end_id, None, "final_end")
                )

        flows = tuple(
            BpmnFlow(
                flow_id=ids.create("Flow", key),
                source_ref=source,
                target_ref=target,
                name=name,
            )
            for source, target, name, key in connections
        )
        return BpmnProcessModel(nodes=tuple(nodes), flows=flows)

    @staticmethod
    def _flow_references(
        model: BpmnProcessModel,
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        incoming: dict[str, list[str]] = defaultdict(list)
        outgoing: dict[str, list[str]] = defaultdict(list)
        for flow in model.flows:
            incoming[flow.target_ref].append(flow.flow_id)
            outgoing[flow.source_ref].append(flow.flow_id)
        return incoming, outgoing

    @staticmethod
    def _number(value: float) -> str:
        return str(int(value)) if value.is_integer() else f"{value:.2f}"
