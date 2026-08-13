from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.ai_runtime import (
    AIRuntimeExecutionMode,
    AIRuntimeIdentity,
    AIRuntimeRequest,
    AIRuntimeResult,
    InMemoryAIRuntimeRegistry,
)
from asep.application import (
    DeterministicProjectOperationalPlanBuilder,
    ProjectAIRuntimeExecutionRequest,
    ProjectAIRuntimeExecutionService,
    ProjectEngineeringExecutionService,
    ProjectQualityGateService,
    ProjectService,
    ProjectSessionMemoryService,
    ProjectSessionService,
)
from asep.errors import ProjectNotFoundError, ProjectSessionNotFoundError
from asep.projects import (
    InMemoryProjectExecutionRepository,
    InMemoryProjectRepository,
    InMemoryProjectSessionRepository,
    InMemorySessionMemoryRepository,
    SessionMemoryKind,
    ProjectOperationalPlan,
    ProjectValidationFailureAnalysis,
    ProjectValidationFailureCategory,
    ProjectValidationResult,
    ProjectValidationStatus,
    WorkspaceProject,
)
from asep.quality.engine import QualityGateEngine
from asep.quality_results import InMemoryQualityGateResultRepository
from asep.repair import (
    FailureAnalysis,
    RepairAttempt,
    RepairChange,
    RepairPlan,
    RepairResult,
    RepairStatus,
)


class ObservingRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="fake-codex")

    def __init__(
        self,
        workspace: Path,
        executions: InMemoryProjectExecutionRepository,
        *,
        failure: Exception | None = None,
    ) -> None:
        self.workspace = workspace
        self.executions = executions
        self.failure = failure
        self.requests: list[AIRuntimeRequest] = []
        self.execution_seen_before_mutation = None

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        current = self.executions.list_by_project("project-1")
        assert len(current) == 1
        self.execution_seen_before_mutation = current[0]
        assert current[0].operational_plan is not None
        assert not (self.workspace / "app.py").exists()
        (self.workspace / "app.py").write_text(
            "HEALTH = {'status': 'ok'}\n", encoding="utf-8"
        )
        (self.workspace / "test_app.py").write_text(
            "def test_health(): assert True\n", encoding="utf-8"
        )
        if self.failure is not None:
            raise self.failure
        return AIRuntimeResult(output="health endpoint added", identity=self.identity)


class ValidationSequence:
    def __init__(
        self,
        statuses: tuple[ProjectValidationStatus, ...],
    ) -> None:
        self.calls: list[tuple[str, int]] = []
        self.strategies: list[tuple[str, ...]] = []
        self._statuses = iter(statuses)

    def validate(self, execution_id, workspace, *, sequence, test_paths=None):
        self.calls.append((execution_id, sequence))
        assert (workspace / "app.py").exists()
        status = next(self._statuses)
        return ProjectValidationResult(
            execution_id=execution_id,
            sequence=sequence,
            command=("python", "-m", "pytest", "."),
            exit_code=0 if status is ProjectValidationStatus.PASSED else 1,
            status=status,
            output=(
                "1 passed"
                if status is ProjectValidationStatus.PASSED
                else "FAILED tests/test_health.py::test_health - AssertionError"
            ),
            completed_at=datetime.now(UTC),
        )

    def validate_plan(self, execution_id, workspace, plan, *, start_sequence):
        hints = tuple(dict.fromkeys(
            hint for step in plan.steps for hint in step.validation_hints
        )) or ("pytest",)
        self.strategies.append(hints)
        return (self.validate(
            execution_id, workspace, sequence=start_sequence
        ),)


class RepairOnce:
    def __init__(self, status: RepairStatus) -> None:
        self.analyze_calls = 0
        self.repair_calls = 0
        self.status = status
        self.analyses: list[FailureAnalysis] = []

    def analyze(self, failure_output: str) -> FailureAnalysis:
        self.analyze_calls += 1
        analysis = FailureAnalysis(
            summary="pytest failed",
            failure_output=failure_output,
            affected_paths=("app.py",),
        )
        self.analyses.append(analysis)
        return analysis

    def repair(self, execution_id, workspace, analysis) -> RepairResult:
        self.repair_calls += 1
        plan = RepairPlan(
            analysis=analysis,
            changes=(RepairChange(
                path="app.py",
                content="HEALTH = {'status': 'ok'}\n",
                reason="repair failing health behavior",
            ),),
            test_paths=(".",),
        )
        return RepairResult(
            status=self.status,
            attempts=(RepairAttempt(
                attempt=1,
                plan=plan,
                status=self.status,
                validation_output="repair validation",
            ),),
            final_analysis=analysis,
        )


