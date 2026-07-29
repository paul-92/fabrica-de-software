"""Modelos validados usados pelos loaders e pelo Orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegistryAgent(StrictModel):
    id: str
    name: str
    version: str
    status: str
    contract: str
    manual: str
    capabilities: list[str] = Field(default_factory=list)
    department: str
    dependencies: list[str] = Field(default_factory=list)
    applicable_project_types: list[str] = Field(default_factory=list)


class RegistryReference(StrictModel):
    id: str
    path: str
    version: str | None = None


class QualityGateReference(StrictModel):
    id: str
    owner: str
    definition: str


class WorkflowRegistryEntry(StrictModel):
    id: str
    name: str
    version: str
    purpose: str
    project_types: list[str]
    stages: list[str]
    agents: list[str]
    conditions: list[str]
    gates: list[str]
    approvals: list[str]
    path: str


class AgentRegistryDocument(StrictModel):
    version: str
    agents: list[RegistryAgent]


class ReferenceRegistryDocument(StrictModel):
    version: str


class ContractRegistryDocument(ReferenceRegistryDocument):
    contracts: list[RegistryReference]


class PlaybookRegistryDocument(ReferenceRegistryDocument):
    playbooks: list[RegistryReference]


class KnowledgeRegistryDocument(ReferenceRegistryDocument):
    knowledge: list[RegistryReference]


class WorkflowRegistryDocument(ReferenceRegistryDocument):
    workflows: list[WorkflowRegistryEntry]


class QualityGateRegistryDocument(ReferenceRegistryDocument):
    quality_gates: list[QualityGateReference]


class WorkflowStage(StrictModel):
    id: str
    mode: Literal["sequential", "parallel", "conditional"]
    workflow: str | None = None
    workflows: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def has_workflow_reference(self) -> "WorkflowStage":
        if self.mode == "parallel" and (self.workflow or not self.workflows):
            raise ValueError("stage parallel deve usar apenas workflows")
        if self.mode != "parallel" and (not self.workflow or self.workflows):
            raise ValueError(
                "stage sequential/conditional deve usar apenas workflow"
            )
        return self


class AgentContract(StrictModel):
    id: str
    name: str
    version: str
    status: str
    department: str
    role: str
    reports_to: str
    mission: str
    capabilities: list[str]
    receives: list[str]
    required_inputs: list[str]
    optional_inputs: list[str]
    produces: list[str]
    required_outputs: list[str]
    consults: list[str]
    quality_gates: list[str]
    approval_rules: list[str]
    next_agents: list[str]
    cannot: list[str]
    human_approval_required: list[str]
    escalation_conditions: list[str]
    success_criteria: list[str]
    failure_conditions: list[str]


class WorkflowDefinition(StrictModel):
    id: str
    name: str
    version: str
    description: str
    applicable_project_types: list[str]
    required_context: list[str]
    stages: list[WorkflowStage]
    stage_dependencies: dict[str, list[str]]
    assigned_agents: dict[str, list[str]]
    stage_quality_gates: dict[str, str] = Field(default_factory=dict)
    conditions: list[str]
    quality_gates: list[str]
    human_approvals: list[str]
    artifacts: list[str]
    failure_handling: dict[str, str]
    completion_criteria: list[str]


class ProjectQualityGate(StrictModel):
    id: str
    status: str
    reason: str
    evaluated_by: str
    evaluated_at: str


class ProjectBlocker(StrictModel):
    id: str
    description: str
    owner: str
    resume_condition: str


class ApprovalRequest(StrictModel):
    id: str
    authority: str
    requested_from: str
    subject: str
    status: str
    requested_at: str


class ApprovalRecord(StrictModel):
    id: str
    authority: str
    approver: str
    decision: str
    subject: str
    date: str


class SprintState(StrictModel):
    id: str
    objective: str
    status: str
    completed_at: str | None = None


class ProjectDefinition(StrictModel):
    id: str
    name: str
    version: str
    status: str
    project_type: str
    workflow_id: str
    data_classification: str
    sponsor: str | None = None
    product_owner: str | None = None
    current_stage: str | None = None
    current_stage_status: str | None = None
    workflow_run_id: str | None = None
    active_agent: str | None = None
    quality_gate: ProjectQualityGate | None = None
    blockers: list[ProjectBlocker] = Field(default_factory=list)
    approval_requests: list[ApprovalRequest] = Field(default_factory=list)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    approved_stack: dict[str, str] = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    sprint: SprintState | None = None
    last_updated: str | None = None


class LoadedProject(BaseModel):
    definition: ProjectDefinition
    path: Path
    readme: str
    markdown_artifacts: tuple[Path, ...]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RegistrySnapshot(BaseModel):
    root: Path
    agents: dict[str, RegistryAgent]
    contracts: dict[str, RegistryReference]
    workflows: dict[str, WorkflowRegistryEntry]
    quality_gates: dict[str, QualityGateReference]
    playbooks: dict[str, RegistryReference]
    knowledge: dict[str, RegistryReference]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PreparationResult(BaseModel):
    project_id: str
    workflow_id: str
    project_status: str
    stage_ids: tuple[str, ...]
    loaded_components: dict[str, int]
    artifact_count: int
    warnings: tuple[str, ...]
    elapsed_seconds: float
