"""DTOs HTTP v1 e mapeamento do caso de uso Intelligent Engineering."""

from __future__ import annotations

from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from asep.agents import AgentId
from asep.ai_planning import AutonomousEngineeringRequest
from asep.application import (
    ApplicationIntelligentEngineeringRequest,
    ApplicationIntelligentEngineeringResult,
)
from asep.intelligence import KnowledgeAwareContext
from asep.memory import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
)
from asep.planning import PlanningContext, PlanningRequest
from asep.repair import FailureAnalysis


class HttpSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemoryEntryDto(HttpSchema):
    memory_id: str
    agent_id: str
    execution_id: str
    workflow_execution_id: str | None = None
    category: MemoryCategory
    importance: MemoryImportance = MemoryImportance.NORMAL
    content: str
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None

    @field_validator(
        "memory_id",
        "agent_id",
        "execution_id",
        "workflow_execution_id",
        "content",
    )
    @classmethod
    def identifiers_and_content_are_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identificadores e conteúdo não podem ser vazios")
        return value

    @field_validator("created_at", "updated_at", "expires_at")
    @classmethod
    def timestamps_are_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("timestamps devem possuir timezone")
        return value

    @model_validator(mode="after")
    def timestamps_are_consistent(self) -> MemoryEntryDto:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at não pode preceder created_at")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at deve suceder created_at")
        return self

    def to_domain(self) -> MemoryEntry:
        return MemoryEntry(
            memory_id=MemoryId(value=self.memory_id),
            agent_id=AgentId(value=self.agent_id),
            execution_id=self.execution_id,
            workflow_execution_id=self.workflow_execution_id,
            category=self.category,
            importance=self.importance,
            content=self.content,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=self.updated_at,
            expires_at=self.expires_at,
        )

    @classmethod
    def from_domain(cls, entry: MemoryEntry) -> MemoryEntryDto:
        return cls(
            memory_id=entry.memory_id.value,
            agent_id=entry.agent_id.value,
            execution_id=entry.execution_id,
            workflow_execution_id=entry.workflow_execution_id,
            category=entry.category,
            importance=entry.importance,
            content=entry.content,
            metadata=dict(entry.metadata),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            expires_at=entry.expires_at,
        )