class ExceptionalValidationStrategy(ValidationSequence):
    def strategy(self, *args, **kwargs):
        raise RuntimeError("strategy unavailable")


class AnalyzingValidation(ValidationSequence):
    def analyze_failure(self, result):
        return ProjectValidationFailureAnalysis(
            execution_id=result.execution_id,
            validator_id=result.validator,
            category=ProjectValidationFailureCategory.TEST_FAILURE,
            summary="bounded validation failure",
            evidence=result.output,
        )


class ExceptionalRepair(RepairOnce):
    def repair(self, execution_id, workspace, analysis):
        raise LookupError("repair boundary failed")


class ExceptionalQualityGate:
    def evaluate_and_record(self, execution, validation, workspace):
        raise OSError("quality storage failed")


def graph(
    tmp_path: Path,
    *,
    failure: Exception | None = None,
    validation_statuses: tuple[ProjectValidationStatus, ...] = (
        ProjectValidationStatus.PASSED,
    ),
    repair_status: RepairStatus = RepairStatus.EXHAUSTED,
):
    projects = InMemoryProjectRepository()
    projects.save(WorkspaceProject(
        project_id="project-1",
        name="Fixture",
        workspace_path=tmp_path,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))
    executions = InMemoryProjectExecutionRepository()
    project_service = ProjectService(projects)
    sessions_repository = InMemoryProjectSessionRepository()
    sessions = ProjectSessionService(
        project_service,
        sessions_repository,
        executions,
        id_generator=lambda: "session-1",
    )
    sessions.create("project-1", "Health task")
    memory_identifiers = iter(("memory-1", "memory-2", "memory-3"))
    memory = ProjectSessionMemoryService(
        project_service,
        sessions,
        InMemorySessionMemoryRepository(),
        id_generator=lambda: next(memory_identifiers),
    )
    memory.add("project-1", "session-1", SessionMemoryKind.FACT, "Uses FastAPI")
    runtime = ObservingRuntime(tmp_path, executions, failure=failure)
    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)
    runtime_execution = ProjectAIRuntimeExecutionService(
        project_service,
        registry,
        sessions,
        executions,
        memory_service=memory,
        operational_plan_builder=DeterministicProjectOperationalPlanBuilder(),
        defer_completion=True,
        id_generator=lambda: "execution-1",
    )
    validation = ValidationSequence(validation_statuses)
    repair = RepairOnce(repair_status)
    quality_results = InMemoryQualityGateResultRepository()
    return (
        ProjectEngineeringExecutionService(
            runtime_execution,
            project_service,
            executions,
            memory,
            validation,
            repair,
            ProjectQualityGateService(QualityGateEngine(), quality_results),
        ),
        runtime,
        executions,
        memory,
        validation,
        repair,
        quality_results,
    )


def request(**changes) -> ProjectAIRuntimeExecutionRequest:
    values = {
        "project_id": "project-1",
        "session_id": "session-1",
        "runtime_id": "codex",
        "instruction": (
            "Add GET /health returning {'status': 'ok'} and create a test."
        ),
        "execution_mode": AIRuntimeExecutionMode.WORKSPACE_WRITE,
    }
    values.update(changes)
    return ProjectAIRuntimeExecutionRequest(**values)


def test_proof_task_plan_runtime_mutation_diff_and_single_execution(
    tmp_path: Path,
) -> None:
    service, runtime, executions, memory, validation, repair, quality = graph(tmp_path)

    result = service.execute(request())

    assert result.execution.execution_id == "execution-1"
    assert result.execution.operational_plan is not None
    assert result.execution.operational_plan.execution_id == "execution-1"
    assert [step.operation.value for step in result.execution.operational_plan.steps] == [
        "analyze_context",
        "execute_workspace_task",
        "capture_workspace_changes",
    ]
    assert len(executions.list_by_project("project-1")) == 1
    assert runtime.execution_seen_before_mutation.execution_id == "execution-1"
    assert runtime.requests[0].execution_mode is AIRuntimeExecutionMode.WORKSPACE_WRITE
    assert runtime.requests[0].context["project_session"]["session_id"] == "session-1"
    assert runtime.requests[0].context["session_memory"]["entries"][0]["content"] == "Uses FastAPI"
    assert {change.path for change in result.changes} == {"app.py", "test_app.py"}
    assert validation.calls == [("execution-1", 1)]
    assert repair.analyze_calls == repair.repair_calls == 0
    assert quality.list_by_run("execution-1")[0].decision.value == "APPROVED"
    assert all(
        item.source_execution_id == "execution-1"
        for item in memory.list("project-1", "session-1")
        if item.kind is SessionMemoryKind.ARTIFACT
    )


