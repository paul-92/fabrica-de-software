"""Construção determinística do modelo canônico de execução."""

from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from asep.execution.models import ExecutionState, StageState
from asep.execution_graph.models import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    GraphMetadata,
    NodeStatus,
)
from asep.models import WorkflowDefinition, WorkflowStage

if TYPE_CHECKING:
    from asep.application.stage_execution import StageExecutionReport


class ExecutionGraphBuilder:
    def build(
        self,
        workflow: WorkflowDefinition,
        *,
        state: ExecutionState | None = None,
        stage_reports: Mapping[str, StageExecutionReport] | None = None,
        metadata: GraphMetadata | None = None,
    ) -> ExecutionGraph:
        reports = stage_reports or {}
        stage_by_id = {stage.id: stage for stage in workflow.stages}
        ordered_ids = self._ordered_stage_ids(workflow)
        state_by_id = (
            {stage.id: stage for stage in state.stages}
            if state is not None
            else {}
        )

        nodes = tuple(
            self._node(
                stage_by_id[stage_id],
                workflow,
                state_by_id.get(stage_id),
                reports.get(stage_id),
            )
            for stage_id in ordered_ids
        )
        edges = tuple(
            sorted(
                (
                    ExecutionEdge(source=dependency, target=stage_id)
                    for stage_id, dependencies in (
                        workflow.stage_dependencies.items()
                    )
                    for dependency in dependencies
                ),
                key=lambda edge: (
                    edge.source,
                    edge.target,
                    edge.type,
                ),
            )
        )
        return ExecutionGraph(
            metadata=metadata or self._metadata(workflow, state),
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _node(
        stage: WorkflowStage,
        workflow: WorkflowDefinition,
        stage_state: StageState | None,
        report: StageExecutionReport | None,
    ) -> ExecutionNode:
        agent_result = report.agent_result if report is not None else None
        provider_result = (
            report.provider_result if report is not None else None
        )
        gate_result = report.gate_result if report is not None else None
        artifact_references = (
            (
                *report.artifact_references,
                *(
                    (report.gate_artifact_reference,)
                    if report.gate_artifact_reference is not None
                    else ()
                ),
            )
            if report is not None
            else ()
        )
        return ExecutionNode(
            id=stage.id,
            label=stage.id,
            mode=stage.mode,
            workflow_reference=stage.workflow,
            workflow_references=tuple(stage.workflows),
            status=(
                NodeStatus(stage_state.status)
                if stage_state is not None
                else NodeStatus.PENDING
            ),
            agent_ids=tuple(
                sorted(workflow.assigned_agents.get(stage.id, ()))
            ),
            quality_gate_id=workflow.stage_quality_gates.get(stage.id),
            agent_result_status=(
                agent_result.status if agent_result is not None else None
            ),
            provider_result_status=(
                provider_result.status
                if provider_result is not None
                else None
            ),
            gate_decision=(
                gate_result.decision if gate_result is not None else None
            ),
            artifact_paths=tuple(
                sorted(
                    reference.path for reference in artifact_references
                )
            ),
            warnings=(
                tuple(agent_result.warnings)
                if agent_result is not None
                else ()
            ),
            errors=(
                tuple(agent_result.errors)
                if agent_result is not None
                else ()
            ),
        )

    @staticmethod
    def _metadata(
        workflow: WorkflowDefinition,
        state: ExecutionState | None,
    ) -> GraphMetadata:
        return GraphMetadata(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            run_id=state.run_id if state is not None else None,
            project_id=state.project_id if state is not None else None,
            execution_status=(
                state.execution_status if state is not None else None
            ),
            created_at=state.created_at if state is not None else None,
            updated_at=state.updated_at if state is not None else None,
        )

    @staticmethod
    def _ordered_stage_ids(
        workflow: WorkflowDefinition,
    ) -> tuple[str, ...]:
        stage_ids = {stage.id for stage in workflow.stages}
        indegree = {stage_id: 0 for stage_id in stage_ids}
        dependents: dict[str, list[str]] = defaultdict(list)

        for stage_id, dependencies in workflow.stage_dependencies.items():
            if stage_id not in stage_ids:
                raise ValueError(
                    f"dependências para nó inexistente: {stage_id}"
                )
            for dependency in dependencies:
                if dependency not in stage_ids:
                    raise ValueError(
                        f"dependência inexistente: {dependency}"
                    )
                indegree[stage_id] += 1
                dependents[dependency].append(stage_id)

        ready = [
            stage_id
            for stage_id, degree in indegree.items()
            if degree == 0
        ]
        heapq.heapify(ready)
        ordered: list[str] = []
        while ready:
            stage_id = heapq.heappop(ready)
            ordered.append(stage_id)
            for dependent in sorted(dependents[stage_id]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    heapq.heappush(ready, dependent)

        if len(ordered) != len(stage_ids):
            raise ValueError("workflow contém ciclo de dependências")
        return tuple(ordered)
