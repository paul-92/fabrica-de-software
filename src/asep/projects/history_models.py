from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeUsage
from asep.access.models import LEGACY_ADMIN_USER_ID, LEGACY_ORGANIZATION_ID
from asep.quality_results import StoredQualityGateResult
from asep.repair import RepairResult
from asep.workspace_changes import WorkspaceChange


class ProjectExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProjectOperationalPlanOperation(StrEnum):
    ANALYZE_CONTEXT = "analyze_context"
    EXECUTE_WORKSPACE_TASK = "execute_workspace_task"
    CAPTURE_WORKSPACE_CHANGES = "capture_workspace_changes"
    INSPECT = "inspect"
    IMPLEMENT = "implement"
    VALIDATE = "validate"


class ProjectOperationalPlanSource(StrEnum):
    DETERMINISTIC = "deterministic"
    AI = "ai"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class ProjectOperationalPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str
    operation: ProjectOperationalPlanOperation
    description: str
    dependencies: tuple[str, ...] = ()
    target_hints: tuple[str, ...] = ()
    validation_hints: tuple[str, ...] = ()

    @field_validator("step_id", "description")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operational plan fields must not be blank")
        return normalized

    @field_validator("dependencies", "target_hints", "validation_hints")
    @classmethod
    def entries_not_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("operational plan entries must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("operational plan entries must be unique")
        return normalized


class ProjectOperationalPlan(BaseModel):
    """Bounded facts describing the work intended by one execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    steps: tuple[ProjectOperationalPlanStep, ...] = Field(
        min_length=1,
        max_length=7,
    )
    created_at: datetime
    source: ProjectOperationalPlanSource = ProjectOperationalPlanSource.DETERMINISTIC

    @field_validator("execution_id")
    @classmethod
    def execution_id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operational plan execution_id must not be blank")
        return normalized

    @field_validator("created_at")
    @classmethod
    def plan_timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("operational plan timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def steps_are_unique(self) -> "ProjectOperationalPlan":
        identifiers = tuple(step.step_id for step in self.steps)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("operational plan steps must be unique")
        return self


class ProjectValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProjectValidationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    validator_id: str
    targets: tuple[str, ...] = ()


class ProjectValidationStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    validators: tuple[str, ...] = Field(min_length=1)
    reason: str
    target_hints: tuple[ProjectValidationTarget, ...] = ()


class ProjectValidationFailureCategory(StrEnum):
    SYNTAX_OR_COMPILE_ERROR = "syntax_or_compile_error"
    TEST_FAILURE = "test_failure"
    IMPORT_ERROR = "import_error"
    ASSERTION_FAILURE = "assertion_failure"
    LINT_FAILURE = "lint_failure"
    BUILD_FAILURE = "build_failure"
    UNKNOWN = "unknown"


class ProjectValidationFailureAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    validator_id: str
    category: ProjectValidationFailureCategory
    summary: str
    relevant_paths: tuple[str, ...] = ()
    evidence: str = ""


class ProjectValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    sequence: int = Field(ge=1)
    validator: str = "pytest"
    command: tuple[str, ...] = Field(min_length=1)
    exit_code: int
    status: ProjectValidationStatus
    output: str
    completed_at: datetime

    @field_validator("execution_id", "validator")
    @classmethod
    def validation_execution_id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("validation execution_id must not be blank")
        return normalized

    @field_validator("command")
    @classmethod
    def command_entries_not_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("validation command entries must not be blank")
        return value

    @field_validator("completed_at")
    @classmethod
    def validation_timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("validation timestamp must be timezone-aware")
        return value


class ProjectRepairResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    result: RepairResult

    @field_validator("execution_id")
    @classmethod
    def repair_execution_id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("repair execution_id must not be blank")
        return normalized


class ProjectEngineeringStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    step_id: str
    executor: str = "developer_agent"
    tool_id: str
    succeeded: bool
    output: str
    started_at: datetime
    completed_at: datetime


class ProjectSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    @field_validator("session_id", "project_id", "title")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("session fields must not be blank")
        return normalized

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session timestamps must be timezone-aware")
        return value


class ProjectExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    session_id: str
    project_id: str
    organization_id: str = LEGACY_ORGANIZATION_ID
    requested_by_user_id: str = LEGACY_ADMIN_USER_ID
    runtime_id: str
    instruction: str
    execution_mode: AIRuntimeExecutionMode
    status: ProjectExecutionStatus
    operational_plan: ProjectOperationalPlan | None = None
    preparation_analysis: dict = Field(default_factory=dict)
    preparation_workspace_fingerprint: str | None = None
    preparation_context_fingerprint: str | None = None
    validation_strategy: ProjectValidationStrategy | None = None
    validations: tuple[ProjectValidationResult, ...] = ()
    failure_analyses: tuple[ProjectValidationFailureAnalysis, ...] = ()
    repair: ProjectRepairResult | None = None
    quality_gate: StoredQualityGateResult | None = None
    step_results: tuple[ProjectEngineeringStepResult, ...] = ()
    output: str | None = None
    model: str | None = None
    usage: AIRuntimeUsage | None = None
    changes: tuple[WorkspaceChange, ...] = ()
    error_code: str | None = None
    context_entry_count: int = Field(default=0, ge=0)
    context_truncated: bool = False
    context_char_count: int = Field(default=0, ge=0)
    context_omitted_execution_count: int = Field(default=0, ge=0)
    memory_entry_count: int = Field(default=0, ge=0)
    memory_char_count: int = Field(default=0, ge=0)
    memory_truncated: bool = False
    created_at: datetime
    completed_at: datetime | None = None

    @field_validator("execution_id", "session_id", "project_id", "runtime_id", "instruction")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("execution fields must not be blank")
        return normalized

    @field_validator("created_at", "completed_at")
    @classmethod
    def timestamp_is_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("execution timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def terminal_state_is_consistent(self) -> "ProjectExecution":
        terminal = self.status in {
            ProjectExecutionStatus.SUCCEEDED,
            ProjectExecutionStatus.FAILED,
        }
        if terminal != (self.completed_at is not None):
            raise ValueError("terminal execution must have completed_at")
        if self.status is ProjectExecutionStatus.SUCCEEDED and self.error_code is not None:
            raise ValueError("succeeded execution cannot have error_code")
        if self.status is ProjectExecutionStatus.FAILED and not self.error_code:
            raise ValueError("failed execution must have error_code")
        if (
            self.operational_plan is not None
            and self.operational_plan.execution_id != self.execution_id
        ):
            raise ValueError("operational plan must belong to the execution")
        if any(
            validation.execution_id != self.execution_id
            for validation in self.validations
        ):
            raise ValueError("validations must belong to the execution")
        if (
            self.validation_strategy is not None
            and self.validation_strategy.execution_id != self.execution_id
        ):
            raise ValueError("validation strategy must belong to the execution")
        if any(
            analysis.execution_id != self.execution_id
            for analysis in self.failure_analyses
        ):
            raise ValueError("failure analyses must belong to the execution")
        if self.repair is not None and self.repair.execution_id != self.execution_id:
            raise ValueError("repair must belong to the execution")
        if (
            self.quality_gate is not None
            and self.quality_gate.run_id != self.execution_id
        ):
            raise ValueError("quality gate must belong to the execution")
        if any(item.execution_id != self.execution_id for item in self.step_results):
            raise ValueError("step results must belong to the execution")
        return self


__all__ = [
    "ProjectExecution",
    "ProjectEngineeringStepResult",
    "ProjectExecutionStatus",
    "ProjectOperationalPlan",
    "ProjectOperationalPlanOperation",
    "ProjectOperationalPlanSource",
    "ProjectOperationalPlanStep",
    "ProjectRepairResult",
    "ProjectValidationResult",
    "ProjectValidationFailureAnalysis",
    "ProjectValidationFailureCategory",
    "ProjectValidationStrategy",
    "ProjectValidationTarget",
    "ProjectValidationStatus",
    "ProjectSession",
]
