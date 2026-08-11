"""Execução dos componentes internos de uma etapa de workflow."""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from asep.artifacts.manager import ArtifactManager
from asep.execution.models import (
    AgentContext,
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
    ArtifactReference,
    GateResult,
    ExecutionState,
    StageState,
    StageStatus,
)
from asep.execution_package import (
    ExecutionContext,
    ExecutionContract,
    ExecutionInput,
    ExecutionMetadata,
    ExecutionPackageBuilder,
    ExecutionQualityGate,
    ExecutionSubject,
)
from asep.models import (
    AgentContract,
    LoadedProject,
    RegistrySnapshot,
)
from asep.prompting import PromptBuildInput, PromptBuilder
from asep.providers import (
    AgentExecutionResult,
    AgentExecutionStatus,
    AgentProvider,
    ProviderError,
)
from asep.quality.engine import QualityGateEngine
from asep.quality_results import (
    QualityGateResultRepository,
    StoredQualityGateResult,
)
from asep.runtime.agent_runtime import AgentRuntime
from asep.yaml_io import load_yaml


@dataclass(frozen=True, slots=True)
class StageExecutionReport:
    """Resultado da execução interna de uma etapa, sem transições de estado."""

    agent_result: AgentResult
    artifact_references: tuple[ArtifactReference, ...] = ()
    gate_result: GateResult | None = None
    gate_artifact_reference: ArtifactReference | None = None
    provider_result: AgentExecutionResult | None = None


