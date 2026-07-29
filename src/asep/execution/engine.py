"""Motor determinístico de workflows estritamente sequenciais."""

from __future__ import annotations

from pathlib import Path

from asep.errors import UnsupportedCapabilityError, WorkflowValidationError
from asep.execution.models import ExecutionState, StageState, StageStatus
from asep.models import WorkflowDefinition


class SequentialWorkflowEngine:
    """Valida capacidade e seleciona uma única próxima etapa."""

    def validate(self, workflow: WorkflowDefinition, *, path: Path | None = None) -> None:
        unsupported = [
            f"{stage.id}:{stage.mode}"
            for stage in workflow.stages
            if stage.mode != "sequential"
        ]
        if unsupported:
            raise UnsupportedCapabilityError(
                f"Workflow usa modos não suportados: {unsupported}", path=path
            )
        ambiguous_agents = [
            stage.id
            for stage in workflow.stages
            if len(workflow.assigned_agents.get(stage.id, [])) != 1
        ]
        if ambiguous_agents:
            raise UnsupportedCapabilityError(
                f"Etapas exigem exatamente um agente executável: {ambiguous_agents}",
                path=path,
            )
        missing_gates = [
            stage.id
            for stage in workflow.stages
            if stage.id not in workflow.stage_quality_gates
        ]
        if missing_gates:
            raise UnsupportedCapabilityError(
                f"Etapas sem quality gate explícito: {missing_gates}", path=path
            )
        stage_ids = [stage.id for stage in workflow.stages]
        known = set(stage_ids)
        for stage_id, dependencies in workflow.stage_dependencies.items():
            if stage_id not in known:
                raise WorkflowValidationError(
                    f"Dependências para etapa inexistente: {stage_id}", path=path
                )
            missing = set(dependencies) - known
            if missing:
                raise WorkflowValidationError(
                    f"Dependências inexistentes em {stage_id}: {sorted(missing)}",
                    path=path,
                )
        self._topological_order(workflow.stage_dependencies, stage_ids, path)

    def ordered_stage_ids(self, workflow: WorkflowDefinition) -> tuple[str, ...]:
        self.validate(workflow)
        return tuple(
            self._topological_order(
                workflow.stage_dependencies,
                [stage.id for stage in workflow.stages],
                None,
            )
        )

    def next_stage(
        self, workflow: WorkflowDefinition, state: ExecutionState
    ) -> StageState | None:
        by_id = {stage.id: stage for stage in state.stages}
        for stage_id in self.ordered_stage_ids(workflow):
            stage = by_id[stage_id]
            if stage.status == StageStatus.COMPLETED:
                continue
            dependencies = workflow.stage_dependencies.get(stage_id, [])
            if not all(
                by_id[dependency].status == StageStatus.COMPLETED
                for dependency in dependencies
            ):
                return None
            if stage.status in {
                StageStatus.PENDING,
                StageStatus.READY,
                StageStatus.BLOCKED,
                StageStatus.FAILED,
                StageStatus.AWAITING_APPROVAL,
            }:
                return stage
            return None
        return None

    @staticmethod
    def _topological_order(
        dependencies: dict[str, list[str]],
        stage_ids: list[str],
        path: Path | None,
    ) -> list[str]:
        order: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(stage_id: str) -> None:
            if stage_id in visiting:
                raise WorkflowValidationError(
                    f"Ciclo de dependência detectado em: {stage_id}", path=path
                )
            if stage_id in visited:
                return
            visiting.add(stage_id)
            for dependency in dependencies.get(stage_id, []):
                visit(dependency)
            visiting.remove(stage_id)
            visited.add(stage_id)
            order.append(stage_id)

        for stage_id in stage_ids:
            visit(stage_id)
        return order