class PlanningContextDto(HttpSchema):
    objective: str
    memory: tuple[MemoryEntryDto, ...] = ()
    workflow: dict[str, JsonValue] = Field(default_factory=dict)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    available_capabilities: tuple[str, ...] = ()
    available_tools: dict[str, str] = Field(default_factory=dict)

    @field_validator("objective")
    @classmethod
    def objective_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("objective não pode ser vazio")
        return value

    @field_validator("available_capabilities")
    @classmethod
    def capabilities_are_unique(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("available_capabilities possui duplicatas")
        return value

    def to_domain(self) -> PlanningContext:
        return PlanningContext(
            objective=self.objective,
            memory=tuple(entry.to_domain() for entry in self.memory),
            workflow=self.workflow,
            metadata=self.metadata,
            constraints=self.constraints,
            available_capabilities=self.available_capabilities,
            available_tools=self.available_tools,
        )

    @classmethod
    def from_domain(cls, context: PlanningContext) -> PlanningContextDto:
        return cls(
            objective=context.objective,
            memory=tuple(MemoryEntryDto.from_domain(e) for e in context.memory),
            workflow=dict(context.workflow),
            metadata=dict(context.metadata),
            constraints=context.constraints,
            available_capabilities=context.available_capabilities,
            available_tools=dict(context.available_tools),
        )


class PlanningRequestDto(HttpSchema):
    goal: str
    context: PlanningContextDto
    workflow_execution_id: str | None = None
    agent_id: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("goal", "workflow_execution_id", "agent_id")
    @classmethod
    def request_text_is_not_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("identificadores e objetivo não podem ser vazios")
        return value

    def to_domain(self) -> PlanningRequest:
        return PlanningRequest(
            goal=self.goal,
            context=self.context.to_domain(),
            workflow_execution_id=self.workflow_execution_id,
            agent_id=(AgentId(value=self.agent_id) if self.agent_id else None),
            metadata=self.metadata,
        )

    @classmethod
    def from_domain(cls, request: PlanningRequest) -> PlanningRequestDto:
        return cls(
            goal=request.goal,
            context=PlanningContextDto.from_domain(request.context),
            workflow_execution_id=request.workflow_execution_id,
            agent_id=request.agent_id.value if request.agent_id else None,
            metadata=dict(request.metadata),
        )


class KnowledgeAwareContextDto(HttpSchema):
    base_context: dict[str, JsonValue] = Field(default_factory=dict)
    learned_entries: tuple[MemoryEntryDto, ...] = ()
    knowledge_count: int
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def count_matches_entries(self) -> KnowledgeAwareContextDto:
        if self.knowledge_count != len(self.learned_entries):
            raise ValueError(
                "knowledge_count deve corresponder às entradas aprendidas"
            )
        return self

    def to_domain(self) -> KnowledgeAwareContext:
        return KnowledgeAwareContext(
            base_context=self.base_context,
            learned_entries=tuple(
                entry.to_domain() for entry in self.learned_entries
            ),
            knowledge_count=self.knowledge_count,
            metadata=self.metadata,
        )


class FailureAnalysisDto(HttpSchema):
    summary: str
    failure_output: str = ""
    affected_paths: tuple[str, ...] = ()
    probable_cause: str | None = None

    @field_validator("summary")
    @classmethod
    def summary_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary não pode ser vazio")
        return value

    def to_domain(self) -> FailureAnalysis:
        return FailureAnalysis(**self.model_dump(mode="python"))

    @classmethod
    def from_domain(cls, analysis: FailureAnalysis) -> FailureAnalysisDto:
        return cls.model_validate(analysis.model_dump(mode="python"))


class AutonomousEngineeringRequestDto(HttpSchema):
    analysis: FailureAnalysisDto
    replacement_contents: dict[str, str]
    test_paths: tuple[str, ...] = ("tests",)

    def to_domain(self) -> AutonomousEngineeringRequest:
        return AutonomousEngineeringRequest(
            analysis=self.analysis.to_domain(),
            replacement_contents=self.replacement_contents,
            test_paths=self.test_paths,
        )


class IntelligentEngineeringExecuteRequest(HttpSchema):
    planning_request: PlanningRequestDto
    knowledge_context: KnowledgeAwareContextDto
    engineering_request: AutonomousEngineeringRequestDto

    def to_application(self) -> ApplicationIntelligentEngineeringRequest:
        return ApplicationIntelligentEngineeringRequest(
            planning_request=self.planning_request.to_domain(),
            knowledge_context=self.knowledge_context.to_domain(),
            engineering_request=self.engineering_request.to_domain(),
        )


class PlanStepDto(HttpSchema):
    step_id: str
    description: str
    required_capability: str
    tool_id: str | None
    agent_id: str | None
    dependencies: tuple[str, ...]
    priority: int
    status: str
    estimated_cost: float
    estimated_duration_seconds: float
    metadata: dict[str, JsonValue]

    @classmethod
    def from_domain(cls, step) -> PlanStepDto:
        return cls(
            step_id=step.step_id,
            description=step.description,
            required_capability=step.required_capability,
            tool_id=step.tool_id.value if step.tool_id else None,
            agent_id=step.agent_id.value if step.agent_id else None,
            dependencies=step.dependencies,
            priority=step.priority,
            status=step.status.value,
            estimated_cost=step.estimated_cost,
            estimated_duration_seconds=step.estimated_duration_seconds,
            metadata=dict(step.metadata),
        )


class ExecutionPlanDto(HttpSchema):
    plan_id: str
    goal: str
    steps: tuple[PlanStepDto, ...]
    estimated_cost: float
    estimated_duration_seconds: float
    created_at: datetime
    metadata: dict[str, JsonValue]


class PlanningStatisticsDto(HttpSchema):
    total_steps: int
    dependency_count: int
    maximum_depth: int
    estimated_cost: float
    estimated_duration_seconds: float
    memory_entries_considered: int


class PlanningResultDto(HttpSchema):
    plan: ExecutionPlanDto
    warnings: tuple[str, ...]
    validation_messages: tuple[str, ...]
    statistics: PlanningStatisticsDto

    @classmethod
    def from_domain(cls, result) -> PlanningResultDto:
        return cls(
            plan=ExecutionPlanDto(
                plan_id=result.plan.plan_id,
                goal=result.plan.goal,
                steps=tuple(PlanStepDto.from_domain(s) for s in result.plan.steps),
                estimated_cost=result.plan.estimated_cost,
                estimated_duration_seconds=result.plan.estimated_duration_seconds,
                created_at=result.plan.created_at,
                metadata=dict(result.plan.metadata),
            ),
            warnings=result.warnings,
            validation_messages=result.validation_messages,
            statistics=PlanningStatisticsDto.model_validate(
                result.statistics.model_dump(mode="python")
            ),
        )


class RepairChangeDto(HttpSchema):
    path: str
    content: str
    overwrite: bool
    reason: str


class RepairPlanDto(HttpSchema):
    analysis: FailureAnalysisDto
    changes: tuple[RepairChangeDto, ...]
    test_paths: tuple[str, ...]

    @classmethod
    def from_domain(cls, plan) -> RepairPlanDto:
        return cls(
            analysis=FailureAnalysisDto.from_domain(plan.analysis),
            changes=tuple(
                RepairChangeDto.model_validate(c.model_dump(mode="python"))
                for c in plan.changes
            ),
            test_paths=plan.test_paths,
        )


class RepairAttemptDto(HttpSchema):
    attempt: int
    plan: RepairPlanDto
    status: str
    validation_output: str
    messages: tuple[str, ...]


class RepairResultDto(HttpSchema):
    status: str
    attempts: tuple[RepairAttemptDto, ...]
    final_analysis: FailureAnalysisDto | None
    messages: tuple[str, ...]

    @classmethod
    def from_domain(cls, result) -> RepairResultDto:
        return cls(
            status=result.status.value,
            attempts=tuple(
                RepairAttemptDto(
                    attempt=a.attempt,
                    plan=RepairPlanDto.from_domain(a.plan),
                    status=a.status.value,
                    validation_output=a.validation_output,
                    messages=a.messages,
                )
                for a in result.attempts
            ),
            final_analysis=(
                FailureAnalysisDto.from_domain(result.final_analysis)
                if result.final_analysis else None
            ),
            messages=result.messages,
        )


class RepairProposalDto(HttpSchema):
    summary: str
    reasoning: str
    candidate_files: tuple[str, ...]
    suggested_actions: tuple[str, ...]
    confidence: float


class EngineeringReflectionDto(HttpSchema):
    summary: str
    outcome: str
    lessons: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    should_retry: bool
    confidence: float


class AutonomousEngineeringResultDto(HttpSchema):
    proposal: RepairProposalDto
    plan: RepairPlanDto
    repair_result: RepairResultDto
    reflection: EngineeringReflectionDto

    @classmethod
    def from_domain(cls, result) -> AutonomousEngineeringResultDto:
        return cls(
            proposal=RepairProposalDto.model_validate(
                result.proposal.model_dump(mode="python")
            ),
            plan=RepairPlanDto.from_domain(result.plan),
            repair_result=RepairResultDto.from_domain(result.repair_result),
            reflection=EngineeringReflectionDto.model_validate(
                result.reflection.model_dump(mode="json")
            ),
        )


class IntelligentEngineeringExecuteResponse(HttpSchema):
    planning_request: PlanningRequestDto
    planning_result: PlanningResultDto
    engineering_result: AutonomousEngineeringResultDto

    @classmethod
    def from_application(
        cls,
        result: ApplicationIntelligentEngineeringResult,
    ) -> IntelligentEngineeringExecuteResponse:
        return cls(
            planning_request=PlanningRequestDto.from_domain(
                result.planning_request
            ),
            planning_result=PlanningResultDto.from_domain(
                result.planning_result
            ),
            engineering_result=AutonomousEngineeringResultDto.from_domain(
                result.engineering_result
            ),
        )


__all__ = [
    "IntelligentEngineeringExecuteRequest",
    "IntelligentEngineeringExecuteResponse",
]
