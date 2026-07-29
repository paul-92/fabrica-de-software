"""Projeção determinística dos modelos ASEP para ExecutionGraph."""

from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from asep.execution.models import (
    AgentResultStatus,
    ExecutionState,
    RunContext,
    StageState,
)
from asep.execution_graph.errors import InvalidGraphError
from asep.execution_graph.models import (
    EXECUTION_GRAPH_SCHEMA_VERSION,
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    GraphMetadata,
    NodeExecutionDetails,
    NodeStatus,
    QualityGateSummary,
)
from asep.models import WorkflowDefinition, WorkflowStage
from asep.providers.models import AgentExecutionStatus

if TYPE_CHECKING:
    from asep.application.stage_execution import StageExecutionReport


class ExecutionGraphBuilder:
    def build(
        self,
        workflow: WorkflowDefinition,
        *,
        run_context: RunContext | None = None,
        execution_state: ExecutionState | None = None,
        stage_reports: Mapping[str, StageExecutionReport] | None = None,
        project_name: str | None = None,
    ) -> ExecutionGraph:
        reports = stage_reports or {}
        stage_ids = tuple(stage.id for stage in workflow.stages)
        self._validate_inputs(
            workflow,
            stage_ids,
            reports,
            run_context,
            execution_state,
        )

        stage_by_id = {stage.id: stage for stage in workflow.stages}
        state_by_id = (
            {stage.id: stage for stage in execution_state.stages}
            if execution_state is not None
            else {}
        )
        ordered_ids = self._ordered_stage_ids(workflow, set(stage_ids))
        nodes = tuple(
            self._node(
                stage_by_id[stage_id],
                workflow,
                state_by_id.get(stage_id),
                reports.get(stage_id),
            )
            for stage_id in ordered_ids
        )
        edges = self._edges(workflow)
        project_id = (
            execution_state.project_id
            if execution_state is not None
            else (
                run_context.project_id
                if run_context is not None
                else None
            )
        )
        run_id = (
            execution_state.run_id
            if execution_state is not None
            else run_context.run_id if run_context is not None else None
        )
        metadata = self._metadata(
            workflow,
            nodes,
            edges,
            project_name,
            run_context,
            execution_state,
            reports,
        )
        graph_id = (
            f"execution:{run_id}"
            if run_id is not None
            else f"workflow:{workflow.id}:{workflow.version}"
        )
        return ExecutionGraph(
            graph_id=graph_id,
            project_id=project_id,
            workflow_id=workflow.id,
            run_id=run_id,
            schema_version=EXECUTION_GRAPH_SCHEMA_VERSION,
            nodes=nodes,
            edges=edges,
            metadata=metadata,
        )

    @classmethod
    def _node(
        cls,
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
        artifacts = (
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
        started_at = (
            agent_result.started_at if agent_result is not None else None
        )
        finished_at = (
            agent_result.finished_at if agent_result is not None else None
        )
        duration_ms = (
            int((finished_at - started_at).total_seconds() * 1000)
            if started_at is not None and finished_at is not None
            else None
        )
        execution = NodeExecutionDetails(
            agent_result_status=(
                agent_result.status if agent_result is not None else None
            ),
            provider_result_status=(
                provider_result.status
                if provider_result is not None
                else None
            ),
            provider_name=(
                provider_result.provider_name
                if provider_result is not None
                else None
            ),
            provider_version=(
                provider_result.provider_version
                if provider_result is not None
                else None
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            attempt=stage_state.attempts if stage_state is not None else 0,
            exit_code=(
                provider_result.exit_code
                if provider_result is not None
                else None
            ),
            warnings=cls._ordered_text(
                agent_result.warnings if agent_result is not None else ()
            ),
            errors=cls._ordered_text(
                agent_result.errors if agent_result is not None else ()
            ),
        )
        quality_gate = (
            QualityGateSummary(
                gate_id=gate_result.gate_id,
                decision=gate_result.decision,
                satisfied_criteria=cls._ordered_text(
                    gate_result.satisfied_criteria
                ),
                unsatisfied_criteria=cls._ordered_text(
                    gate_result.unsatisfied_criteria
                ),
                evaluated_at=gate_result.evaluated_at,
            )
            if gate_result is not None
            else None
        )
        return ExecutionNode(
            node_id=stage.id,
            stage_id=stage.id,
            label=stage.id,
            mode=stage.mode,
            workflow_reference=stage.workflow,
            workflow_references=tuple(sorted(stage.workflows)),
            status=cls._node_status(stage_state, report),
            agent_ids=tuple(
                sorted(workflow.assigned_agents.get(stage.id, ()))
            ),
            execution=execution,
            artifacts=tuple(
                sorted(
                    artifacts,
                    key=lambda item: (
                        item.path,
                        item.artifact_id,
                    ),
                )
            ),
            quality_gate=quality_gate,
            metadata={
                "quality_gate_id": workflow.stage_quality_gates.get(
                    stage.id
                )
            },
        )

    @staticmethod
    def _node_status(
        stage_state: StageState | None,
        report: StageExecutionReport | None,
    ) -> NodeStatus:
        if stage_state is not None:
            return NodeStatus(stage_state.status.value)
        if report is None:
            return NodeStatus.PENDING
        if (
            report.provider_result is not None
            and report.provider_result.status == AgentExecutionStatus.PARTIAL
        ):
            return NodeStatus.PARTIAL
        mapping = {
            AgentResultStatus.COMPLETED: NodeStatus.COMPLETED,
            AgentResultStatus.BLOCKED: NodeStatus.BLOCKED,
            AgentResultStatus.AWAITING_APPROVAL: (
                NodeStatus.AWAITING_APPROVAL
            ),
            AgentResultStatus.FAILED: NodeStatus.FAILED,
        }
        return mapping[report.agent_result.status]

    @staticmethod
    def _edges(
        workflow: WorkflowDefinition,
    ) -> tuple[ExecutionEdge, ...]:
        return tuple(
            sorted(
                (
                    ExecutionEdge(
                        source=dependency,
                        target=stage_id,
                    )
                    for stage_id, dependencies in (
                        workflow.stage_dependencies.items()
                    )
                    for dependency in dependencies
                ),
                key=lambda edge: (
                    edge.source,
                    edge.target,
                    edge.edge_type,
                ),
            )
        )

    @staticmethod
    def _metadata(
        workflow: WorkflowDefinition,
        nodes: tuple[ExecutionNode, ...],
        edges: tuple[ExecutionEdge, ...],
        project_name: str | None,
        run_context: RunContext | None,
        execution_state: ExecutionState | None,
        reports: Mapping[str, StageExecutionReport],
    ) -> GraphMetadata:
        if execution_state is not None:
            created_from = "execution_state"
        elif reports:
            created_from = "stage_reports"
        elif run_context is not None:
            created_from = "run_context"
        else:
            created_from = "workflow_definition"
        counts = Counter(node.status.value for node in nodes)
        return GraphMetadata(
            project_name=project_name,
            workflow_name=workflow.name,
            created_from=created_from,
            total_nodes=len(nodes),
            total_edges=len(edges),
            status_counts=dict(sorted(counts.items())),
        )

    @staticmethod
    def _validate_inputs(
        workflow: WorkflowDefinition,
        stage_ids: tuple[str, ...],
        reports: Mapping[str, StageExecutionReport],
        run_context: RunContext | None,
        execution_state: ExecutionState | None,
    ) -> None:
        known = set(stage_ids)
        if len(stage_ids) != len(known):
            raise InvalidGraphError("Workflow contém etapas duplicadas.")
        unknown_reports = set(reports) - known
        if unknown_reports:
            raise InvalidGraphError(
                f"Relatórios referenciam etapas inexistentes: "
                f"{sorted(unknown_reports)}"
            )
        if execution_state is not None:
            state_ids = [stage.id for stage in execution_state.stages]
            if len(state_ids) != len(set(state_ids)):
                raise InvalidGraphError("Estado contém etapas duplicadas.")
            unknown_state = set(state_ids) - known
            if unknown_state:
                raise InvalidGraphError(
                    f"Estado referencia etapas inexistentes: "
                    f"{sorted(unknown_state)}"
                )
            if execution_state.workflow_id != workflow.id:
                raise InvalidGraphError(
                    "Estado pertence a outro workflow."
                )
        if run_context is not None:
            if run_context.workflow_id != workflow.id:
                raise InvalidGraphError(
                    "RunContext pertence a outro workflow."
                )
            if execution_state is not None and (
                run_context.run_id != execution_state.run_id
                or run_context.project_id != execution_state.project_id
            ):
                raise InvalidGraphError(
                    "RunContext diverge do estado da execução."
                )
        for stage_id, dependencies in workflow.stage_dependencies.items():
            if stage_id not in known:
                raise InvalidGraphError(
                    f"Dependências para etapa inexistente: {stage_id}"
                )
            if len(dependencies) != len(set(dependencies)):
                raise InvalidGraphError(
                    f"Dependências duplicadas em: {stage_id}"
                )
            unknown = set(dependencies) - known
            if unknown:
                raise InvalidGraphError(
                    f"Dependências inexistentes em {stage_id}: "
                    f"{sorted(unknown)}"
                )
            if stage_id in dependencies:
                raise InvalidGraphError(
                    f"Self-loop não permitido em: {stage_id}"
                )

    @staticmethod
    def _ordered_stage_ids(
        workflow: WorkflowDefinition,
        stage_ids: set[str],
    ) -> tuple[str, ...]:
        indegree = {stage_id: 0 for stage_id in stage_ids}
        dependents: dict[str, list[str]] = defaultdict(list)
        for stage_id, dependencies in workflow.stage_dependencies.items():
            for dependency in dependencies:
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
            raise InvalidGraphError(
                "Workflow contém ciclo de dependências."
            )
        return tuple(ordered)

    @staticmethod
    def _ordered_text(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {value.strip() for value in values if value.strip()},
                key=lambda value: (value.casefold(), value),
            )
        )