class StageExecutionService:
    """Executa agente, artefatos e gate sem decidir o estado do workflow."""

    def __init__(
        self,
        agent_runtime: AgentRuntime,
        artifact_manager: ArtifactManager,
        gate_engine: QualityGateEngine,
        *,
        provider: AgentProvider | None = None,
        prompt_builder: PromptBuilder | None = None,
        package_builder: ExecutionPackageBuilder | None = None,
        quality_gate_results: QualityGateResultRepository | None = None,
    ) -> None:
        self._agent_runtime = agent_runtime
        self._artifact_manager = artifact_manager
        self._gate_engine = gate_engine
        self._provider = provider
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._package_builder = package_builder or ExecutionPackageBuilder()
        self._quality_gate_results = quality_gate_results

    def execute(
        self,
        context: AgentContext,
        registry: RegistrySnapshot,
        artifacts_path: Path,
        gate_id: str,
        stage_status: StageStatus,
        logger: logging.Logger,
    ) -> StageExecutionReport:
        result = self._agent_runtime.execute(context, registry, logger)
        return self._finalize_result(
            result,
            context,
            artifacts_path,
            gate_id,
            stage_status,
            logger,
        )

    def _finalize_result(
        self,
        result: AgentResult,
        context: AgentContext,
        artifacts_path: Path,
        gate_id: str,
        stage_status: StageStatus,
        logger: logging.Logger,
        *,
        provider_result: AgentExecutionResult | None = None,
    ) -> StageExecutionReport:
        if result.status != AgentResultStatus.COMPLETED:
            return StageExecutionReport(
                agent_result=result,
                provider_result=provider_result,
            )

        references = tuple(
            self._artifact_manager.persist(
                draft,
                artifacts_path,
                run_id=context.run_id,
                project_id=context.project_id,
                stage_id=context.stage_id,
                agent_id=context.agent_id,
            )
            for draft in result.artifacts
        )
        for _reference in references:
            logger.info(
                "Artefato criado.",
                extra={
                    "event_type": "artifact_created",
                    "project_id": context.project_id,
                    "workflow_id": context.workflow_id,
                    "stage_id": context.stage_id,
                    "agent_id": context.agent_id,
                },
            )

        logger.info(
            "Quality gate iniciado.",
            extra={
                "event_type": "gate_started",
                "project_id": context.project_id,
                "workflow_id": context.workflow_id,
                "stage_id": context.stage_id,
            },
        )
        gate = self._gate_engine.evaluate(
            gate_id, result, list(references), stage_status
        )
        gate_reference = self._artifact_manager.persist(
            ArtifactDraft(
                relative_path=f"quality-gates/{context.stage_id}-result.yaml",
                type="yaml",
                content=yaml.safe_dump(
                    gate.model_dump(mode="json"),
                    allow_unicode=True,
                    sort_keys=False,
                ),
            ),
            artifacts_path,
            run_id=context.run_id,
            project_id=context.project_id,
            stage_id=context.stage_id,
            agent_id="quality-gate-engine",
        )
        if self._quality_gate_results is not None:
            self._quality_gate_results.record(
                StoredQualityGateResult.from_gate_result(gate)
            )
        logger.info(
            f"Quality gate concluído: {gate.decision}.",
            extra={
                "event_type": "gate_completed",
                "project_id": context.project_id,
                "workflow_id": context.workflow_id,
                "stage_id": context.stage_id,
            },
        )
        return StageExecutionReport(
            agent_result=result,
            artifact_references=references,
            gate_result=gate,
            gate_artifact_reference=gate_reference,
            provider_result=provider_result,
        )

    def execute_stage(
        self,
        project: LoadedProject,
        state: ExecutionState,
        stage: StageState,
        registry: RegistrySnapshot,
        artifacts_path: Path,
        logger: logging.Logger,
    ) -> StageExecutionReport:
        """Monta o contexto e delega a execução interna da etapa."""
        scope_path = project.path / "business-analysis" / "scope.md"
        constraints_path = (
            project.path / "business-analysis" / "constraints.md"
        )
        scope = (
            scope_path.read_text(encoding="utf-8")
            if scope_path.is_file()
            else None
        )
        constraints = (
            (constraints_path.read_text(encoding="utf-8"),)
            if constraints_path.is_file()
            else ()
        )
        context = AgentContext(
            run_id=state.run_id,
            project_id=state.project_id,
            project_name=project.definition.name,
            workflow_id=state.workflow_id,
            stage_id=stage.id,
            agent_id=stage.agent_id,
            started_at=datetime.now(UTC),
            objective=(
                project.definition.sprint.objective
                if project.definition.sprint
                else None
            ),
            scope_received=scope,
            constraints=constraints,
            pending_items=tuple(project.definition.open_questions),
        )
        if self._provider is not None:
            return self._execute_with_provider(
                project,
                context,
                registry,
                artifacts_path,
                stage.quality_gate_id or "QG-UNSPECIFIED",
                logger,
            )
        return self.execute(
            context,
            registry,
            artifacts_path,
            stage.quality_gate_id or "QG-UNSPECIFIED",
            StageStatus.RUNNING,
            logger,
        )

    def _execute_with_provider(
        self,
        project: LoadedProject,
        context: AgentContext,
        registry: RegistrySnapshot,
        artifacts_path: Path,
        gate_id: str,
        logger: logging.Logger,
    ) -> StageExecutionReport:
        contract = self._load_contract(registry, context.agent_id)
        prompt = self._prompt_builder.build(
            PromptBuildInput(
                run_id=context.run_id,
                project_id=context.project_id,
                project_name=context.project_name,
                workflow_id=context.workflow_id,
                stage_id=context.stage_id,
                agent_id=context.agent_id,
                stage_objective=context.objective,
                project_description=project.readme,
                agent_contract=contract.mission,
                required_inputs=tuple(contract.required_inputs),
                expected_artifacts=tuple(contract.required_outputs),
                quality_criteria=tuple(contract.success_criteria),
                restrictions=(
                    *context.constraints,
                    *contract.cannot,
                ),
                open_questions=context.pending_items,
            )
        )
        execution_context = ExecutionContext(
            project=ExecutionSubject(
                id=context.project_id,
                name=context.project_name,
                description=project.readme,
            ),
            workflow=ExecutionSubject(id=context.workflow_id),
            stage=ExecutionSubject(id=context.stage_id),
            inputs=self._execution_inputs(project, context),
            contract=ExecutionContract(
                id=contract.id,
                version=contract.version,
                mission=contract.mission,
                required_inputs=tuple(contract.required_inputs),
                expected_outputs=tuple(contract.required_outputs),
                constraints=tuple(contract.cannot),
            ),
            quality_gate=ExecutionQualityGate(
                id=gate_id,
                criteria=tuple(contract.success_criteria),
            ),
            open_questions=context.pending_items,
        )
        package = self._package_builder.build(
            prompt=prompt,
            context=execution_context,
            metadata=ExecutionMetadata(
                generator="asep",
                generator_version="0.1.0",
                python_version=platform.python_version(),
            ),
            run_id=context.run_id,
            project_id=context.project_id,
            workflow_id=context.workflow_id,
            stage_id=context.stage_id,
            agent_id=context.agent_id,
            created_by="stage-execution-service",
            expected_outputs=tuple(contract.required_outputs),
            constraints=(
                *context.constraints,
                *contract.cannot,
            ),
        )
        try:
            provider_result = self._provider.execute(package)
        except ProviderError as exc:
            provider_result = AgentExecutionResult(
                status=AgentExecutionStatus.FAILED,
                provider_name=self._provider.name,
                provider_version="unknown",
                errors=(exc.message,),
            )

        result = self._to_agent_result(context, provider_result)
        return self._finalize_result(
            result,
            context,
            artifacts_path,
            gate_id,
            StageStatus.RUNNING,
            logger,
            provider_result=provider_result,
        )

    @staticmethod
    def _execution_inputs(
        project: LoadedProject,
        context: AgentContext,
    ) -> tuple[ExecutionInput, ...]:
        inputs = [
            ExecutionInput(
                name="project-brief",
                value=project.readme,
            )
        ]
        if context.scope_received:
            inputs.append(
                ExecutionInput(
                    name="scope",
                    value=context.scope_received,
                )
            )
        return tuple(inputs)

    @staticmethod
    def _load_contract(
        registry: RegistrySnapshot,
        agent_id: str,
    ) -> AgentContract:
        reference = registry.contracts[agent_id]
        path = (registry.root / reference.path).resolve()
        return AgentContract.model_validate(load_yaml(path))

    @staticmethod
    def _to_agent_result(
        context: AgentContext,
        provider_result: AgentExecutionResult,
    ) -> AgentResult:
        finished_at = datetime.now(UTC)
        if provider_result.status == AgentExecutionStatus.SUCCESS:
            artifacts = [
                ArtifactDraft(
                    relative_path=(
                        f"provider-results/{context.stage_id}-result.md"
                    ),
                    content=provider_result.stdout,
                )
            ]
            status = AgentResultStatus.COMPLETED
        else:
            artifacts = []
            status = AgentResultStatus.FAILED

        errors = list(provider_result.errors)
        if status == AgentResultStatus.FAILED and not errors:
            detail = (
                provider_result.stderr.strip()
                or f"Provider retornou {provider_result.status}."
            )
            errors.append(detail)
        return AgentResult(
            status=status,
            agent_id=context.agent_id,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=finished_at,
            artifacts=artifacts,
            messages=(
                [provider_result.stdout]
                if provider_result.stdout
                else []
            ),
            warnings=list(provider_result.warnings),
            errors=errors,
            metadata={
                "provider_name": provider_result.provider_name,
                "provider_version": provider_result.provider_version,
                "provider_status": provider_result.status,
                "exit_code": provider_result.exit_code,
                "provider_metadata": provider_result.model_dump(
                    mode="json"
                )["metadata"],
                "produced_files": [
                    item.model_dump(mode="json")
                    for item in provider_result.produced_files
                ],
            },
        )
