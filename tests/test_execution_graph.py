from __future__ import annotations

import json
from datetime import UTC, datetime

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
    StageState,
    StageStatus,
)
from asep.execution_graph import (
    EdgeType,
    ExecutionGraphBuilder,
    ExecutionGraphSerializer,
    GraphMetadata,
    NodeStatus,
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
) -> WorkflowDefinition:
    stages = []
    for stage_id in stage_ids:
        if stage_id == parallel_stage:
            stages.append(
                WorkflowStage(
                    id=stage_id,
                    mode="parallel",
                    workflows=["branch-a", "branch-b"],
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
        name="Software Project",
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
    stage_ids: tuple[str, ...],
) -> ExecutionState:
    return ExecutionState(
        run_id=RUN_ID,
        project_id="sample",
        workflow_id="software-project",
        execution_status=ExecutionStatus.RUNNING,
        current_stage=stage_ids[0] if stage_ids else None,
        created_at=NOW,
        updated_at=NOW,
        stages=[
            StageState(
                id=stage_id,
                status=(
                    StageStatus.COMPLETED
                    if index == 0
                    else StageStatus.PENDING
                ),
                agent_id=f"{stage_id}-agent",
                quality_gate_id=f"QG-{stage_id.upper()}",
            )
            for index, stage_id in enumerate(stage_ids)
        ],
    )


def stage_report(stage_id: str) -> StageExecutionReport:
    agent_result = AgentResult(
        status=AgentResultStatus.COMPLETED,
        agent_id=f"{stage_id}-agent",
        stage_id=stage_id,
        run_id=RUN_ID,
        started_at=NOW,
        finished_at=NOW,
        warnings=["revisar"],
    )
    provider_result = AgentExecutionResult(
        status=AgentExecutionStatus.SUCCESS,
        provider_name="fake",
        provider_version="1.0",
        exit_code=0,
        stdout="done",
    )
    artifact = ArtifactReference(
        artifact_id="artifact-1",
        run_id=RUN_ID,
        project_id="sample",
        stage_id=stage_id,
        agent_id=f"{stage_id}-agent",
        path=f"results/{stage_id}.md",
        type="markdown",
        created_at=NOW,
        checksum="0" * 64,
    )
    gate = GateResult(
        gate_id=f"QG-{stage_id.upper()}",
        run_id=RUN_ID,
        stage_id=stage_id,
        decision=GateDecision.APPROVED_WITH_PENDING,
        satisfied_criteria=["resultado válido"],
        unsatisfied_criteria=[],
        evaluated_at=NOW,
    )
    return StageExecutionReport(
        agent_result=agent_result,
        artifact_references=(artifact,),
        gate_result=gate,
        provider_result=provider_result,
    )


def test_builds_linear_graph_with_dependency_edges() -> None:
    definition = workflow(
        ("analysis", "implementation", "review"),
        {
            "analysis": [],
            "implementation": ["analysis"],
            "review": ["implementation"],
        },
    )

    graph = ExecutionGraphBuilder().build(definition)

    assert tuple(node.id for node in graph.nodes) == (
        "analysis",
        "implementation",
        "review",
    )
    assert tuple(
        (edge.source, edge.target, edge.type) for edge in graph.edges
    ) == (
        ("analysis", "implementation", EdgeType.DEPENDENCY),
        ("implementation", "review", EdgeType.DEPENDENCY),
    )
    assert all(node.status is NodeStatus.PENDING for node in graph.nodes)


def test_parallel_branches_use_deterministic_topological_order() -> None:
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

    assert tuple(node.id for node in graph.nodes) == (
        "start",
        "branch-a",
        "branch-b",
        "join",
    )
    start = graph.nodes[0]
    assert start.mode == "parallel"
    assert start.workflow_references == ("branch-a", "branch-b")


def test_isolated_nodes_are_sorted_lexicographically() -> None:
    definition = workflow(
        ("zeta", "alpha", "middle"),
        {"zeta": [], "alpha": [], "middle": []},
    )

    graph = ExecutionGraphBuilder().build(definition)

    assert tuple(node.id for node in graph.nodes) == (
        "alpha",
        "middle",
        "zeta",
    )
    assert graph.edges == ()


def test_associates_state_stage_report_and_execution_metadata() -> None:
    definition = workflow(("analysis", "review"), {
        "analysis": [],
        "review": ["analysis"],
    })
    state = execution_state(("analysis", "review"))

    graph = ExecutionGraphBuilder().build(
        definition,
        state=state,
        stage_reports={"analysis": stage_report("analysis")},
    )

    analysis = graph.nodes[0]
    assert analysis.status is NodeStatus.COMPLETED
    assert analysis.agent_result_status is AgentResultStatus.COMPLETED
    assert (
        analysis.provider_result_status
        is AgentExecutionStatus.SUCCESS
    )
    assert analysis.gate_decision is GateDecision.APPROVED_WITH_PENDING
    assert analysis.artifact_paths == ("results/analysis.md",)
    assert analysis.warnings == ("revisar",)
    assert graph.metadata.run_id == RUN_ID
    assert graph.metadata.project_id == "sample"
    assert graph.metadata.execution_status is ExecutionStatus.RUNNING
    assert graph.metadata.created_at == NOW


def test_custom_metadata_is_preserved() -> None:
    definition = workflow(("analysis",), {"analysis": []})
    metadata = GraphMetadata(
        schema_version="1.1.0",
        workflow_id=definition.id,
        workflow_name="Fluxo de análise",
        workflow_version=definition.version,
        project_id="project-á",
    )

    graph = ExecutionGraphBuilder().build(
        definition,
        metadata=metadata,
    )

    assert graph.metadata is metadata
    assert graph.metadata.schema_version == "1.1.0"


def test_serializes_deterministic_canonical_json() -> None:
    definition = workflow(
        ("review", "analysis"),
        {"review": ["analysis"], "analysis": []},
    )
    graph = ExecutionGraphBuilder().build(definition)
    serializer = ExecutionGraphSerializer()

    first = serializer.serialize(graph)
    second = serializer.serialize(graph)
    document = json.loads(first)

    assert first == second
    assert first.endswith("\n")
    assert document["metadata"]["workflow_name"] == "Software Project"
    assert [node["id"] for node in document["nodes"]] == [
        "analysis",
        "review",
    ]
    assert document["edges"] == [
        {
            "source": "analysis",
            "target": "review",
            "type": "dependency",
        }
    ]


def test_models_are_immutable() -> None:
    graph = ExecutionGraphBuilder().build(
        workflow(("analysis",), {"analysis": []})
    )

    with pytest.raises(ValidationError):
        graph.nodes = ()  # type: ignore[misc]
    with pytest.raises(ValidationError):
        graph.nodes[0].status = NodeStatus.RUNNING  # type: ignore[misc]