def test_repair_success_keeps_identity_and_approves_quality_gate(
    tmp_path: Path,
) -> None:
    service, _, executions, memory, validation, repair, quality = graph(
        tmp_path,
        validation_statuses=(
            ProjectValidationStatus.FAILED,
            ProjectValidationStatus.PASSED,
        ),
        repair_status=RepairStatus.SUCCEEDED,
    )

    result = service.execute(request())

    assert result.execution.status.value == "succeeded"
    assert [item.execution_id for item in result.execution.validations] == [
        "execution-1",
        "execution-1",
    ]
    assert [item.sequence for item in result.execution.validations] == [1, 2]
    assert result.execution.validations[0].command == (
        "python", "-m", "pytest", "."
    )
    assert result.execution.validations[0].exit_code == 1
    assert "FAILED tests/test_health.py" in result.execution.validations[0].output
    assert result.execution.repair.execution_id == "execution-1"
    assert result.execution.repair.result.status is RepairStatus.SUCCEEDED
    assert repair.analyze_calls == repair.repair_calls == 1
    assert validation.calls == [("execution-1", 1), ("execution-1", 2)]
    assert validation.strategies == [("pytest",), ("pytest",)]
    assert result.execution.quality_gate.run_id == "execution-1"
    assert result.execution.quality_gate.decision.value == "APPROVED"
    assert quality.list_by_run("execution-1") == (result.execution.quality_gate,)
    assert executions.get("execution-1") == result.execution
    assert any(
        item.source_execution_id == "execution-1"
        for item in memory.list("project-1", "session-1")
    )


def test_repair_exhausted_fails_execution_and_blocks_quality_gate(
    tmp_path: Path,
) -> None:
    service, _, executions, memory, validation, repair, quality = graph(
        tmp_path,
        validation_statuses=(
            ProjectValidationStatus.FAILED,
            ProjectValidationStatus.FAILED,
        ),
        repair_status=RepairStatus.EXHAUSTED,
    )

    result = service.execute(request())

    assert result.execution.status.value == "failed"
    assert result.execution.error_code == "REPAIR_EXHAUSTED"
    assert len(result.execution.validations) == 2
    assert result.execution.validations[-1].status is ProjectValidationStatus.FAILED
    assert result.execution.repair.result.status is RepairStatus.EXHAUSTED
    assert len(result.execution.repair.result.attempts) == 1
    assert repair.analyze_calls == repair.repair_calls == 1
    assert validation.calls == [("execution-1", 1), ("execution-1", 2)]
    assert result.execution.quality_gate.run_id == "execution-1"
    assert result.execution.quality_gate.decision.value == "BLOCKED"
    assert quality.list_by_run("execution-1")[0].decision.value == "BLOCKED"
    assert executions.get("execution-1") == result.execution
    assert all(
        item.source_execution_id is None
        for item in memory.list("project-1", "session-1")
    )


def test_project_and_session_are_validated_before_runtime(tmp_path: Path) -> None:
    service, runtime, executions, _, _, _, _ = graph(tmp_path)

    with pytest.raises(ProjectNotFoundError):
        service.execute(request(project_id="missing"))
    with pytest.raises(ProjectSessionNotFoundError):
        service.execute(request(session_id="missing"))

    assert runtime.requests == []
    assert executions.list_by_project("project-1") == ()


def test_read_only_mode_cannot_start_engineering_execution(tmp_path: Path) -> None:
    service, runtime, executions, _, _, _, _ = graph(tmp_path)

    with pytest.raises(ValueError, match="workspace_write"):
        service.execute(request(execution_mode=AIRuntimeExecutionMode.READ_ONLY))

    assert runtime.requests == []
    assert executions.list_by_project("project-1") == ()


