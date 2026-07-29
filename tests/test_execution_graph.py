from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from asep.application.stage_execution import StageExecutionReport
from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactReference,
    ExecutionState,
    ExecutionStatus,
    GateDecision,
    GateResult,
    RunContext,
    StageState,
    StageStatus,
)
from asep.execution_graph import (
    EXECUTION_GRAPH_SCHEMA_VERSION,
    EdgeType,
    ExecutionEdge,
    ExecutionGraph,
    ExecutionGraphBuilder,
    ExecutionGraphError,
    ExecutionGraphSerializer,
    ExecutionNode,
    GraphMetadata,
    InvalidGraphError,
    NodeExecutionDetails,
    NodeStatus,
    QualityGateSummary,
)
from asep.models import WorkflowDefinition, WorkflowStage
from asep.providers import AgentExecutionResult, AgentExecutionStatus

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"
NOW = datetime(2026, 7, 29, tzinfo=UTC)


def workflow(
    stage_ids: tuple[str, ...],
    dependencies: dict[str, list[str]],
    *,
    parallel_stage: str | None = None,
    name: str = "Software Project",
) -> WorkflowDefinition:
    stages = []
    for stage_id in stage_ids:
        if stage_id == parallel_stage:
            stages.append(
                WorkflowStage(
                    id=stage_id,
                    mode="parallel",
                    workflows=["branch-b", "branch-a"],
                )
            )
        else:
            stages.append(
                WorkflowStage(
                    id=stage_id,
                    mode="sequential",
                    workflow=f"{stage_id}-workflow",
                )
            )
    return WorkflowDefinition(
        id="software-project",
        name=name,
        version="1.0.0",
        description="Fluxo canônico.",
        applicable_project_types=["software"],
        required_context=[],
        stages=stages,
        stage_dependencies=dependencies,
        assigned_agents={
            stage_id: [f"{stage_id}-agent"] for stage_id in stage_ids
        },
        stage_quality_gates={
            stage_id: f"QG-{stage_id.upper()}"
            for stage_id in stage_ids
        },
        conditions=[],
        quality_gates=[
            f"QG-{stage_id.upper()}" for stage_id in stage_ids
        ],
        human_approvals=[],
        artifacts=[],
        failure_handling={},
        completion_criteria=[],
    )


def execution_state(
    statuses: dict[str, StageStatus],
    *,
    execution_status: ExecutionStatus = ExecutionStatus.RUNNING,
) -> ExecutionState:
    return ExecutionState(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        execution_status=execution_status,
        current_stage=next(iter(statuses), None),
        created_at=NOW,
        updated_at=NOW,
        stages=[
            StageState(
                id=stage_id,
                status=status,
                agent_id=f"{stage_id}-agent",
                quality_gate_id=f"QG-{stage_id.upper()}",
                attempts=1 if status != StageStatus.PENDING else 0,
            )
            for stage_id, status in statuses.items()
        ],
    )


def run_context() -> RunContext:
    return RunContext(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        started_at=NOW,
        execution_status=ExecutionStatus.RUNNING,
        project_path=Path("project"),
        state_path=Path("project/.asep/state.yaml"),
        artifacts_path=Path("project/artifacts"),
        logs_path=Path("project/log.jsonl"),
    )


def artifact(stage_id: str, path: str | None = None) -> ArtifactReference:
    return ArtifactReference(
        artifact_id=f"artifact-{stage_id}-{path or 'result'}",
        run_id=RUN_ID,
        project_id="sample",
        stage_id=stage_id,
        agent_id=f"{stage_id}-agent",
        path=path or f"results/{stage_id}.md",
        type="markdown",
        created_at=NOW,
        checksum="0" * 64,
    )


