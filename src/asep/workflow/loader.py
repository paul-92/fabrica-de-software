"""Leitura e validação semântica de workflows."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from asep.errors import (
    ConfigurationError,
    WorkflowValidationError,
    describe_validation_error,
)
from asep.models import RegistrySnapshot, WorkflowDefinition, WorkflowRegistryEntry
from asep.yaml_io import load_yaml


class WorkflowLoader:
    """Converte YAML em modelo e valida dependências, agentes e gates."""

    def load(
        self, entry: WorkflowRegistryEntry, registry: RegistrySnapshot
    ) -> WorkflowDefinition:
        path = (registry.root / entry.path).resolve()
        try:
            workflow = WorkflowDefinition.model_validate(load_yaml(path))
        except ValidationError as exc:
            raise WorkflowValidationError(
                f"Workflow inválido: {describe_validation_error(exc)}", path=path
            ) from exc
        except ConfigurationError as exc:
            raise WorkflowValidationError(
                f"Workflow inválido: {exc.message}", path=path
            ) from exc
        if workflow.id != entry.id or workflow.version != entry.version:
            raise WorkflowValidationError(
                "ID ou versão diverge do Registry.", path=path
            )
        self._validate_semantics(workflow, registry, path)
        return workflow

    def _validate_semantics(
        self, workflow: WorkflowDefinition, registry: RegistrySnapshot, path: Path
    ) -> None:
        stage_ids = [stage.id for stage in workflow.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise WorkflowValidationError("Etapas duplicadas.", path=path)
        known_stages = set(stage_ids)

        for stage_id, dependencies in workflow.stage_dependencies.items():
            if stage_id not in known_stages:
                raise WorkflowValidationError(
                    f"Dependências declaradas para etapa inexistente: {stage_id}",
                    path=path,
                )
            unknown = set(dependencies) - known_stages
            if unknown:
                raise WorkflowValidationError(
                    f"Dependências inexistentes em {stage_id}: {sorted(unknown)}",
                    path=path,
                )

        assigned_stages = set(workflow.assigned_agents)
        if assigned_stages != known_stages:
            missing = sorted(known_stages - assigned_stages)
            extra = sorted(assigned_stages - known_stages)
            raise WorkflowValidationError(
                f"Atribuição de agentes inconsistente; ausentes={missing}, extras={extra}",
                path=path,
            )
        unknown_agents = {
            agent
            for agents in workflow.assigned_agents.values()
            for agent in agents
            if agent not in registry.agents
        }
        if unknown_agents:
            raise WorkflowValidationError(
                f"Agentes não registrados: {sorted(unknown_agents)}", path=path
            )
        unknown_gates = set(workflow.quality_gates) - set(registry.quality_gates)
        if unknown_gates:
            raise WorkflowValidationError(
                f"Quality gates não registrados: {sorted(unknown_gates)}", path=path
            )
        unknown_stage_gate_stages = set(workflow.stage_quality_gates) - known_stages
        unknown_stage_gates = (
            set(workflow.stage_quality_gates.values())
            - set(workflow.quality_gates)
        )
        if unknown_stage_gate_stages or unknown_stage_gates:
            raise WorkflowValidationError(
                "Mapeamento stage_quality_gates inconsistente; "
                f"etapas={sorted(unknown_stage_gate_stages)}, "
                f"gates={sorted(unknown_stage_gates)}",
                path=path,
            )
        registry_entry = registry.workflows[workflow.id]
        workflow_agents = {
            agent for agents in workflow.assigned_agents.values() for agent in agents
        }
        if set(registry_entry.stages) != known_stages:
            raise WorkflowValidationError(
                "Etapas do workflow divergem do Registry.", path=path
            )
        if set(registry_entry.agents) != workflow_agents:
            raise WorkflowValidationError(
                "Agentes do workflow divergem do Registry.", path=path
            )
        if set(registry_entry.gates) != set(workflow.quality_gates):
            raise WorkflowValidationError(
                "Quality gates do workflow divergem do Registry.", path=path
            )
        self._validate_acyclic(workflow.stage_dependencies, known_stages, path)

    @staticmethod
    def _validate_acyclic(
        dependencies: dict[str, list[str]], stage_ids: set[str], path: Path
    ) -> None:
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

        for stage_id in stage_ids:
            visit(stage_id)
