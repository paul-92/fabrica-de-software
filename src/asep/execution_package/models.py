"""Modelos imutáveis do protocolo de pacotes de execução."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

ASEP_EXECUTION_PROTOCOL = "asep-execution-package"
ASEP_EXECUTION_PROTOCOL_VERSION = "1.0.0"
DEFAULT_EXECUTION_PACKAGE_VERSION = "1.0.0"


class ExecutionContextItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: str


class ExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: str
    required: bool = True


class ExecutionSubject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str | None = None
    description: str | None = None


class ExecutionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    version: str
    mission: str
    required_inputs: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


class ExecutionQualityGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    criteria: tuple[str, ...] = ()


class ExecutionContext(BaseModel):
    """Contexto estruturado consumível por qualquer provedor futuro."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project: ExecutionSubject
    workflow: ExecutionSubject
    stage: ExecutionSubject
    inputs: tuple[ExecutionInput, ...] = ()
    contract: ExecutionContract
    quality_gate: ExecutionQualityGate | None = None
    open_questions: tuple[str, ...] = ()
    additional_context: tuple[ExecutionContextItem, ...] = ()


class ExecutionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    generator: str
    generator_version: str
    python_version: str
    provider: None = None


class ExecutionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: str
    protocol_version: str
    package_version: str
    run_id: str
    project_id: str
    workflow_id: str
    stage_id: str
    agent_id: str
    created_by: str
    provider: None = None
    prompt_checksum: str
    context_checksum: str
    expected_outputs_checksum: str
    constraints_checksum: str

    @field_validator(
        "run_id",
        "project_id",
        "workflow_id",
        "stage_id",
        "agent_id",
        "created_by",
    )
    @classmethod
    def identifiers_are_safe_path_values(cls, value: str) -> str:
        if (
            not value.strip()
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
        ):
            raise ValueError("identificador não pode conter separadores de path")
        return value


class ExecutionPackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest: ExecutionManifest
    task: str
    context: ExecutionContext
    metadata: ExecutionMetadata
    expected_outputs: tuple[str, ...]
    constraints: tuple[str, ...]


class ExecutionPackageFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    path: Path


class ExecutionPackageResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    package_path: Path
    files: tuple[ExecutionPackageFile, ...]
    written_files: tuple[str, ...]
    unchanged_files: tuple[str, ...]