def test_runtime_failure_keeps_one_failed_execution_and_change_evidence(
    tmp_path: Path,
) -> None:
    failure = RuntimeError("runtime failed")
    service, _, executions, _, validation, _, quality = graph(
        tmp_path, failure=failure
    )

    with pytest.raises(RuntimeError) as caught:
        service.execute(request())

    assert caught.value is failure
    persisted = executions.get("execution-1")
    assert persisted.status.value == "failed"
    assert persisted.error_code == "RUNTIME_ERROR"
    assert persisted.operational_plan.execution_id == persisted.execution_id
    assert {change.path for change in persisted.changes} == {"app.py", "test_app.py"}
    assert len(executions.list_by_project("project-1")) == 1
    assert validation.calls == []
    assert quality.list_by_run("execution-1") == ()


def test_operational_plan_is_strict_frozen_and_owned_by_execution(
    tmp_path: Path,
) -> None:
    service, _, _, _, _, _, _ = graph(tmp_path)
    plan = service.execute(request()).execution.operational_plan
    assert plan is not None
    with pytest.raises((FrozenInstanceError, TypeError, ValueError)):
        plan.execution_id = "other"  # type: ignore[misc]
    with pytest.raises(ValueError):
        ProjectOperationalPlan.model_validate({
            **plan.model_dump(mode="python"),
            "unsupported": True,
        })


def assert_unexpected_failure_is_terminal(
    executions: InMemoryProjectExecutionRepository,
    memory: ProjectSessionMemoryService,
    *,
    error_code: str,
):
    persisted = executions.get("execution-1")
    assert persisted.execution_id == "execution-1"
    assert persisted.status.value == "failed"
    assert persisted.completed_at is not None
    assert persisted.error_code == error_code
    assert len(persisted.error_code) <= 100
    assert persisted.operational_plan is not None
    assert persisted.operational_plan.execution_id == persisted.execution_id
    assert {item.path for item in persisted.changes} == {"app.py", "test_app.py"}
    assert all(
        item.source_execution_id is None
        for item in memory.list("project-1", "session-1")
    )
    return persisted


def test_validation_strategy_exception_persists_terminal_failure(
    tmp_path: Path,
) -> None:
    service, _, executions, memory, _, _, quality = graph(tmp_path)
    service._validation = ExceptionalValidationStrategy(())
    failure = RuntimeError("strategy unavailable")

    with pytest.raises(RuntimeError) as caught:
        service.execute(request())

    assert str(caught.value) == str(failure)
    persisted = assert_unexpected_failure_is_terminal(
        executions, memory, error_code="RUNTIME_ERROR",
    )
    assert persisted.validation_strategy is None
    assert persisted.validations == ()
    assert quality.list_by_run("execution-1") == ()


def test_repair_exception_preserves_failed_validation_and_identity(
    tmp_path: Path,
) -> None:
    service, _, executions, memory, _, _, quality = graph(
        tmp_path, validation_statuses=(ProjectValidationStatus.FAILED,),
    )
    service._validation = AnalyzingValidation((ProjectValidationStatus.FAILED,))
    service._repair = ExceptionalRepair(RepairStatus.EXHAUSTED)

    with pytest.raises(LookupError, match="repair boundary failed"):
        service.execute(request())

    persisted = assert_unexpected_failure_is_terminal(
        executions, memory, error_code="LOOKUP_ERROR",
    )
    assert len(persisted.validations) == 1
    assert persisted.validations[0].execution_id == persisted.execution_id
    assert persisted.validations[0].status is ProjectValidationStatus.FAILED
    assert len(persisted.failure_analyses) == 1
    assert persisted.failure_analyses[0].execution_id == persisted.execution_id
    assert persisted.repair is None
    assert quality.list_by_run("execution-1") == ()


def test_quality_gate_exception_preserves_validation_and_does_not_add_memory(
    tmp_path: Path,
) -> None:
    service, _, executions, memory, _, _, _ = graph(tmp_path)
    service._quality = ExceptionalQualityGate()

    with pytest.raises(OSError, match="quality storage failed"):
        service.execute(request())

    persisted = assert_unexpected_failure_is_terminal(
        executions, memory, error_code="OSERROR",
    )
    assert len(persisted.validations) == 1
    assert persisted.validations[0].status is ProjectValidationStatus.PASSED
    assert persisted.quality_gate is None
