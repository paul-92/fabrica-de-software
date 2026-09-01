from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from asep.projects import (
    ProjectExecution,
    ProjectSession,
    SessionMemoryEntry,
    SessionMemoryKind,
    WorkspaceProject,
    WorkspaceDirectory,
    WorkspaceFileContent,
    ProjectOperationalPlan,
    ProjectRepairResult,
    ProjectValidationResult,
)
from asep.quality_results import StoredQualityGateResult
from asep.application import SessionMemorySearchItem, SessionMemorySearchPage
from asep.ai_runtime import AIRuntimeExecutionMode
from asep.workspace_changes import WorkspaceChangeType


class ProjectHttpSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateProjectRequest(ProjectHttpSchema):
    name: str

    @field_validator("name")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value


class ProjectResponse(ProjectHttpSchema):
    project_id: str
    name: str
    workspace_id: str | None
    workspace_kind: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: WorkspaceProject) -> "ProjectResponse":
        return cls(
            project_id=project.project_id,
            name=project.name,
            workspace_id=project.workspace_id,
            workspace_kind=project.workspace_kind,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectListResponse(ProjectHttpSchema):
    items: tuple[ProjectResponse, ...]


class WorkspaceEntryResponse(ProjectHttpSchema):
    path: str
    name: str
    kind: str
    size: int | None


class WorkspaceDirectoryResponse(ProjectHttpSchema):
    path: str
    entries: tuple[WorkspaceEntryResponse, ...]

    @classmethod
    def from_domain(cls, directory: WorkspaceDirectory) -> "WorkspaceDirectoryResponse":
        return cls.model_validate(directory.model_dump(mode="json"))


class WorkspaceFileContentResponse(ProjectHttpSchema):
    path: str
    name: str
    content: str
    size: int
    language: str
    truncated: bool

    @classmethod
    def from_domain(cls, content: WorkspaceFileContent) -> "WorkspaceFileContentResponse":
        return cls.model_validate(content.model_dump(mode="json"))


class ProjectAIRuntimeExecutionRequestBody(ProjectHttpSchema):
    session_id: str
    runtime_id: str
    instruction: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY
    dependency_requests: tuple[dict[str, Any], ...] = ()
    sprint_id: str | None = None
    sprint_name: str | None = None
    engineering_phase: str | None = None

    @field_validator("session_id", "runtime_id", "instruction")
    @classmethod
    def execution_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campo obrigatório não pode ser vazio")
        return value.strip()


class ProjectEngineeringPreparationResponse(ProjectHttpSchema):
    execution_id: str
    project_id: str
    session_id: str
    runtime_id: str
    instruction: str
    status: str
    analysis: dict[str, Any]
    operational_plan: "OperationalPlanResponse"
    dependency_plan: dict[str, Any]
    error_code: str | None = None
    blocker: str | None = None
    next_action: str | None = None
    sprint_id: str | None = None
    sprint_name: str | None = None
    engineering_phase: str | None = None
    created_at: datetime


class AIRuntimeUsageResponse(ProjectHttpSchema):
    input_units: int | None
    output_units: int | None
    total_units: int | None
    cost: float | None


class WorkspaceChangeResponse(ProjectHttpSchema):
    path: str
    change_type: WorkspaceChangeType
    size_before: int | None
    size_after: int | None


class OperationalPlanStepResponse(ProjectHttpSchema):
    step_id: str
    operation: str
    description: str
    dependencies: tuple[str, ...] = ()
    target_hints: tuple[str, ...] = ()
    validation_hints: tuple[str, ...] = ()


class OperationalPlanResponse(ProjectHttpSchema):
    execution_id: str
    steps: tuple[OperationalPlanStepResponse, ...]
    created_at: datetime
    source: str = "deterministic"

    @classmethod
    def from_domain(cls, plan: ProjectOperationalPlan | None):
        return None if plan is None else cls.model_validate(plan.model_dump(mode="json"))


class ValidationResponse(ProjectHttpSchema):
    execution_id: str
    sequence: int
    validator: str = "pytest"
    command: tuple[str, ...]
    exit_code: int
    status: str
    output: str
    completed_at: datetime

    @classmethod
    def from_domain(cls, result: ProjectValidationResult):
        return cls.model_validate(result.model_dump(mode="json"))


class RepairResponse(ProjectHttpSchema):
    execution_id: str
    outcome: str
    attempt_count: int

    @classmethod
    def from_domain(cls, repair: ProjectRepairResult | None):
        if repair is None:
            return None
        return cls(
            execution_id=repair.execution_id,
            outcome=repair.result.status.value,
            attempt_count=len(repair.result.attempts),
        )


class ProjectQualityGateResponse(ProjectHttpSchema):
    gate_id: str
    execution_id: str
    stage_id: str
    decision: str
    satisfied_criteria: tuple[str, ...]
    unsatisfied_criteria: tuple[str, ...]
    evaluated_at: datetime

    @classmethod
    def from_domain(cls, gate: StoredQualityGateResult | None):
        if gate is None:
            return None
        return cls(
            gate_id=gate.gate_id,
            execution_id=gate.run_id,
            stage_id=gate.stage_id,
            decision=gate.decision.value,
            satisfied_criteria=gate.satisfied_criteria,
            unsatisfied_criteria=gate.unsatisfied_criteria,
            evaluated_at=gate.evaluated_at,
        )


class ProjectEngineeringStepResultResponse(ProjectHttpSchema):
    execution_id: str
    step_id: str
    executor: str
    tool_id: str
    succeeded: bool
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime


class ProjectIdempotentNoOpEvidenceResponse(ProjectHttpSchema):
    prior_execution_id: str
    workspace_fingerprint: str
    artifact_paths: tuple[str, ...]


class ProjectAIRuntimeExecutionResponse(ProjectHttpSchema):
    execution_id: str
    output: str
    runtime_id: str
    model_id: str
    usage: AIRuntimeUsageResponse | None
    metadata: dict[str, Any]
    execution_mode: AIRuntimeExecutionMode
    changes: tuple[WorkspaceChangeResponse, ...] = ()
    context_entry_count: int
    context_truncated: bool
    context_char_count: int
    context_omitted_execution_count: int
    memory_entry_count: int
    memory_char_count: int
    memory_truncated: bool
    status: str | None = None
    instruction: str | None = None
    operational_plan: OperationalPlanResponse | None = None
    validations: tuple[ValidationResponse, ...] | None = None
    repair: RepairResponse | None = None
    quality_gate: ProjectQualityGateResponse | None = None
    step_results: tuple[ProjectEngineeringStepResultResponse, ...] | None = None
    error_code: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    idempotent_noop_evidence: ProjectIdempotentNoOpEvidenceResponse | None = None


class CreateProjectSessionRequest(ProjectHttpSchema):
    title: str

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized


class ProjectSessionResponse(ProjectHttpSchema):
    session_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, session: ProjectSession) -> "ProjectSessionResponse":
        return cls.model_validate(session.model_dump(mode="json"))