def stage_report(
    stage_id: str,
    *,
    agent_status: AgentResultStatus = AgentResultStatus.COMPLETED,
    provider_status: AgentExecutionStatus = AgentExecutionStatus.SUCCESS,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
    include_gate: bool = True,
) -> StageExecutionReport:
    agent_result = AgentResult(
        status=agent_status,
        agent_id=f"{stage_id}-agent",
        stage_id=stage_id,
        run_id=RUN_ID,
        started_at=NOW,
        finished_at=NOW + timedelta(milliseconds=1250),
        warnings=list(warnings),
        errors=list(errors),
    )
    provider_result = AgentExecutionResult(
        status=provider_status,
        provider_name="fake",
        provider_version="2.0",
        exit_code=0 if provider_status == AgentExecutionStatus.SUCCESS else 1,
        stdout="done",
        errors=(
            errors
            if provider_status == AgentExecutionStatus.FAILED
            else ()
        ),
        stderr=(
            "failed"
            if provider_status == AgentExecutionStatus.FAILED and not errors
            else ""
        ),
    )
    gate = (
        GateResult(
            gate_id=f"QG-{stage_id.upper()}",
            run_id=RUN_ID,
            stage_id=stage_id,
            decision=GateDecision.APPROVED,
            satisfied_criteria=["resultado válido"],
            unsatisfied_criteria=[],
            evaluated_at=NOW,
        )
        if include_gate
        else None
    )
    return StageExecutionReport(
        agent_result=agent_result,
        artifact_references=(artifact(stage_id),),
        gate_result=gate,
        provider_result=provider_result,
    )


def metadata(
    nodes: int,
    edges: int,
    *,
    workflow_name: str = "Software Project",
) -> GraphMetadata:
    return GraphMetadata(
        workflow_name=workflow_name,
        created_from="test",
        total_nodes=nodes,
        total_edges=edges,
    )


def test_builds_linear_workflow_nodes_and_edges() -> None:
    definition = workflow(
        ("analysis", "implementation", "review"),
        {
            "analysis": [],
            "implementation": ["analysis"],
            "review": ["implementation"],
        },
    )

    graph = ExecutionGraphBuilder().build(definition)

    assert tuple(node.node_id for node in graph.nodes) == (
        "analysis",
        "implementation",
        "review",
    )
    assert tuple(
        (edge.source, edge.target, edge.edge_type)
        for edge in graph.edges
    ) == (
        ("analysis", "implementation", EdgeType.DEPENDENCY),
        ("implementation", "review", EdgeType.DEPENDENCY),
    )


def test_parallel_dependencies_have_stable_topological_order() -> None:
    definition = workflow(
        ("join", "branch-b", "start", "branch-a"),
        {
            "join": ["branch-b", "branch-a"],
            "branch-b": ["start"],
            "start": [],
            "branch-a": ["start"],
        },
        parallel_stage="start",
    )

    graph = ExecutionGraphBuilder().build(definition)

    assert tuple(node.node_id for node in graph.nodes) == (
        "start",
        "branch-a",
        "branch-b",
        "join",
    )
    assert graph.nodes[0].workflow_references == (
        "branch-a",
        "branch-b",
    )


def test_isolated_nodes_are_sorted_and_have_no_edges() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(
            ("zeta", "alpha", "middle"),
            {"zeta": [], "alpha": [], "middle": []},
        )
    )

    assert tuple(node.node_id for node in graph.nodes) == (
        "alpha",
        "middle",
        "zeta",
    )
    assert graph.edges == ()


def test_empty_workflow_produces_empty_graph() -> None:
    graph = ExecutionGraphBuilder().build(workflow((), {}))

    assert graph.nodes == ()
    assert graph.edges == ()
    assert graph.metadata.total_nodes == 0
    assert graph.metadata.status_counts == {}


def test_unexecuted_workflow_has_pending_nodes_and_definition_identity() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []})
    )

    assert graph.graph_id == "workflow:software-project:1.0.0"
    assert graph.project_id is None
    assert graph.run_id is None
    assert graph.nodes[0].status is NodeStatus.PENDING
    assert graph.metadata.created_from == "workflow_definition"


def test_run_context_associates_execution_identity() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []}),
        run_context=run_context(),
        project_name="Projeto Ágil",
    )

    assert graph.graph_id == f"execution:{RUN_ID}"
    assert graph.project_id == "sample"
    assert graph.run_id == RUN_ID
    assert graph.metadata.project_name == "Projeto Ágil"
    assert graph.metadata.created_from == "run_context"


