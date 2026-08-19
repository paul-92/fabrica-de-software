"""Execução controlada de AI Runtime e histórico de projeto."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import json

from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from enum import StrEnum

from asep._json_values import freeze_json
from asep.access.models import RequestPrincipal
from asep.access.models import LEGACY_ADMIN_USER_ID, LEGACY_ORGANIZATION_ID
from asep.ai_usage import AIUsageOperation, AIUsageService, AIUsageStatus
from asep.ai_quotas import AIQuotaService
from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeRegistry,
    AIRuntimeRequest,
    AIRuntimeResult,
)
from asep.application.project_sessions import ProjectSessionService
from asep.application.session_context import (
    SessionContextBuilder,
    SessionRuntimeContext,
    session_runtime_context_char_count,
)
from asep.application.projects import ProjectService
from asep.application.session_memory import (
    ProjectSessionMemoryService,
    SessionMemoryContext,
    serialize_session_memory_context,
)
from asep.application.workspace_changes import WorkspaceChange, WorkspaceSnapshotter
from asep.dependency_provisioning import ControlledDependencyBrokerRunner, ProjectDependencyProvisioningService, SQLiteDependencyRequestRepository, DependencyRequestDecision, SQLiteProvisioningEvidenceRepository, ProvisioningEvidence, DependencyProvisioningStatus, DependencyPlan, DependencyPlanItem,validate_node_dependency_version
from asep.application.project_engineering_planning import BoundedProjectAnalysis
from asep.projects import (
    ProjectExecution,
    ProjectExecutionRepository,
    ProjectExecutionStatus,
    ProjectOperationalPlan,
    ProjectEngineeringStepResult,
    ProjectOperationalPlanSource,
)


class ProjectOperationalPlanBuilder(Protocol):
    def build(self, execution: ProjectExecution) -> ProjectOperationalPlan: ...


class ProjectEngineeringPlanningCapability(Protocol):
    @property
    def ai_backed(self) -> bool: ...
    def analyze(self, workspace: Path) -> BoundedProjectAnalysis: ...

    def plan_from_analysis(
        self,
        execution: ProjectExecution,
        analysis: BoundedProjectAnalysis,
        session_context: SessionRuntimeContext,
        memory_context: SessionMemoryContext,
    ) -> ProjectOperationalPlan: ...


class ProjectEngineeringInternalExecutionCapability(Protocol):
    def execute_supported_plan(
        self,
        execution: ProjectExecution,
        plan: ProjectOperationalPlan,
        workspace: Path,
        analysis: BoundedProjectAnalysis,
    ) -> tuple[ProjectEngineeringStepResult, ...] | None: ...


class EngineeringPhase(StrEnum):
    PLANNING="planning"; ARCHITECTURE="architecture"; DEVELOPMENT="development"; TESTING="testing"; DELIVERY="delivery"
class EngineeringDependencyRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    package:str; requested_version:str; reason:str; ecosystem:str="node"; registry:str|None=None
    @field_validator("package","requested_version","reason")
    @classmethod
    def valid_text(cls,value:str)->str:
        value=value.strip()
        if not value or any(token in value.casefold() for token in ("http:","https:","git:","file:")): raise ValueError("invalid dependency request")
        return value
    @field_validator("ecosystem")
    @classmethod
    def node_only(cls,value:str)->str:
        if value!="node": raise ValueError("unsupported ecosystem")
        return value
    @field_validator("requested_version")
    @classmethod
    def node_version(cls, value: str) -> str:
        return validate_node_dependency_version(value)
        @classmethod
        def allowed_registry(cls,value:str|None)->str|None:
            if value is not None and value.rstrip("/").casefold()!="https://registry.npmjs.org": raise ValueError("registry not allowed")
            return value
class ProjectAIRuntimeExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str
    session_id: str
    runtime_id: str
    instruction: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    execution_mode: AIRuntimeExecutionMode = AIRuntimeExecutionMode.READ_ONLY
    principal: RequestPrincipal | None = None
    dependency_requests: tuple[EngineeringDependencyRequest,...]=()
    sprint_id:str|None=None
    sprint_name:str|None=None
    engineering_phase:EngineeringPhase|None=None
    @model_validator(mode="after")
    def normalize_dependencies(self):
        unique={}; packages={}
        for item in self.dependency_requests:
            key=(item.ecosystem,item.package,item.requested_version,item.registry or "https://registry.npmjs.org/")
            prior=packages.get((item.ecosystem,item.package))
            if prior is not None and prior!=key: raise ValueError("conflicting dependency requests")
            packages[(item.ecosystem,item.package)]=key; unique[key]=item
        object.__setattr__(self,"dependency_requests",tuple(unique.values()))
        return self

    @field_validator("project_id", "session_id", "runtime_id", "instruction")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("campo obrigatório não pode ser vazio")
        return normalized

    @field_validator("metadata")
    @classmethod
    def metadata_is_json(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return freeze_json(value, location="project runtime metadata")


class ProjectAIRuntimeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    runtime_result: AIRuntimeResult
    changes: tuple[WorkspaceChange, ...] = ()
    execution_mode: AIRuntimeExecutionMode
    execution: ProjectExecution
    bounded_analysis: BoundedProjectAnalysis | None = None


class ProjectAIRuntimeExecutionService:
    def __init__(self, projects: ProjectService, runtimes: AIRuntimeRegistry,
                 sessions: ProjectSessionService, executions: ProjectExecutionRepository,
                 snapshotter: WorkspaceSnapshotter | None = None,
                 dependency_provisioning: ProjectDependencyProvisioningService | None = None,
                 dependency_broker: ControlledDependencyBrokerRunner | None = None,
                 dependency_requests: SQLiteDependencyRequestRepository | None = None,
                 provisioning_evidence: SQLiteProvisioningEvidenceRepository | None = None,
                 context_builder: SessionContextBuilder | None = None, *,
                 memory_service: ProjectSessionMemoryService | None = None,
                 operational_plan_builder: ProjectOperationalPlanBuilder | None = None,
                 engineering_planning: ProjectEngineeringPlanningCapability | None = None,
                 internal_execution: ProjectEngineeringInternalExecutionCapability | None = None,
                 defer_completion: bool = False,
                 clock: Callable[[], datetime] | None = None,
                 id_generator: Callable[[], str] | None = None) -> None:
        self._projects = projects
        self._runtimes = runtimes
        self._sessions = sessions
        self._executions = executions
        self._snapshotter = snapshotter or WorkspaceSnapshotter()
        self._context_builder = context_builder or SessionContextBuilder(executions)
        self._memory = memory_service
        self._operational_plan_builder = operational_plan_builder
        self._engineering_planning = engineering_planning
        self._internal_execution = internal_execution
        self._defer_completion = defer_completion
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_generator = id_generator or (lambda: str(uuid4()))
        self._usage: AIUsageService | None = None
        self._quotas: AIQuotaService | None = None
        self._locks_guard = Lock()
        self._write_locks: dict[str, Lock] = {}
        self._dependency_provisioning = dependency_provisioning
        self._dependency_broker = dependency_broker
        self._dependency_requests = dependency_requests
        self._provisioning_evidence = provisioning_evidence

    def with_usage_metering(self, service: AIUsageService) -> "ProjectAIRuntimeExecutionService":
        self._usage = service
        return self

    def with_quota_guard(self, service: AIQuotaService) -> "ProjectAIRuntimeExecutionService":
        self._quotas = service
        return self

    def _invoke_runtime(self, runtime, runtime_request: AIRuntimeRequest,
                        execution: ProjectExecution,
                        principal: RequestPrincipal | None,
                        operation: AIUsageOperation) -> AIRuntimeResult:
        started = self._clock()
        trusted_user = principal.user_id if principal else LEGACY_ADMIN_USER_ID
        trusted_org = principal.organization_id if principal else LEGACY_ORGANIZATION_ID
        admission = self._quotas.admit(trusted_org, trusted_user) if self._quotas else None
        try:
            is_workspace_write = runtime_request.execution_mode is AIRuntimeExecutionMode.WORKSPACE_WRITE
            has_manifest = runtime_request.workspace is not None and (runtime_request.workspace / "package.json").is_file()
            if is_workspace_write and execution.engineering_phase == "development" and not execution.dependency_requests and runtime_request.workspace is not None and not has_manifest:
                raise RuntimeError("dependency_missing_structured_declaration")
            if is_workspace_write and runtime_request.workspace is not None and execution.dependency_requests:
                for requested in execution.dependency_requests:
                    if self._dependency_requests is None:
                        raise RuntimeError("dependency_approval_required")
                    matches = [item for item in self._dependency_requests.list(execution.project_id)
                               if item.ecosystem == requested.get("ecosystem", "node")
                               and item.package == requested["package"]
                               and item.requested_version == requested["requested_version"]
                               and item.registry == (requested.get("registry") or "https://registry.npmjs.org/")]
                    if not matches:
                        self._dependency_requests.create(project_id=execution.project_id,session_id=execution.session_id,execution_id=execution.execution_id,package=requested["package"],requested_version=requested["requested_version"],reason=requested["reason"],registry=requested.get("registry") or "https://registry.npmjs.org/")
                        raise RuntimeError("dependency_approval_required")
                    if matches[-1].status is not DependencyRequestDecision.APPROVED:
                        raise RuntimeError("dependency_approval_required" if matches[-1].status is DependencyRequestDecision.PENDING else "dependency_policy_blocked")
                if self._dependency_provisioning is None or self._dependency_broker is None:
                    raise RuntimeError("dependency_provisioning_failed")
                if has_manifest:
                    self._dependency_provisioning.provision_node(runtime_request.workspace, self._dependency_broker)
                else:
                    self._dependency_provisioning.provision_requests(
                        runtime_request.workspace, self._dependency_broker,
                        requests=execution.dependency_requests,
                    )
                if self._provisioning_evidence is not None:
                    self._provisioning_evidence.save(ProvisioningEvidence(evidence_id=str(uuid4()),execution_id=execution.execution_id,project_id=execution.project_id,package_manager="node",registry="https://registry.npmjs.org/",status=DependencyProvisioningStatus.PROVISIONED,created_at=started,completed_at=self._clock()))
            evidence = (() if self._provisioning_evidence is None else
                        self._provisioning_evidence.for_execution(execution.project_id, execution.execution_id))
            runtime_request = runtime_request.model_copy(update={"metadata": {
                **dict(runtime_request.metadata), "project_id": execution.project_id,
                "execution_id": execution.execution_id,
                "preparation_id": execution.execution_id if execution.operational_plan is not None else None,
                "sprint_id": execution.sprint_id, "sprint_name": execution.sprint_name,
                "engineering_phase": execution.engineering_phase,
                "dependency_requests": execution.dependency_requests,
                "dependency_provisioning": tuple(item.model_dump(mode="json") for item in evidence),
                "execution_mode": execution.execution_mode.value,
            }})
            result = runtime.execute(runtime_request)
        except Exception as error:
            if self._provisioning_evidence is not None and str(error).startswith("dependency_"):
                try: status=DependencyProvisioningStatus(str(error))
                except ValueError: status=DependencyProvisioningStatus.FAILED
                self._provisioning_evidence.save(ProvisioningEvidence(evidence_id=str(uuid4()),execution_id=execution.execution_id,project_id=execution.project_id,package_manager="node",registry="https://registry.npmjs.org/",status=status,created_at=started,completed_at=self._clock(),error_code=str(error)))
            if self._usage is not None:
                self._usage.record(organization_id=trusted_org, user_id=trusted_user,
                    project_id=execution.project_id, session_id=execution.session_id,
                    execution_id=execution.execution_id, runtime_id=runtime.identity.runtime_id,
                    provider=runtime.identity.runtime_id, model=runtime.identity.model_id,
                    operation=operation, started_at=started, status=AIUsageStatus.FAILED)
            if admission is not None and self._usage is not None: self._quotas.reconcile(admission)
            raise
        if self._usage is not None:
            self._usage.record(organization_id=trusted_org, user_id=trusted_user,
                project_id=execution.project_id, session_id=execution.session_id,
                execution_id=execution.execution_id, runtime_id=result.identity.runtime_id,
                provider=str(result.metadata.get("provider", result.identity.runtime_id)),
                model=result.identity.model_id, operation=operation, started_at=started,
                status=AIUsageStatus.SUCCEEDED, result=result)
        if admission is not None: self._quotas.reconcile(admission)
        return result

    def _record_ai_planning(self, execution: ProjectExecution, principal: RequestPrincipal | None, plan: ProjectOperationalPlan) -> None:
        if self._usage is None or plan.source is not ProjectOperationalPlanSource.AI:
            return
        self._usage.record(
            organization_id=principal.organization_id if principal else LEGACY_ORGANIZATION_ID,
            user_id=principal.user_id if principal else LEGACY_ADMIN_USER_ID,
            project_id=execution.project_id, session_id=execution.session_id,
            execution_id=execution.execution_id, runtime_id="planning-runtime",
            provider="planning-runtime", model=None, operation=AIUsageOperation.PLANNING,
            started_at=self._clock(), status=AIUsageStatus.SUCCEEDED,
        )

    def _plan(self, execution, analysis, session_context, memory_context, principal):
        admission = None
        if self._quotas is not None and getattr(self._engineering_planning, "ai_backed", False):
            admission = self._quotas.admit(execution.organization_id, execution.requested_by_user_id)
        try:
            plan = self._engineering_planning.plan_from_analysis(execution, analysis, session_context, memory_context)
        except Exception:
            if admission is not None:
                self._usage.record(organization_id=execution.organization_id,user_id=execution.requested_by_user_id,
                    project_id=execution.project_id,session_id=execution.session_id,execution_id=execution.execution_id,
                    runtime_id="planning-runtime",provider="planning-runtime",model=None,operation=AIUsageOperation.PLANNING,
                    started_at=self._clock(),status=AIUsageStatus.FAILED)
                self._quotas.reconcile(admission)
            raise
        self._record_ai_planning(execution, principal, plan)
        if admission is not None: self._quotas.reconcile(admission)
        return plan

    def _dependency_plan(self, execution: ProjectExecution, workspace: Path) -> DependencyPlan:
        candidates: list[DependencyPlanItem] = []
        structured_sources=(
            (workspace/".asep"/"dependency-baseline.json","baseline"),
            (workspace/".asep"/"approved-adrs.json","adr"),
            (workspace/".asep"/"sprint-preparation.json","sprint_preparation"),
        )
        for source_path, source in structured_sources:
            if not source_path.is_file():
                continue
            try:
                document=json.loads(source_path.read_text(encoding="utf-8"))
                if document.get("status")!="approved" or not isinstance(document.get("dependencies"),list):
                    continue
                for item in document["dependencies"]:
                    candidates.append(DependencyPlanItem(
                        ecosystem=item.get("ecosystem","node"),package=item["package"],
                        requested_version=item.get("requested_version"),reason=item["reason"],
                        source=source,source_reference=item.get("source_reference") or source_path.name,
                    ))
            except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError) as exc:
                raise RuntimeError("dependency_plan_invalid_structured_source") from exc
        for item in execution.dependency_requests:
            candidates.append(DependencyPlanItem(
                ecosystem=item.get("ecosystem", "node"), package=item["package"],
                requested_version=item["requested_version"], reason=item["reason"],
                source="sprint_preparation", source_reference=execution.sprint_id,
            ))
        manifest = workspace / "package.json"
        if manifest.is_file():
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError("dependency_plan_invalid_workspace_source") from exc
            for field in ("dependencies", "devDependencies", "optionalDependencies"):
                values = payload.get(field, {})
                if not isinstance(values, dict):
                    raise RuntimeError("dependency_plan_invalid_workspace_source")
                for package, version in values.items():
                    candidates.append(DependencyPlanItem(
                        package=package, requested_version=version,
                        reason=f"Declared in package.json {field}",
                        source="workspace_analysis", source_reference=f"package.json#{field}",
                    ))
        unique: dict[tuple[str, str, str | None, str], DependencyPlanItem] = {}
        for item in candidates:
            key=(item.ecosystem,item.package,item.requested_version,"https://registry.npmjs.org/")
            unique[key]=item
        planned=[]
        for item in unique.values():
            if not item.requested_version:
                planned.append(item.model_copy(update={"status":"version_selection_required"}))
                continue
            request_id=None; status="pending"
            if self._dependency_requests is not None:
                matches=[stored for stored in self._dependency_requests.list(execution.project_id)
                         if stored.ecosystem==item.ecosystem and stored.package==item.package
                         and stored.requested_version==item.requested_version]
                stored=(matches[-1] if matches else self._dependency_requests.create(
                    project_id=execution.project_id,session_id=execution.session_id,
                    execution_id=execution.execution_id,package=item.package,
                    requested_version=item.requested_version,reason=item.reason,
                    registry="https://registry.npmjs.org/"))
                request_id=stored.request_id; status=stored.status.value
            planned.append(item.model_copy(update={"dependency_request_id":request_id,"status":status}))
        return DependencyPlan(project_id=execution.project_id,preparation_id=execution.execution_id,
                              sprint_id=execution.sprint_id,engineering_phase=execution.engineering_phase,
                              items=tuple(planned),created_at=self._clock())

    def prepare(
        self, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectExecution:
        """Persist a real plan without crossing the workspace mutation boundary."""
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError("project engineering preparation requires workspace_write mode")
        if self._engineering_planning is None:
            raise RuntimeError("project engineering planning is unavailable")
        project = self._projects.get(request.project_id, request.principal)
        self._sessions.get(request.project_id, request.session_id)
        session_context = self._context_builder.build(request.project_id, request.session_id)
        memory_context = (
            self._memory.context(request.project_id, request.session_id)
            if self._memory is not None else SessionMemoryContext()
        )
        before = self._snapshotter.capture(project.workspace_path)
        execution = ProjectExecution(
            execution_id=self._id_generator(), session_id=request.session_id,
            project_id=request.project_id, runtime_id=request.runtime_id,
            organization_id=project.organization_id,
            requested_by_user_id=request.principal.user_id if request.principal else LEGACY_ADMIN_USER_ID,
            instruction=request.instruction, execution_mode=request.execution_mode,
            dependency_requests=tuple(item.model_dump(mode="json") for item in request.dependency_requests),
            sprint_id=request.sprint_id, sprint_name=request.sprint_name,
            engineering_phase=request.engineering_phase,
            status=ProjectExecutionStatus.PENDING,
            context_entry_count=len(session_context.entries),
            context_truncated=session_context.truncated,
            context_char_count=session_runtime_context_char_count(session_context),
            context_omitted_execution_count=session_context.omitted_execution_count,
            memory_entry_count=len(memory_context.entries),
            memory_char_count=len(serialize_session_memory_context(memory_context)),
            memory_truncated=memory_context.truncated,
            created_at=self._clock(),
        )
        analysis = self._engineering_planning.analyze(project.workspace_path)
        plan = self._plan(execution, analysis, session_context, memory_context, request.principal)
        dependency_plan = self._dependency_plan(execution, project.workspace_path)
        blocker_code = None
        next_action = None
        if request.engineering_phase is EngineeringPhase.DEVELOPMENT and not dependency_plan.items and not (project.workspace_path / "package.json").is_file():
            blocker_code = "dependency_plan_missing_source"
            next_action = "Defina ou aprove a stack técnica na preparação da sprint."
        elif any(item.status == "version_selection_required" for item in dependency_plan.items):
            blocker_code = "version_selection_required"
            next_action = "Selecione uma versão estruturada para cada dependência obrigatória."
        elif any(item.status == "pending" for item in dependency_plan.items):
            blocker_code = "dependency_approval_required"
            next_action = "Revise e aprove as dependências necessárias."
        after = self._snapshotter.capture(project.workspace_path)
        if self._snapshotter.changes(before, after):
            raise RuntimeError("planning mutated the workspace")
        prepared = ProjectExecution.model_validate({
            **execution.model_dump(mode="python"),
            "operational_plan": plan,
            "dependency_plan": dependency_plan.model_dump(mode="json"),
            "dependency_requests": tuple({
                "ecosystem": item.ecosystem, "package": item.package,
                "requested_version": item.requested_version, "reason": item.reason,
                "registry": "https://registry.npmjs.org/",
            } for item in dependency_plan.items if item.requested_version is not None),
            "status": ProjectExecutionStatus.BLOCKED if blocker_code else ProjectExecutionStatus.PENDING,
            "error_code": blocker_code,
            "blocker": "Dependências aguardando revisão" if blocker_code else None,
            "next_action": next_action,
            "completed_at": self._clock() if blocker_code else None,
            "preparation_analysis": analysis.model_dump(mode="json"),
            "preparation_workspace_fingerprint": self._snapshot_fingerprint(after),
            "preparation_context_fingerprint": self._context_fingerprint(
                session_context, memory_context,
            ),
        })
        self._executions.create(prepared)
        return prepared
    def select_dependency_version(
        self,
        project_id: str,
        preparation_id: str,
        package: str,
        version: str,
    ) -> ProjectExecution:
        """Resolve one structured dependency version without executing the runtime."""

        if self._dependency_requests is None:
            raise RuntimeError("dependency approval repository is unavailable")

        normalized_version = validate_node_dependency_version(version)

        prepared = self._executions.get_by_project(project_id, preparation_id)

        if prepared.status not in {
            ProjectExecutionStatus.PENDING,
            ProjectExecutionStatus.BLOCKED,
        }:
            raise ValueError("preparation is not available for dependency version selection")

        if prepared.dependency_plan is None:
            raise ValueError("preparation dependency plan is unavailable")

        dependency_plan = DependencyPlan.model_validate(prepared.dependency_plan)

        matching = [
            item
            for item in dependency_plan.items
            if item.ecosystem == "node" and item.package == package
        ]

        if len(matching) != 1:
            raise ValueError("dependency plan item not found or ambiguous")

        selected = matching[0]

        if selected.status != "version_selection_required":
            raise ValueError("dependency version has already been selected")

        existing = [
            item
            for item in self._dependency_requests.list(project_id)
            if item.execution_id == preparation_id
            and item.ecosystem == selected.ecosystem
            and item.package == selected.package
            and item.requested_version == normalized_version
        ]

        if existing:
            stored = existing[-1]
        else:
            stored = self._dependency_requests.create(
                project_id=prepared.project_id,
                session_id=prepared.session_id,
                execution_id=prepared.execution_id,
                package=selected.package,
                requested_version=normalized_version,
                reason=selected.reason,
                registry="https://registry.npmjs.org/",
            )

        updated_items = tuple(
            item.model_copy(
                update={
                    "requested_version": normalized_version,
                    "status": stored.status.value,
                    "dependency_request_id": stored.request_id,
                }
            )
            if item.package == selected.package
            and item.ecosystem == selected.ecosystem
            else item
            for item in dependency_plan.items
        )

        updated_plan = dependency_plan.model_copy(
            update={
                "items": updated_items,
                "version": dependency_plan.version + 1,
            }
        )

        has_version_selection = any(
            item.status == "version_selection_required"
            for item in updated_items
        )

        if has_version_selection:
            error_code = "version_selection_required"
            next_action = (
                "Selecione uma versão estruturada para cada dependência obrigatória."
            )
        else:
            error_code = "dependency_approval_required"
            next_action = "Revise e aprove as dependências necessárias."

        updated = ProjectExecution.model_validate(
            {
                **prepared.model_dump(mode="python"),
                "dependency_plan": updated_plan.model_dump(mode="json"),
                "dependency_requests": tuple(
                    {
                        "ecosystem": item.ecosystem,
                        "package": item.package,
                        "requested_version": item.requested_version,
                        "reason": item.reason,
                        "registry": "https://registry.npmjs.org/",
                    }
                    for item in updated_items
                    if item.requested_version is not None
                ),
                "status": ProjectExecutionStatus.BLOCKED,
                "error_code": error_code,
                "blocker": "Dependências aguardando revisão",
                "next_action": next_action,
                "completed_at": self._clock(),
            }
        )

        self._executions.update(updated)

        return updated
    def execute_prepared(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectAIRuntimeExecutionResult:
        """Execute exactly one persisted preparation after fail-closed checks."""
        prepared = self._executions.get(preparation_id)
        if prepared.status not in {ProjectExecutionStatus.PENDING, ProjectExecutionStatus.BLOCKED}:
            raise ValueError("preparation is not available for approval")
        if prepared.status is ProjectExecutionStatus.BLOCKED and prepared.error_code != "dependency_approval_required":
            raise ValueError("preparation blocker must be resolved before approval")
        if request.execution_mode is not AIRuntimeExecutionMode.WORKSPACE_WRITE:
            raise ValueError("prepared execution requires workspace_write mode")
        if (
            prepared.project_id != request.project_id
            or prepared.session_id != request.session_id
            or prepared.runtime_id != request.runtime_id
            or prepared.instruction != request.instruction
        ):
            raise ValueError("preparation identity does not match approval")
        if prepared.operational_plan is None or not prepared.preparation_analysis:
            raise ValueError("prepared plan is invalid")
        project = self._projects.get(request.project_id, request.principal)
        self._sessions.get(request.project_id, request.session_id)
        session_context = self._context_builder.build(request.project_id, request.session_id)
        memory_context = (
            self._memory.context(request.project_id, request.session_id)
            if self._memory is not None else SessionMemoryContext()
        )
        current_snapshot = self._snapshotter.capture(project.workspace_path)
        if (
            self._snapshot_fingerprint(current_snapshot)
            != prepared.preparation_workspace_fingerprint
            or self._context_fingerprint(session_context, memory_context)
            != prepared.preparation_context_fingerprint
        ):
            raise ValueError("preparation context is stale")
        analysis = BoundedProjectAnalysis.model_validate(prepared.preparation_analysis)
        execution = ProjectExecution.model_validate({
            **prepared.model_dump(mode="python"), "status": ProjectExecutionStatus.RUNNING,
            "error_code": None, "blocker": None, "next_action": None, "completed_at": None,
        })
        self._executions.update(execution)
        return self._execute_prepared_runtime(
            request, execution, project.workspace_path, analysis,
            session_context, memory_context, current_snapshot,
        )

    def cancel_prepared(
        self, preparation_id: str, request: ProjectAIRuntimeExecutionRequest,
    ) -> ProjectExecution:
        prepared = self._executions.get(preparation_id)
        if prepared.status not in {ProjectExecutionStatus.PENDING, ProjectExecutionStatus.BLOCKED}:
            raise ValueError("preparation is not available for cancellation")
        if (
            prepared.project_id != request.project_id
            or prepared.session_id != request.session_id
            or prepared.runtime_id != request.runtime_id
            or prepared.instruction != request.instruction
        ):
            raise ValueError("preparation identity does not match cancellation")
        cancelled = ProjectExecution.model_validate({
            **prepared.model_dump(mode="python"),
            "status": ProjectExecutionStatus.FAILED,
            "error_code": "PREPARATION_CANCELLED",
            "completed_at": self._clock(),
        })
        self._executions.update(cancelled)
        return cancelled

    def _execute_prepared_runtime(
        self, request, execution, workspace, analysis, session_context,
        memory_context, before,
    ) -> ProjectAIRuntimeExecutionResult:
        try:
            runtime = self._runtimes.get(request.runtime_id)
            execution = ProjectExecution.model_validate({
                **execution.model_dump(mode="python"), "model": runtime.identity.model_id,
            })
            self._executions.update(execution)
            runtime_request = AIRuntimeRequest(
                instruction=request.instruction,
                metadata={**dict(request.metadata),"project_id":request.project_id,"execution_id":execution.execution_id,"preparation_id":execution.execution_id,"sprint_id":execution.sprint_id,"sprint_name":execution.sprint_name,"engineering_phase":execution.engineering_phase,"dependency_requests":execution.dependency_requests,"execution_mode":execution.execution_mode.value},
                context={
                    "project_session": session_context.model_dump(mode="json"),
                    "session_memory": memory_context.model_dump(mode="json"),
                    "project_engineering": {
                        "task": execution.instruction,
                        "project_analysis": analysis.model_dump(mode="json"),
                        "ordered_steps": tuple(
                            step.model_dump(mode="json")
                            for step in execution.operational_plan.steps
                        ),
                        "guidance": (
                            "Follow the validated step order and dependencies.",
                            "Treat target_hints as candidate areas and inspect before assuming files exist.",
                            "Respect the supplied workspace and sandbox boundaries.",
                            "Produce an implementation compatible with the current task.",
                        ),
                    },
                },
                workspace=workspace,
                execution_mode=request.execution_mode,
            )
            lock = self._write_lock(request.project_id)
            if not lock.acquire(blocking=False):
                raise RuntimeError("workspace write já está em execução")
            try:
                step_results = (
                    self._internal_execution.execute_supported_plan(
                        execution, execution.operational_plan, workspace, analysis,
                    ) if self._internal_execution is not None else None
                )
                if step_results is None:
                    result = self._invoke_runtime(runtime, runtime_request, execution, request.principal, AIUsageOperation.IMPLEMENTATION)
                else:
                    execution = ProjectExecution.model_validate({
                        **execution.model_dump(mode="python"), "step_results": step_results,
                    })
                    self._executions.update(execution)
                    if any(not item.succeeded for item in step_results):
                        raise RuntimeError("DeveloperAgent step execution failed")
                    result = AIRuntimeResult(
                        output="Project plan executed by DeveloperAgent.",
                        identity=AIRuntimeIdentity(runtime_id="developer-agent", model_id="controlled-tools"),
                        metadata={"executor": "developer_agent"},
                    )
                after = self._snapshotter.capture(workspace)
                changes = self._snapshotter.changes(before, after)
                return self._persist_success(
                    execution, result, changes,
                    completion_workspace_fingerprint=self._snapshot_fingerprint(after),
                ).model_copy(
                    update={"bounded_analysis": analysis}
                )
            finally:
                lock.release()
        except Exception as error:
            changes = ()
            try:
                changes = self._snapshotter.changes(before, self._snapshotter.capture(workspace))
            except Exception:
                error.add_note("Workspace change evidence could not be completed.")
            if self._executions.get(execution.execution_id).status is ProjectExecutionStatus.RUNNING:
                self._persist_failure(execution, error, changes)
            raise

    @staticmethod
    def _snapshot_fingerprint(snapshot) -> str:
        payload = {
            path: state.model_dump(mode="json")
            for path, state in sorted(snapshot.items())
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _context_fingerprint(session_context, memory_context) -> str:
        payload = {
            "session": session_context.model_dump(mode="json"),
            "memory": memory_context.model_dump(mode="json"),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def execute(self, request: ProjectAIRuntimeExecutionRequest) -> ProjectAIRuntimeExecutionResult:
        project = self._projects.get(request.project_id, request.principal)
        self._sessions.get(request.project_id, request.session_id)
        session_context = self._context_builder.build(
            request.project_id, request.session_id
        )
        memory_context = (
            self._memory.context(request.project_id, request.session_id)
            if self._memory is not None
            else SessionMemoryContext()
        )
        execution = ProjectExecution(
            execution_id=self._id_generator(), session_id=request.session_id,
            project_id=request.project_id, runtime_id=request.runtime_id,
            organization_id=project.organization_id,
            requested_by_user_id=request.principal.user_id if request.principal else LEGACY_ADMIN_USER_ID,
            instruction=request.instruction, execution_mode=request.execution_mode,
            dependency_requests=tuple(item.model_dump(mode="json") for item in request.dependency_requests),
            sprint_id=request.sprint_id, sprint_name=request.sprint_name,
            engineering_phase=request.engineering_phase,
            status=ProjectExecutionStatus.RUNNING,
            context_entry_count=len(session_context.entries),
            context_truncated=session_context.truncated,
            context_char_count=session_runtime_context_char_count(session_context),
            context_omitted_execution_count=session_context.omitted_execution_count,
            memory_entry_count=len(memory_context.entries),
            memory_char_count=len(serialize_session_memory_context(memory_context)),
            memory_truncated=memory_context.truncated,
            created_at=self._clock(),
        )
        self._executions.create(execution)
        bounded_analysis = None
        try:
            if self._engineering_planning is not None:
                bounded_analysis = self._engineering_planning.analyze(
                    project.workspace_path
                )
                plan = self._plan(execution, bounded_analysis, session_context, memory_context, request.principal)
                execution = ProjectExecution.model_validate(
                    {**execution.model_dump(mode="python"), "operational_plan": plan}
                )
            elif self._operational_plan_builder is not None:
                execution = ProjectExecution.model_validate(
                    {
                        **execution.model_dump(mode="python"),
                        "operational_plan": self._operational_plan_builder.build(
                            execution
                        ),
                    }
                )
            if execution.operational_plan is not None:
                self._executions.update(execution)
        except Exception as error:
            self._persist_failure(execution, error)
            raise
        try:
            runtime = self._runtimes.get(request.runtime_id)
        except Exception as error:
            self._persist_failure(execution, error)
            raise
        execution = ProjectExecution.model_validate({
            **execution.model_dump(), "model": runtime.identity.model_id,
        })
        self._executions.update(execution)
        runtime_context = {
            "project_session": session_context.model_dump(mode="json"),
            "session_memory": memory_context.model_dump(mode="json"),
        }
        if execution.operational_plan is not None and bounded_analysis is not None:
            runtime_context["project_engineering"] = {
                "task": execution.instruction,
                "project_analysis": bounded_analysis.model_dump(mode="json"),
                "ordered_steps": tuple(
                    step.model_dump(mode="json")
                    for step in execution.operational_plan.steps
                ),
                "guidance": (
                    "Follow the validated step order and dependencies.",
                    "Treat target_hints as candidate areas and inspect before assuming files exist.",
                    "Respect the supplied workspace and sandbox boundaries.",
                    "Produce an implementation compatible with the current task.",
                ),
            }
        runtime_request = AIRuntimeRequest(
            instruction=request.instruction, metadata={**dict(request.metadata),"project_id":request.project_id,"execution_id":execution.execution_id,"sprint_id":execution.sprint_id,"sprint_name":execution.sprint_name,"engineering_phase":execution.engineering_phase,"dependency_requests":execution.dependency_requests,"execution_mode":execution.execution_mode.value},
            context=runtime_context,
            workspace=project.workspace_path, execution_mode=request.execution_mode,
        )
        if request.execution_mode is AIRuntimeExecutionMode.READ_ONLY:
            try:
                result = self._invoke_runtime(runtime, runtime_request, execution, request.principal, AIUsageOperation.OTHER)
            except Exception as error:
                self._persist_failure(execution, error)
                raise
            return self._persist_success(execution, result, ()).model_copy(
                update={"bounded_analysis": bounded_analysis}
            )

        lock = self._write_lock(request.project_id)
        if not lock.acquire(blocking=False):
            error = RuntimeError("workspace write já está em execução")
            self._persist_failure(execution, error)
            raise error
        try:
            before = self._snapshotter.capture(project.workspace_path)
            try:
                step_results = (
                    self._internal_execution.execute_supported_plan(
                        execution,
                        execution.operational_plan,
                        project.workspace_path,
                        bounded_analysis,
                    )
                    if self._internal_execution is not None
                    and execution.operational_plan is not None
                    else None
                )
                if step_results is None:
                    result = self._invoke_runtime(runtime, runtime_request, execution, request.principal, AIUsageOperation.IMPLEMENTATION)
                else:
                    execution = ProjectExecution.model_validate({
                        **execution.model_dump(mode="python"),
                        "step_results": step_results,
                    })
                    self._executions.update(execution)
                    if any(not item.succeeded for item in step_results):
                        raise RuntimeError("DeveloperAgent step execution failed")
                    result = AIRuntimeResult(
                        output="Project plan executed by DeveloperAgent.",
                        identity=AIRuntimeIdentity(
                            runtime_id="developer-agent",
                            model_id="controlled-tools",
                        ),
                        metadata={"executor": "developer_agent"},
                    )
            except Exception as error:
                changes: tuple[WorkspaceChange, ...] = ()
                try:
                    changes = self._snapshotter.changes(before, self._snapshotter.capture(project.workspace_path))
                    error.workspace_changes = changes  # type: ignore[attr-defined]
                except Exception:
                    error.add_note("Workspace change evidence could not be completed.")
                self._persist_failure(execution, error, changes)
                raise
            after = self._snapshotter.capture(project.workspace_path)
            changes = self._snapshotter.changes(before, after)
            return self._persist_success(
                execution, result, changes,
                completion_workspace_fingerprint=self._snapshot_fingerprint(after),
            ).model_copy(
                update={"bounded_analysis": bounded_analysis}
            )
        except Exception as error:
            if self._executions.get(execution.execution_id).status is ProjectExecutionStatus.RUNNING:
                self._persist_failure(execution, error)
            raise
        finally:
            lock.release()

    def _persist_success(
        self, execution: ProjectExecution, result: AIRuntimeResult,
        changes: tuple[WorkspaceChange, ...], *,
        completion_workspace_fingerprint: str | None = None,
    ) -> ProjectAIRuntimeExecutionResult:
        if self._defer_completion:
            pending_validation = ProjectExecution.model_validate({
                **execution.model_dump(),
                "output": result.output,
                "model": result.identity.model_id,
                "usage": result.usage,
                "changes": changes,
                "completion_workspace_fingerprint": completion_workspace_fingerprint,
            })
            self._executions.update(pending_validation)
            return ProjectAIRuntimeExecutionResult(
                runtime_result=result,
                changes=changes,
                execution_mode=execution.execution_mode,
                execution=pending_validation,
            )
        completed = ProjectExecution.model_validate({**execution.model_dump(), **{
            "status": ProjectExecutionStatus.SUCCEEDED, "output": result.output,
            "model": result.identity.model_id, "usage": result.usage,
            "changes": changes, "completed_at": self._clock(),
            "completion_workspace_fingerprint": completion_workspace_fingerprint,
        }})
        self._executions.update(completed)
        if self._memory is not None:
            self._memory.extract_and_add(completed)
        return ProjectAIRuntimeExecutionResult(runtime_result=result, changes=changes,
                                               execution_mode=execution.execution_mode,
                                               execution=completed)

    def _persist_failure(self, execution: ProjectExecution, error: Exception,
                         changes: tuple[WorkspaceChange, ...] = ()) -> None:
        explicit_code = getattr(error, "code", None)
        if explicit_code is None:
            code = re.sub(
                r"(?<!^)(?=[A-Z])", "_", type(error).__name__
            ).upper()
            if code.startswith("AI_RUNTIME_") and code.endswith("_ERROR"):
                code = code[:-6]
        else:
            code = str(explicit_code).upper()
        failed = ProjectExecution.model_validate({**execution.model_dump(), **{
            "status": ProjectExecutionStatus.FAILED, "changes": changes,
            "error_code": code, "completed_at": self._clock(),
        }})
        self._executions.update(failed)

    def _write_lock(self, project_id: str) -> Lock:
        with self._locks_guard:
            return self._write_locks.setdefault(project_id, Lock())


__all__ = [
    "ProjectAIRuntimeExecutionRequest",
    "ProjectAIRuntimeExecutionResult",
    "ProjectAIRuntimeExecutionService",
    "ProjectEngineeringPlanningCapability",
    "ProjectEngineeringInternalExecutionCapability",
    "ProjectOperationalPlanBuilder",
]
