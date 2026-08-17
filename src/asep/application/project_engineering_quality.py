"""Quality Gate mapping for bounded project engineering validation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactReference,
    GateResult,
    StageStatus,
)
from asep.projects import (
    ProjectExecution,
    ProjectValidationResult,
    ProjectValidationStatus,
)
from asep.quality.engine import QualityGateEngine
from asep.quality_results import (
    QualityGateResultRepository,
    StoredQualityGateResult,
)
from asep.workspace_changes import WorkspaceChangeType

_GATE_ID = "PROJECT-ENGINEERING-VALIDATION"
_STAGE_ID = "project-engineering-validation"


class ProjectQualityGateCapability(Protocol):
    def evaluate_and_record(
        self,
        execution: ProjectExecution,
        validation: ProjectValidationResult | tuple[ProjectValidationResult, ...],
        workspace: Path,
    ) -> StoredQualityGateResult: ...


class ProjectQualityGateService:
    def __init__(
        self,
        engine: QualityGateEngine,
        results: QualityGateResultRepository,
    ) -> None:
        self._engine = engine
        self._results = results

    def evaluate_and_record(
        self,
        execution: ProjectExecution,
        validation: ProjectValidationResult | tuple[ProjectValidationResult, ...],
        workspace: Path,
    ) -> StoredQualityGateResult:
        validations = validation if isinstance(validation, tuple) else (validation,)
        passed = (
            any(item.status is ProjectValidationStatus.PASSED for item in validations)
            and all(item.status is not ProjectValidationStatus.FAILED for item in validations)
        )
        completed_at = max(item.completed_at for item in validations)
        agent_result = AgentResult(
            status=(
                AgentResultStatus.COMPLETED if passed else AgentResultStatus.FAILED
            ),
            agent_id="project-engineering",
            stage_id=_STAGE_ID,
            run_id=execution.execution_id,
            started_at=execution.created_at,
            finished_at=completed_at,
            messages=["Project validation passed."] if passed else [],
            errors=[] if passed else ["Project validation failed."],
            metadata={
                "project_execution_id": execution.execution_id,
                "validation_exit_code": validations[-1].exit_code,
                "validation_exit_codes": {
                    item.validator: item.exit_code for item in validations
                },
            },
        )
        gate = self._engine.evaluate(
            _GATE_ID,
            agent_result,
            self._artifact_references(execution, workspace),
            StageStatus.RUNNING,
        )
        stored = StoredQualityGateResult.from_gate_result(
            GateResult.model_validate(gate.model_dump(mode="json"))
        )
        # In this bounded flow run_id is explicitly the canonical
        # ProjectExecution.execution_id; it is not a SequentialExecution id.
        if stored.run_id != execution.execution_id:
            raise ValueError("quality gate identity mismatch")
        self._results.record(stored)
        return stored

    @staticmethod
    def _artifact_references(
        execution: ProjectExecution,
        workspace: Path,
    ) -> list[ArtifactReference]:
        references: list[ArtifactReference] = []
        root = workspace.resolve()
        for change in execution.changes:
            if change.change_type is WorkspaceChangeType.DELETED:
                continue
            path = (root / change.path).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                continue
            if not path.is_file():
                continue
            references.append(ArtifactReference(
                artifact_id=f"{execution.execution_id}:{change.path}",
                run_id=execution.execution_id,
                project_id=execution.project_id,
                stage_id=_STAGE_ID,
                agent_id="project-engineering",
                path=change.path,
                type="workspace-file",
                created_at=execution.created_at,
                checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
            ))
        return references


__all__ = ["ProjectQualityGateCapability", "ProjectQualityGateService"]
