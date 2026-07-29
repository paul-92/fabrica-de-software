from __future__ import annotations

import inspect
import re
from xml.etree import ElementTree as ET

import pytest
from pydantic import ValidationError

from asep.execution_graph import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    GraphMetadata,
    NodeStatus,
)
from asep.exporters import (
    BpmnExporter,
    BpmnExportError,
    BpmnExportOptions,
)
from asep.exporters.bpmn import (
    BPMNDI_NS,
    BPMN_NS,
    DC_NS,
    DI_NS,
    XSI_NS,
)
from asep.exporters.errors import UnsupportedBpmnGraphError

NS = {
    "bpmn": BPMN_NS,
    "bpmndi": BPMNDI_NS,
    "dc": DC_NS,
    "di": DI_NS,
}


def node(node_id: str, *, label: str | None = None) -> ExecutionNode:
    return ExecutionNode(
        node_id=node_id,
        stage_id=node_id,
        label=label or node_id,
        mode="sequential",
        status=NodeStatus.PENDING,
    )


def graph(
    nodes: tuple[ExecutionNode, ...],
    pairs: tuple[tuple[str, str], ...] = (),
) -> ExecutionGraph:
    return ExecutionGraph(
        graph_id="workflow:test:1.0",
        workflow_id="test",
        nodes=nodes,
        edges=tuple(
            ExecutionEdge(source=source, target=target)
            for source, target in pairs
        ),
        metadata=GraphMetadata(
            workflow_name="Test workflow",
            created_from="test",
            total_nodes=len(nodes),
            total_edges=len(pairs),
            status_counts={"pending": len(nodes)} if nodes else {},
        ),
    )


def parse(source: ExecutionGraph) -> tuple[str, ET.Element]:
    xml = BpmnExporter().export(source)
    return xml, ET.fromstring(xml)


def process(root: ET.Element) -> ET.Element:
    result = root.find("bpmn:process", NS)
    assert result is not None
    return result


def ids(root: ET.Element) -> list[str]:
    return [
        value
        for element in root.iter()
        if (value := element.get("id")) is not None
    ]


def flow_pairs(root: ET.Element) -> set[tuple[str, str]]:
    return {
        (flow.attrib["sourceRef"], flow.attrib["targetRef"])
        for flow in root.findall(".//bpmn:sequenceFlow", NS)
    }


def tasks(root: ET.Element) -> dict[str, ET.Element]:
    return {
        item.attrib["name"]: item
        for item in root.findall(".//bpmn:task", NS)
    }


def test_exports_complete_linear_workflow() -> None:
    source = graph(
        (node("requirements"), node("architecture"), node("tests")),
        (
            ("requirements", "architecture"),
            ("architecture", "tests"),
        ),
    )

    _, root = parse(source)
    task_by_name = tasks(root)
    pairs = flow_pairs(root)
    start = root.find(".//bpmn:startEvent", NS)
    end = root.find(".//bpmn:endEvent", NS)

    assert start is not None
    assert end is not None
    assert len(task_by_name) == 3
    assert not root.findall(".//bpmn:parallelGateway", NS)
    assert (start.attrib["id"], task_by_name["requirements"].attrib["id"]) in pairs
    assert (
        task_by_name["requirements"].attrib["id"],
        task_by_name["architecture"].attrib["id"],
    ) in pairs
    assert (
        task_by_name["architecture"].attrib["id"],
        task_by_name["tests"].attrib["id"],
    ) in pairs
    assert (task_by_name["tests"].attrib["id"], end.attrib["id"]) in pairs