def test_partially_executed_workflow_maps_stage_statuses_and_attempts() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(
            ("analysis", "implementation", "review"),
            {
                "analysis": [],
                "implementation": ["analysis"],
                "review": ["implementation"],
            },
        ),
        execution_state=execution_state(
            {
                "analysis": StageStatus.COMPLETED,
                "implementation": StageStatus.RUNNING,
                "review": StageStatus.PENDING,
            }
        ),
    )

    assert tuple(node.status for node in graph.nodes) == (
        NodeStatus.COMPLETED,
        NodeStatus.RUNNING,
        NodeStatus.PENDING,
    )
    assert graph.nodes[1].execution.attempt == 1
    assert graph.metadata.status_counts == {
        "completed": 1,
        "pending": 1,
        "running": 1,
    }


@pytest.mark.parametrize(
    ("stage_status", "expected"),
    [
        (StageStatus.COMPLETED, NodeStatus.COMPLETED),
        (StageStatus.BLOCKED, NodeStatus.BLOCKED),
        (StageStatus.FAILED, NodeStatus.FAILED),
        (StageStatus.CANCELLED, NodeStatus.CANCELLED),
        (StageStatus.SKIPPED, NodeStatus.SKIPPED),
        (StageStatus.READY, NodeStatus.READY),
    ],
)
def test_maps_existing_stage_statuses(
    stage_status: StageStatus,
    expected: NodeStatus,
) -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []}),
        execution_state=execution_state({"analysis": stage_status}),
    )

    assert graph.nodes[0].status is expected


def test_maps_partial_provider_result_without_execution_state() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []}),
        stage_reports={
            "analysis": stage_report(
                "analysis",
                agent_status=AgentResultStatus.FAILED,
                provider_status=AgentExecutionStatus.PARTIAL,
                errors=("partial result",),
                include_gate=False,
            )
        },
    )

    assert graph.nodes[0].status is NodeStatus.PARTIAL


def test_associates_provider_timing_exit_code_and_result() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []}),
        stage_reports={"analysis": stage_report("analysis")},
    )
    details = graph.nodes[0].execution

    assert details.provider_name == "fake"
    assert details.provider_version == "2.0"
    assert details.provider_result_status is AgentExecutionStatus.SUCCESS
    assert details.agent_result_status is AgentResultStatus.COMPLETED
    assert details.started_at == NOW
    assert details.finished_at == NOW + timedelta(milliseconds=1250)
    assert details.duration_ms == 1250
    assert details.exit_code == 0


def test_associates_sorted_artifacts_and_quality_gate() -> None:
    report = stage_report("analysis")
    second = artifact("analysis", "a-first.md")
    report = StageExecutionReport(
        agent_result=report.agent_result,
        artifact_references=(*report.artifact_references, second),
        gate_result=report.gate_result,
        provider_result=report.provider_result,
    )

    node = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []}),
        stage_reports={"analysis": report},
    ).nodes[0]

    assert tuple(item.path for item in node.artifacts) == (
        "a-first.md",
        "results/analysis.md",
    )
    assert node.quality_gate is not None
    assert node.quality_gate.gate_id == "QG-ANALYSIS"
    assert node.quality_gate.decision is GateDecision.APPROVED


def test_warnings_and_errors_have_predictable_order() -> None:
    report = stage_report(
        "analysis",
        agent_status=AgentResultStatus.FAILED,
        provider_status=AgentExecutionStatus.FAILED,
        warnings=("zeta", "Alpha", "zeta"),
        errors=("second", "First"),
        include_gate=False,
    )

    details = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []}),
        stage_reports={"analysis": report},
    ).nodes[0].execution

    assert details.warnings == ("Alpha", "zeta")
    assert details.errors == ("First", "second")


def test_graph_metadata_is_deterministic_and_complete() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis", "review"), {
            "review": ["analysis"],
            "analysis": [],
        }),
        execution_state=execution_state(
            {
                "review": StageStatus.PENDING,
                "analysis": StageStatus.COMPLETED,
            }
        ),
        project_name="Projeto",
    )

    assert graph.schema_version == EXECUTION_GRAPH_SCHEMA_VERSION
    assert graph.metadata.schema_version == EXECUTION_GRAPH_SCHEMA_VERSION
    assert graph.metadata.generator == "asep"
    assert graph.metadata.total_nodes == 2
    assert graph.metadata.total_edges == 1
    assert graph.metadata.created_from == "execution_state"


