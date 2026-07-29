from __future__ import annotations

import inspect
import re

import pytest
from pydantic import ValidationError

from asep.execution_graph import (
    EdgeType,
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    GraphMetadata,
    NodeStatus,
)
from asep.exporters import (
    MermaidDirection,
    MermaidExporter,
    MermaidExportError,
    MermaidExportOptions,
)


def node(
    node_id: str,
    *,
    label: str | None = None,
    status: NodeStatus = NodeStatus.PENDING,
) -> ExecutionNode:
    return ExecutionNode(
        node_id=node_id,
        stage_id=node_id,
        label=label or node_id,
        mode="sequential",
        status=status,
    )


def graph(
    nodes: tuple[ExecutionNode, ...],
    edges: tuple[ExecutionEdge, ...] = (),
) -> ExecutionGraph:
    counts: dict[str, int] = {}
    for item in nodes:
        counts[item.status.value] = counts.get(item.status.value, 0) + 1
    return ExecutionGraph(
        graph_id="workflow:test:1.0",
        workflow_id="test",
        nodes=nodes,
        edges=edges,
        metadata=GraphMetadata(
            workflow_name="Test",
            created_from="test",
            total_nodes=len(nodes),
            total_edges=len(edges),
            status_counts=counts,
        ),
    )


def test_exports_complete_linear_workflow() -> None:
    source = graph(
        (
            node("requirements", label="Requirements"),
            node("architecture", label="Architecture"),
            node("tests", label="Tests"),
        ),
        (
            ExecutionEdge(
                source="requirements",
                target="architecture",
            ),
            ExecutionEdge(source="architecture", target="tests"),
        ),
    )

    diagram = MermaidExporter().export(source)

    assert diagram == (
        "flowchart TD\n"
        '    requirements["Requirements"]\n'
        '    architecture["Architecture"]\n'
        '    tests["Tests"]\n'
        "\n"
        "    requirements --> architecture\n"
        "    architecture --> tests\n"
        "\n"
        "    classDef pending fill:#f8f9fa,stroke:#adb5bd\n"
        "\n"
        "    class requirements pending\n"
        "    class architecture pending\n"
        "    class tests pending\n"
    )


def test_parallel_workflow_is_reflected_only_by_edges() -> None:
    source = graph(
        tuple(
            node(item)
            for item in (
                "architecture",
                "backend",
                "frontend",
                "tests",
            )
        ),
        (
            ExecutionEdge(source="architecture", target="backend"),
            ExecutionEdge(source="architecture", target="frontend"),
            ExecutionEdge(source="backend", target="tests"),
            ExecutionEdge(source="frontend", target="tests"),
        ),
    )

    diagram = MermaidExporter().export(source)

    assert "    architecture --> backend\n" in diagram
    assert "    architecture --> frontend\n" in diagram
    assert "    backend --> tests\n" in diagram
    assert "    frontend --> tests\n" in diagram
    assert "subgraph" not in diagram


def test_empty_graph_returns_minimal_valid_mermaid() -> None:
    assert MermaidExporter().export(graph(())) == "flowchart TD\n"


def test_isolated_node_is_declared_without_edge() -> None:
    diagram = MermaidExporter().export(graph((node("analysis"),)))

    assert '    analysis["analysis"]\n' in diagram
    assert "-->" not in diagram


def test_multiple_isolated_nodes_preserve_canonical_graph_order() -> None:
    diagram = MermaidExporter().export(
        graph((node("alpha"), node("middle"), node("zeta")))
    )

    assert diagram.index('alpha["alpha"]') < diagram.index(
        'middle["middle"]'
    ) < diagram.index('zeta["zeta"]')


def test_default_direction_is_td() -> None:
    assert MermaidExporter().export(graph(())).startswith("flowchart TD\n")


@pytest.mark.parametrize(
    "direction",
    tuple(MermaidDirection),
)
def test_supports_each_valid_direction(
    direction: MermaidDirection,
) -> None:
    result = MermaidExporter().export(
        graph(()),
        MermaidExportOptions(direction=direction),
    )

    assert result == f"flowchart {direction.value}\n"