def test_parallel_workflow_creates_split_and_join_gateways() -> None:
    source = graph(
        tuple(node(item) for item in ("a", "b", "c", "d")),
        (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")),
    )

    _, root = parse(source)
    gateways = root.findall(".//bpmn:parallelGateway", NS)
    pairs = flow_pairs(root)
    task_by_name = tasks(root)

    assert len(gateways) == 2
    split = next(
        item
        for item in gateways
        if (task_by_name["a"].attrib["id"], item.attrib["id"]) in pairs
    )
    join = next(
        item
        for item in gateways
        if (item.attrib["id"], task_by_name["d"].attrib["id"]) in pairs
    )
    assert {
        target
        for source_id, target in pairs
        if source_id == split.attrib["id"]
    } == {
        task_by_name["b"].attrib["id"],
        task_by_name["c"].attrib["id"],
    }
    assert {
        source_id
        for source_id, target in pairs
        if target == join.attrib["id"]
    } == {
        task_by_name["b"].attrib["id"],
        task_by_name["c"].attrib["id"],
    }


@pytest.mark.parametrize(
    ("pairs", "gateway_count"),
    [
        ((("a", "b"), ("a", "c")), 2),
        ((("a", "c"), ("b", "c")), 2),
    ],
)
def test_split_or_join_also_handles_multiple_finals_or_roots(
    pairs: tuple[tuple[str, str], ...],
    gateway_count: int,
) -> None:
    _, root = parse(graph(tuple(node(item) for item in ("a", "b", "c")), pairs))

    assert len(root.findall(".//bpmn:parallelGateway", NS)) == gateway_count


def test_empty_graph_is_start_directly_to_end() -> None:
    _, root = parse(graph(()))
    start = root.find(".//bpmn:startEvent", NS)
    end = root.find(".//bpmn:endEvent", NS)

    assert start is not None and end is not None
    assert flow_pairs(root) == {(start.attrib["id"], end.attrib["id"])}
    assert not root.findall(".//bpmn:task", NS)


def test_one_isolated_node_is_between_events_without_gateway() -> None:
    _, root = parse(graph((node("only"),)))

    assert len(root.findall(".//bpmn:task", NS)) == 1
    assert len(root.findall(".//bpmn:sequenceFlow", NS)) == 2
    assert not root.findall(".//bpmn:parallelGateway", NS)


def test_multiple_isolated_nodes_use_root_split_and_final_join() -> None:
    _, root = parse(graph((node("a"), node("b"), node("c"))))
    gateways = root.findall(".//bpmn:parallelGateway", NS)
    pairs = flow_pairs(root)

    assert len(gateways) == 2
    assert sorted(
        sum(source == item.attrib["id"] for source, _ in pairs)
        for item in gateways
    ) == [1, 3]
    assert sorted(
        sum(target == item.attrib["id"] for _, target in pairs)
        for item in gateways
    ) == [1, 3]


def test_definitions_process_namespaces_and_configuration() -> None:
    xml = BpmnExporter().export(
        graph(()),
        BpmnExportOptions(
            target_namespace="https://example.test/bpmn",
            exporter="ASEP Test",
            exporter_version="9.1",
        ),
    )
    root = ET.fromstring(xml)
    proc = process(root)

    assert root.tag == f"{{{BPMN_NS}}}definitions"
    assert root.attrib["targetNamespace"] == "https://example.test/bpmn"
    assert root.attrib["exporter"] == "ASEP Test"
    assert root.attrib["exporterVersion"] == "9.1"
    assert proc.attrib["name"] == "Test workflow"
    assert proc.attrib["isExecutable"] == "false"
    for namespace in (BPMN_NS, BPMNDI_NS, DC_NS, DI_NS, XSI_NS):
        assert namespace in xml


def test_options_are_strict_and_typed() -> None:
    with pytest.raises(ValidationError):
        BpmnExportOptions(other=True)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "label",
    (
        "Backend API",
        "Área técnica 東京",
        'A & B < "C" > D',
        "Linha 1\nLinha 2's",
    ),
)
def test_labels_round_trip_through_xml(label: str) -> None:
    xml, root = parse(graph((node("stage", label=label),)))

    assert tasks(root)[label].attrib["name"] == label
    assert xml.encode("utf-8").decode("utf-8") == xml


def test_ids_are_xml_safe_unique_and_collisions_are_deterministic() -> None:
    source = graph(
        (
            node("backend api"),
            node("backend-api"),
            node("01 requirements"),
            node("東京"),
        )
    )
    first, root = parse(source)
    second = BpmnExporter().export(source)
    all_ids = ids(root)

    assert first == second
    assert len(all_ids) == len(set(all_ids))
    assert all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", item) for item in all_ids)
    task_ids = [item.attrib["id"] for item in root.findall(".//bpmn:task", NS)]
    assert any(re.search(r"_[0-9a-f]{8}$", item) for item in task_ids)


def test_xml_contains_complete_deterministic_di() -> None:
    source = graph(
        (node("a"), node("b")),
        (("a", "b"),),
    )
    first, root = parse(source)
    plane = root.find(".//bpmndi:BPMNPlane", NS)
    shapes = root.findall(".//bpmndi:BPMNShape", NS)
    edges = root.findall(".//bpmndi:BPMNEdge", NS)
    semantic_ids = set(ids(process(root)))
    flow_ids = {
        flow.attrib["id"]
        for flow in root.findall(".//bpmn:sequenceFlow", NS)
    }

    assert plane is not None
    assert len(shapes) == 4
    assert len(edges) == 3
    assert {item.attrib["bpmnElement"] for item in shapes} <= semantic_ids
    assert {item.attrib["bpmnElement"] for item in edges} == flow_ids
    assert all(item.find("dc:Bounds", NS) is not None for item in shapes)
    assert all(len(item.findall("di:waypoint", NS)) >= 2 for item in edges)
    assert first == BpmnExporter().export(source)