def test_same_semantics_in_different_input_order_are_identical() -> None:
    first = workflow(
        ("review", "analysis"),
        {"review": ["analysis"], "analysis": []},
    )
    second = workflow(
        ("analysis", "review"),
        {"analysis": [], "review": ["analysis"]},
    )
    builder = ExecutionGraphBuilder()
    serializer = ExecutionGraphSerializer()

    assert serializer.serialize(builder.build(first)) == serializer.serialize(
        builder.build(second)
    )


def test_serializer_outputs_deterministic_unicode_json() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(
            ("análise",),
            {"análise": []},
            name="Engenharia Ágil",
        )
    )
    serializer = ExecutionGraphSerializer()

    first = serializer.serialize(graph)
    document = json.loads(first)

    assert first == serializer.serialize(graph)
    assert first.endswith("\n")
    assert "Engenharia Ágil" in first
    assert document["nodes"][0]["node_id"] == "análise"
    assert document["metadata"]["workflow_name"] == "Engenharia Ágil"


def test_rejects_unknown_dependency_reference() -> None:
    definition = workflow(
        ("analysis",),
        {"analysis": ["missing"]},
    )

    with pytest.raises(InvalidGraphError, match="inexistentes"):
        ExecutionGraphBuilder().build(definition)


def test_rejects_unknown_stage_report() -> None:
    with pytest.raises(InvalidGraphError, match="Relatórios"):
        ExecutionGraphBuilder().build(
            workflow(("analysis",), {"analysis": []}),
            stage_reports={"missing": stage_report("missing")},
        )


def test_rejects_duplicate_workflow_nodes() -> None:
    definition = workflow(
        ("analysis", "analysis"),
        {"analysis": []},
    )

    with pytest.raises(InvalidGraphError, match="duplicadas"):
        ExecutionGraphBuilder().build(definition)


def test_rejects_duplicate_edges() -> None:
    definition = workflow(
        ("analysis", "review"),
        {"analysis": [], "review": ["analysis", "analysis"]},
    )

    with pytest.raises(InvalidGraphError, match="duplicadas"):
        ExecutionGraphBuilder().build(definition)


def test_graph_model_rejects_edge_to_unknown_node() -> None:
    node = ExecutionNode(
        node_id="analysis",
        stage_id="analysis",
        label="Analysis",
        mode="sequential",
    )

    with pytest.raises(ValidationError, match="nó inexistente"):
        ExecutionGraph(
            graph_id="graph",
            workflow_id="workflow",
            nodes=(node,),
            edges=(ExecutionEdge(source="analysis", target="missing"),),
            metadata=metadata(1, 1),
        )


def test_rejects_negative_duration_and_inverted_times() -> None:
    with pytest.raises(ValidationError):
        NodeExecutionDetails(duration_ms=-1)
    with pytest.raises(ValidationError, match="não pode preceder"):
        NodeExecutionDetails(
            started_at=NOW,
            finished_at=NOW - timedelta(seconds=1),
        )


def test_models_and_nested_metadata_are_immutable() -> None:
    source = {"nested": {"labels": ["one"]}}
    node = ExecutionNode(
        node_id="analysis",
        stage_id="analysis",
        label="Analysis",
        mode="sequential",
        metadata=source,
    )
    source["nested"]["labels"].append("changed")  # type: ignore[index]

    assert node.metadata["nested"]["labels"] == ("one",)
    with pytest.raises(ValidationError):
        node.status = NodeStatus.RUNNING  # type: ignore[misc]
    with pytest.raises(TypeError):
        node.metadata["new"] = "value"  # type: ignore[index]


def test_artifact_references_are_immutable() -> None:
    reference = artifact("analysis")

    with pytest.raises(ValidationError):
        reference.path = "changed.md"  # type: ignore[misc]


def test_public_exports_are_intentional() -> None:
    import asep.execution_graph as execution_graph

    assert set(execution_graph.__all__) == {
        "EXECUTION_GRAPH_SCHEMA_VERSION",
        "EdgeType",
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
    }
    assert issubclass(InvalidGraphError, ExecutionGraphError)