def test_rejects_invalid_direction() -> None:
    with pytest.raises(ValidationError):
        MermaidExportOptions(direction="SIDEWAYS")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status", "expected_style"),
    [
        (NodeStatus.PENDING, "fill:#f8f9fa,stroke:#adb5bd"),
        (NodeStatus.READY, "fill:#e7f1ff,stroke:#0d6efd"),
        (NodeStatus.RUNNING, "fill:#fff3cd,stroke:#ffc107"),
        (
            NodeStatus.AWAITING_APPROVAL,
            "fill:#e2d9f3,stroke:#6f42c1",
        ),
        (NodeStatus.COMPLETED, "fill:#d1e7dd,stroke:#198754"),
        (NodeStatus.FAILED, "fill:#f8d7da,stroke:#dc3545"),
        (NodeStatus.BLOCKED, "fill:#e2e3e5,stroke:#6c757d"),
        (
            NodeStatus.SKIPPED,
            "fill:#f8f9fa,stroke:#6c757d,stroke-dasharray:5 5",
        ),
        (NodeStatus.CANCELLED, "fill:#e2e3e5,stroke:#343a40"),
        (NodeStatus.PARTIAL, "fill:#ffe5d0,stroke:#fd7e14"),
    ],
)
def test_maps_every_node_status_to_class_and_style(
    status: NodeStatus,
    expected_style: str,
) -> None:
    diagram = MermaidExporter().export(
        graph((node("stage", status=status),))
    )

    assert f"    classDef {status.value} {expected_style}\n" in diagram
    assert f"    class stage {status.value}\n" in diagram


def test_emits_only_styles_used_by_nodes() -> None:
    diagram = MermaidExporter().export(
        graph(
            (
                node("done", status=NodeStatus.COMPLETED),
                node("active", status=NodeStatus.RUNNING),
            )
        )
    )

    assert "classDef completed " in diagram
    assert "classDef running " in diagram
    assert "classDef failed " not in diagram
    assert "classDef pending " not in diagram


def test_can_disable_status_styles_and_class_assignments() -> None:
    diagram = MermaidExporter().export(
        graph((node("analysis"),)),
        MermaidExportOptions(include_status_styles=False),
    )

    assert "classDef" not in diagram
    assert "class analysis" not in diagram


@pytest.mark.parametrize(
    ("label", "escaped"),
    [
        ("Backend API", "Backend API"),
        ('Review "critical"', "Review &quot;critical&quot;"),
        ("Array[item]", "Array&#91;item&#93;"),
        ("Line one\nLine two", "Line one<br/>Line two"),
        ("Área técnica", "Área técnica"),
        (r"C:\project", "C:&#92;project"),
        ("Status: ready", "Status: ready"),
        ("A & B < C", "A &amp; B &lt; C"),
    ],
)
def test_escapes_labels_without_silently_removing_content(
    label: str,
    escaped: str,
) -> None:
    diagram = MermaidExporter().export(
        graph((node("stage", label=label),))
    )

    assert f'stage["{escaped}"]' in diagram


@pytest.mark.parametrize(
    ("node_id", "safe_id"),
    [
        ("backend-api", "backend_api"),
        ("release.quality", "release_quality"),
        ("qa/tests", "qa_tests"),
        ("01 requirements", "node_01_requirements"),
        ("área técnica", "area_tecnica"),
        ("end", "node_end"),
    ],
)
def test_sanitizes_node_identifiers(
    node_id: str,
    safe_id: str,
) -> None:
    diagram = MermaidExporter().export(graph((node(node_id),)))

    assert f'    {safe_id}["' in diagram
    assert f"    class {safe_id} pending\n" in diagram


def test_resolves_sanitization_collisions_with_stable_checksum() -> None:
    source = graph(
        (
            node("backend api", label="Space"),
            node("backend-api", label="Hyphen"),
        )
    )
    exporter = MermaidExporter()

    first = exporter.export(source)
    second = exporter.export(source)
    declarations = re.findall(
        r'^\s{4}([A-Za-z_][A-Za-z0-9_]*)\["',
        first,
        re.MULTILINE,
    )

    assert first == second
    assert declarations[0] == "backend_api"
    assert re.fullmatch(r"backend_api_[0-9a-f]{8}", declarations[1])
    assert len(set(declarations)) == 2