def test_layout_is_non_negative_and_stable_for_parallel_graph() -> None:
    source = graph(
        tuple(node(item) for item in ("a", "b", "c", "d")),
        (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")),
    )
    first, root = parse(source)
    values = [
        float(bounds.attrib[key])
        for bounds in root.findall(".//dc:Bounds", NS)
        for key in ("x", "y", "width", "height")
    ] + [
        float(point.attrib[key])
        for point in root.findall(".//di:waypoint", NS)
        for key in ("x", "y")
    ]

    assert min(values) >= 0
    assert first == BpmnExporter().export(source)


def test_every_flow_reference_and_incoming_outgoing_is_valid() -> None:
    _, root = parse(
        graph(
            tuple(node(item) for item in ("a", "b", "c")),
            (("a", "c"), ("b", "c")),
        )
    )
    proc = process(root)
    node_ids = {
        item.attrib["id"]
        for item in proc
        if item.tag
        in {
            f"{{{BPMN_NS}}}startEvent",
            f"{{{BPMN_NS}}}endEvent",
            f"{{{BPMN_NS}}}task",
            f"{{{BPMN_NS}}}parallelGateway",
        }
    }
    flows = proc.findall("bpmn:sequenceFlow", NS)
    flow_ids = {item.attrib["id"] for item in flows}
    references = {
        child.text
        for item in proc
        for child in item
        if child.tag in {f"{{{BPMN_NS}}}incoming", f"{{{BPMN_NS}}}outgoing"}
    }

    assert all(item.attrib["sourceRef"] in node_ids for item in flows)
    assert all(item.attrib["targetRef"] in node_ids for item in flows)
    assert references == flow_ids


def test_all_semantic_nodes_are_reachable_from_start_and_reach_end() -> None:
    _, root = parse(
        graph(
            tuple(node(item) for item in ("a", "b", "c", "d")),
            (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")),
        )
    )
    pairs = flow_pairs(root)
    start = root.find(".//bpmn:startEvent", NS)
    end = root.find(".//bpmn:endEvent", NS)
    assert start is not None and end is not None
    semantic = {
        item.attrib["id"]
        for item in process(root)
        if "id" in item.attrib and item.tag != f"{{{BPMN_NS}}}sequenceFlow"
    }

    def reachable(origin: str, links: set[tuple[str, str]]) -> set[str]:
        seen = {origin}
        while True:
            expanded = seen | {target for source, target in links if source in seen}
            if expanded == seen:
                return seen
            seen = expanded

    assert semantic <= reachable(start.attrib["id"], pairs)
    reverse = {(target, source) for source, target in pairs}
    assert semantic <= reachable(end.attrib["id"], reverse)


def test_cyclic_graph_fails_with_specific_error() -> None:
    source = graph(
        (node("a"), node("b")),
        (("a", "b"), ("b", "a")),
    )

    with pytest.raises(UnsupportedBpmnGraphError, match="cíclico"):
        BpmnExporter().export(source)


def test_export_does_not_modify_graph_and_uses_lf_final_newline() -> None:
    source = graph((node("a"), node("b")), (("a", "b"),))
    before = source.model_dump(mode="json")

    xml = BpmnExporter().export(source)

    assert source.model_dump(mode="json") == before
    assert "\r" not in xml
    assert xml.endswith("\n")
    assert not xml.endswith("\n\n")


def test_public_exports_are_intentional() -> None:
    import asep.exporters as exporters

    assert {
        "BpmnExporter",
        "BpmnExportError",
        "BpmnExportOptions",
    } <= set(exporters.__all__)
    assert issubclass(UnsupportedBpmnGraphError, BpmnExportError)


def test_exporter_has_no_forbidden_architecture_dependencies() -> None:
    import asep.exporters.bpmn as bpmn
    import asep.exporters.bpmn_layout as layout
    import asep.exporters.bpmn_models as models

    source = "\n".join(
        inspect.getsource(module) for module in (bpmn, layout, models)
    )
    for forbidden in (
        "asep.workflow",
        "asep.orchestrator",
        "asep.application",
        "asep.providers",
        "asep.execution_package",
        "asep.artifacts",
        "asep.quality",
    ):
        assert forbidden not in source