class ProjectSessionListResponse(ProjectHttpSchema):
    items: tuple[ProjectSessionResponse, ...]


class CreateSessionMemoryRequest(ProjectHttpSchema):
    kind: SessionMemoryKind
    content: str

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("memory content must not be blank")
        return normalized


class SessionMemoryResponse(ProjectHttpSchema):
    memory_id: str
    session_id: str
    project_id: str
    kind: SessionMemoryKind
    content: str
    source_execution_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, entry: SessionMemoryEntry) -> "SessionMemoryResponse":
        return cls.model_validate(entry.model_dump(mode="json"))

    @classmethod
    def from_application(
        cls,
        item: SessionMemorySearchItem,
    ) -> "SessionMemoryResponse":
        return cls.model_validate(item.model_dump(mode="json"))


class SessionMemoryListResponse(ProjectHttpSchema):
    items: tuple[SessionMemoryResponse, ...]


class SessionMemorySearchResponse(ProjectHttpSchema):
    items: tuple[SessionMemoryResponse, ...]
    next_cursor: str | None

    @classmethod
    def from_application(
        cls,
        page: SessionMemorySearchPage,
    ) -> "SessionMemorySearchResponse":
        return cls(
            items=tuple(
                SessionMemoryResponse.from_application(item)
                for item in page.items
            ),
            next_cursor=page.next_cursor,
        )


class ProjectExecutionResponse(ProjectHttpSchema):
    execution_id: str
    session_id: str
    project_id: str
    runtime_id: str
    instruction: str
    execution_mode: AIRuntimeExecutionMode
    status: str
    output: str | None
    model: str | None
    usage: AIRuntimeUsageResponse | None
    changes: tuple[WorkspaceChangeResponse, ...]
    error_code: str | None
    error_detail: str | None = None
    blocker: str | None = None
    next_action: str | None = None
    context_entry_count: int
    context_truncated: bool
    context_char_count: int
    context_omitted_execution_count: int
    memory_entry_count: int
    memory_char_count: int
    memory_truncated: bool
    created_at: datetime
    completed_at: datetime | None
    operational_plan: OperationalPlanResponse | None
    validations: tuple[ValidationResponse, ...]
    repair: RepairResponse | None
    quality_gate: ProjectQualityGateResponse | None
    step_results: tuple[ProjectEngineeringStepResultResponse, ...]
    idempotent_noop_evidence: ProjectIdempotentNoOpEvidenceResponse | None
    dependency_requests: tuple[dict[str, Any], ...] = ()
    dependency_plan: dict[str, Any] | None = None
    sprint_id: str | None = None
    sprint_name: str | None = None
    engineering_phase: str | None = None
    dependency_provisioning: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_domain(cls, execution: ProjectExecution, dependency_provisioning: tuple[dict[str, Any], ...] = ()) -> "ProjectExecutionResponse":
        return cls.model_validate({
            **execution.model_dump(
                mode="json",
                exclude={
                    "operational_plan", "validation_strategy", "validations",
                    "failure_analyses", "repair", "quality_gate", "step_results",
                    "preparation_analysis", "preparation_workspace_fingerprint",
                    "preparation_context_fingerprint",
                    "completion_workspace_fingerprint",
                    "organization_id", "requested_by_user_id",
                },
            ),
            "operational_plan": OperationalPlanResponse.from_domain(
                execution.operational_plan
            ),
            "validations": tuple(
                ValidationResponse.from_domain(item)
                for item in execution.validations
            ),
            "repair": RepairResponse.from_domain(execution.repair),
            "quality_gate": ProjectQualityGateResponse.from_domain(
                execution.quality_gate
            ),
            "step_results": tuple(
                ProjectEngineeringStepResultResponse.model_validate(
                    item.model_dump(mode="json")
                )
                for item in execution.step_results
            ),
            "dependency_provisioning": dependency_provisioning,
        })


class ProjectExecutionListResponse(ProjectHttpSchema):
    items: tuple[ProjectExecutionResponse, ...]