def test_unicode_only_ids_still_receive_safe_unique_identifier() -> None:
    diagram = MermaidExporter().export(
        graph((node("東京"), node("🚀")))
    )
    declarations = re.findall(
        r'^\s{4}([A-Za-z_][A-Za-z0-9_]*)\["',
        diagram,
        re.MULTILINE,
    )

    assert len(declarations) == 2
    assert len(set(declarations)) == 2
    assert all(identifier.startswith("node") for identifier in declarations)


def test_exports_dependency_edge_with_optional_escaped_label() -> None:
    source = graph(
        (node("source"), node("target")),
        (
            ExecutionEdge(
                source="source",
                target="target",
                edge_type=EdgeType.DEPENDENCY,
                label='success ["ready"]',
            ),
        ),
    )

    diagram = MermaidExporter().export(source)

    assert (
        '    source -->|"success &#91;&quot;ready&quot;&#93;"| target\n'
        in diagram
    )


def test_export_does_not_modify_graph() -> None:
    source = graph(
        (
            node("source", status=NodeStatus.COMPLETED),
            node("target", status=NodeStatus.RUNNING),
        ),
        (ExecutionEdge(source="source", target="target"),),
    )
    before = source.model_dump(mode="json")

    MermaidExporter().export(source)

    assert source.model_dump(mode="json") == before


def test_repeated_exports_are_identical() -> None:
    source = graph((node("analysis"),))
    exporter = MermaidExporter()

    assert exporter.export(source) == exporter.export(source)


def test_output_uses_only_lf_and_ends_with_one_newline() -> None:
    diagram = MermaidExporter().export(graph((node("analysis"),)))

    assert "\r" not in diagram
    assert diagram.endswith("\n")
    assert not diagram.endswith("\n\n")


def test_small_diagram_is_structurally_coherent_mermaid() -> None:
    source = graph(
        (
            node("analysis", label='Análise ["A"]'),
            node("review", label="Review"),
        ),
        (ExecutionEdge(source="analysis", target="review"),),
    )
    diagram = MermaidExporter().export(source)
    declared = set(
        re.findall(
            r'^\s{4}([A-Za-z_][A-Za-z0-9_]*)\["',
            diagram,
            re.MULTILINE,
        )
    )
    edge = re.search(
        r"^\s{4}([A-Za-z_][A-Za-z0-9_]*) --> "
        r"([A-Za-z_][A-Za-z0-9_]*)$",
        diagram,
        re.MULTILINE,
    )
    class_nodes = set(
        re.findall(
            r"^\s{4}class ([A-Za-z_][A-Za-z0-9_]*) ",
            diagram,
            re.MULTILINE,
        )
    )

    assert diagram.startswith("flowchart TD\n")
    assert declared == {"analysis", "review"}
    assert edge is not None
    assert set(edge.groups()) <= declared
    assert class_nodes == declared
    assert diagram.count('["') == diagram.count('"]')


def test_public_exports_are_intentional() -> None:
    import asep.exporters as exporters

    assert set(exporters.__all__) == {
        "BpmnExporter",
        "BpmnExportError",
        "BpmnExportOptions",
        "JSON_GRAPH_FORMAT_VERSION",
        "JsonExporter",
        "JsonExportError",
        "MermaidDirection",
        "MermaidExporter",
        "MermaidExportError",
        "MermaidExportOptions",
    }


def test_exporter_has_no_forbidden_direct_architecture_dependencies() -> None:
    import asep.exporters.mermaid as mermaid

    source = inspect.getsource(mermaid)

    assert "asep.workflow" not in source
    assert "asep.orchestrator" not in source
    assert "asep.application" not in source
    assert "asep.providers" not in source
    assert "asep.execution_package" not in source
    assert "asep.artifacts" not in source
    assert "asep.quality" not in source
