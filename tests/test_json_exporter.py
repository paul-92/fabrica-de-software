from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime

import pytest

from asep.execution_graph import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    GraphMetadata,
    NodeExecutionDetails,
    NodeStatus,
)
from asep.exporters import (
    JSON_GRAPH_FORMAT_VERSION,
    JsonExporter,
    JsonExportError,
)


def node(
    node_id: str,
    *,
    status: NodeStatus = NodeStatus.PENDING,
    provider: str | None = None,
    started_at: datetime | None = None,
    metadata: dict | None = None,
) -> ExecutionNode:
    return ExecutionNode(
        node_id=node_id,
        stage_id=node_id,
        label=f"Etapa {node_id}",
        mode="sequential",
        status=status,
        execution=NodeExecutionDetails(
            provider_name=provider,
            started_at=started_at,
        ),
        metadata=metadata or {},
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


def exported(source: ExecutionGraph) -> tuple[str, dict]:
    content = JsonExporter().export(source)
    return content, json.loads(content)


def test_exports_empty_graph_with_versioned_schema() -> None:
    content, payload = exported(graph(()))

    assert payload == {
        "version": "1.0",
        "generated_at": None,
        "graph": {"nodes": [], "edges": []},
    }
    assert content.endswith("\n")
    assert JSON_GRAPH_FORMAT_VERSION == "1.0"


def test_exports_simple_public_node_contract() -> None:
    _, payload = exported(
        graph(
            (
                node(
                    "analysis",
                    status=NodeStatus.RUNNING,
                    provider="codex",
                ),
            )
        )
    )

    result = payload["graph"]["nodes"][0]
    assert set(result) == {"id", "type", "status", "provider", "metadata"}
    assert result["id"] == "analysis"
    assert result["type"] == "stage"
    assert result["status"] == "running"
    assert result["provider"] == "codex"
    assert result["metadata"]["stage_id"] == "analysis"
    assert result["metadata"]["execution"]["attempt"] == 0


def test_exports_multiple_dependency_edges_with_public_names() -> None:
    source = graph(
        (node("c"), node("a"), node("b")),
        (
            ExecutionEdge(source="b", target="c"),
            ExecutionEdge(source="a", target="c"),
        ),
    )

    _, payload = exported(source)

    assert [item["id"] for item in payload["graph"]["nodes"]] == [
        "a",
        "b",
        "c",
    ]
    assert [
        (item["from"], item["to"], item["kind"])
        for item in payload["graph"]["edges"]
    ] == [
        ("a", "c", "dependency"),
        ("b", "c", "dependency"),
    ]


def test_metadata_is_recursively_sorted_and_json_native() -> None:
    source = graph(
        (
            node(
                "stage",
                metadata={
                    "z": {"b": 2, "a": 1},
                    "items": ("á", "b"),
                    "flags": frozenset({"z", "a"}),
                },
            ),
        )
    )

    content, payload = exported(source)
    custom = payload["graph"]["nodes"][0]["metadata"]["custom"]

    assert list(custom) == ["flags", "items", "z"]
    assert list(custom["z"]) == ["a", "b"]
    assert custom["items"] == ["á", "b"]
    assert custom["flags"] == ["a", "z"]
    assert "MappingProxyType" not in content
    assert "frozenset" not in content


def test_generated_at_comes_from_graph_not_export_clock() -> None:
    timestamp = datetime(2026, 7, 29, 12, 30, tzinfo=UTC)
    source = graph((node("stage", started_at=timestamp),))

    first, payload = exported(source)
    second = JsonExporter().export(source)

    assert payload["generated_at"] == timestamp.isoformat()
    assert first == second


def test_export_is_deterministic_and_does_not_modify_graph() -> None:
    source = graph(
        (node("b"), node("a")),
        (ExecutionEdge(source="a", target="b"),),
    )
    before = source.model_dump(mode="json")
    exporter = JsonExporter()

    first = exporter.export(source)
    second = exporter.export(source)

    assert first == second
    assert source.model_dump(mode="json") == before
    assert "\r" not in first
    assert first.endswith("\n")
    assert not first.endswith("\n\n")


def test_output_contains_only_json_values() -> None:
    _, payload = exported(graph((node("análise"),)))

    def assert_json_value(value) -> None:
        assert value is None or isinstance(
            value, (str, int, float, bool, list, dict)
        )
        if isinstance(value, list):
            for item in value:
                assert_json_value(item)
        if isinstance(value, dict):
            assert all(isinstance(key, str) for key in value)
            for item in value.values():
                assert_json_value(item)

    assert_json_value(payload)


def test_rejects_non_serializable_custom_metadata() -> None:
    source = graph((node("stage", metadata={"bad": object()}),))

    with pytest.raises(JsonExportError, match="não serializável"):
        JsonExporter().export(source)


def test_rejects_non_standard_nan_number() -> None:
    source = graph((node("stage", metadata={"bad": float("nan")}),))

    with pytest.raises(JsonExportError, match="incompatível"):
        JsonExporter().export(source)


def test_public_exports_are_available() -> None:
    import asep.exporters as exporters

    assert {
        "JSON_GRAPH_FORMAT_VERSION",
        "JsonExporter",
        "JsonExportError",
    } <= set(exporters.__all__)


def test_exporter_has_no_forbidden_architecture_dependencies() -> None:
    import asep.exporters.json_exporter as json_exporter

    source = inspect.getsource(json_exporter)

    for forbidden in (
        "asep.providers",
        "asep.workflow",
        "asep.orchestrator",
        "asep.cli",
        "asep.application",
    ):
        assert forbidden not in source
