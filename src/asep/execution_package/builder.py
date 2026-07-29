"""Construção determinística de pacotes de execução."""

from __future__ import annotations

from asep.execution_package.models import (
    ASEP_EXECUTION_PROTOCOL,
    ASEP_EXECUTION_PROTOCOL_VERSION,
    DEFAULT_EXECUTION_PACKAGE_VERSION,
    ExecutionContext,
    ExecutionContract,
    ExecutionManifest,
    ExecutionMetadata,
    ExecutionPackage,
    ExecutionQualityGate,
)
from asep.execution_package.serializer import ExecutionPackageSerializer
from asep.prompting.models import PromptBuildResult


class ExecutionPackageBuilder:
    """Combina prompt e contexto estruturado sem IO ou efeitos colaterais."""

    def __init__(
        self,
        serializer: ExecutionPackageSerializer | None = None,
    ) -> None:
        self._serializer = serializer or ExecutionPackageSerializer()

    def build(
        self,
        *,
        prompt: PromptBuildResult,
        context: ExecutionContext,
        metadata: ExecutionMetadata,
        run_id: str,
        project_id: str,
        workflow_id: str,
        stage_id: str,
        agent_id: str,
        created_by: str,
        expected_outputs: tuple[str, ...] = (),
        constraints: tuple[str, ...] = (),
        package_version: str = DEFAULT_EXECUTION_PACKAGE_VERSION,
    ) -> ExecutionPackage:
        normalized_context = self._normalize_context(context)
        normalized_outputs = self._sorted_unique(expected_outputs)
        normalized_constraints = self._sorted_unique(constraints)
        manifest = ExecutionManifest(
            protocol=ASEP_EXECUTION_PROTOCOL,
            protocol_version=ASEP_EXECUTION_PROTOCOL_VERSION,
            package_version=package_version,
            run_id=run_id,
            project_id=project_id,
            workflow_id=workflow_id,
            stage_id=stage_id,
            agent_id=agent_id,
            created_by=created_by,
            provider=None,
            prompt_checksum=self._serializer.checksum_text(prompt.prompt),
            context_checksum=self._serializer.checksum_json(
                normalized_context
            ),
            expected_outputs_checksum=self._serializer.checksum_json(
                list(normalized_outputs)
            ),
            constraints_checksum=self._serializer.checksum_json(
                list(normalized_constraints)
            ),
        )
        return ExecutionPackage(
            manifest=manifest,
            task=prompt.prompt,
            context=normalized_context,
            metadata=metadata,
            expected_outputs=normalized_outputs,
            constraints=normalized_constraints,
        )

    @classmethod
    def _normalize_context(
        cls, context: ExecutionContext
    ) -> ExecutionContext:
        contract = ExecutionContract(
            id=context.contract.id,
            version=context.contract.version,
            mission=context.contract.mission,
            required_inputs=context.contract.required_inputs,
            expected_outputs=cls._sorted_unique(
                context.contract.expected_outputs
            ),
            constraints=cls._sorted_unique(context.contract.constraints),
        )
        quality_gate = (
            ExecutionQualityGate(
                id=context.quality_gate.id,
                criteria=cls._sorted_unique(context.quality_gate.criteria),
            )
            if context.quality_gate
            else None
        )
        return ExecutionContext(
            project=context.project,
            workflow=context.workflow,
            stage=context.stage,
            inputs=context.inputs,
            contract=contract,
            quality_gate=quality_gate,
            open_questions=cls._sorted_unique(context.open_questions),
            additional_context=tuple(
                sorted(
                    context.additional_context,
                    key=lambda item: (
                        item.name.casefold(),
                        item.name,
                        item.value,
                    ),
                )
            ),
        )

    @staticmethod
    def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = (value.strip() for value in values if value.strip())
        unique = dict.fromkeys(normalized)
        return tuple(sorted(unique, key=lambda value: (value.casefold(), value)))
