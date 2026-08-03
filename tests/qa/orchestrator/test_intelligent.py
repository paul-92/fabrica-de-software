"""Testes do Intelligent Orchestrator."""

from __future__ import annotations

import json

from datetime import UTC, datetime
from pathlib import Path

import pytest
from asep.agents import (
    AgentExecutionService,
    InMemoryAgentRegistry,
)
from asep.agents.coordination import (
    AgentCoordinator,
    AgentCoordinatorAdapter,
)
from asep.agents.developer import DeveloperAgent
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineRecorder,
)
from asep.tools.builtin import (
    ListDirectoryTool,
    RunTestsTool,
    WriteFileTool,
)
from asep.tools.execution_service import ToolExecutionService
from asep.tools.models import ToolId
from asep.tools.registry import InMemoryToolRegistry
from asep.agents import (
    AgentError,
    AgentExecutionResult,
    AgentExecutionStatus,
    AgentId,
)
from asep.agents.coordination import (
    CoordinationResult,
    CoordinationStatistics,
    CoordinationStatus,
)
from asep.artifacts.manager import ArtifactManager
from asep.errors import ArtifactError
from asep.execution.models import (
    AgentResult,
    AgentResultStatus,
    ArtifactDraft,
   GateDecision, 
)
from asep.orchestrator.intelligent import (
    CoordinationArtifactCollector,
)

NOW = datetime(2026, 8, 3, 8, 0, tzinfo=UTC)


def coordination_result_with_artifact() -> CoordinationResult:
    """Cria um resultado de coordenação com um artefato pendente."""

    agent_result = AgentResult(
        status=AgentResultStatus.COMPLETED,
        agent_id="developer",
        stage_id="implementation",
        run_id="run-intelligent",
        started_at=NOW,
        finished_at=NOW,
        artifacts=[
            ArtifactDraft(
                relative_path="src/example.py",
                type="python",
                content='print("ASEP")\n',
            )
        ],
        messages=["Arquivo produzido."],
    )

    execution_result = AgentExecutionResult(
        execution_id="execution-1",
        agent_id=AgentId(value="developer"),
        status=AgentExecutionStatus.SUCCEEDED,
        output=agent_result.model_dump(mode="json"),
        started_at=NOW,
        completed_at=NOW,
        duration_seconds=0,
        attempts=1,
        metadata={},
        agent_result=agent_result,
    )

    return CoordinationResult(
        plan_id="plan-1",
        run_id="run-intelligent",
        status=CoordinationStatus.COMPLETED,
        assignments=(),
        results=(execution_result,),
        output={},
        statistics=CoordinationStatistics(
            assignments_total=1,
            completed_total=1,
            failed_total=0,
            agents_used=1,
            duration_seconds=0,
            aggregation_duration_seconds=0,
        ),
    )


def test_collector_persists_coordination_artifacts(
    tmp_path: Path,
) -> None:
    collector = CoordinationArtifactCollector()

    references = collector.persist(
        coordination_result_with_artifact(),
        tmp_path,
        run_id="run-intelligent",
        project_id="project-1",
    )

    assert len(references) == 1

    reference = references[0]

    assert reference.run_id == "run-intelligent"
    assert reference.project_id == "project-1"
    assert reference.stage_id == "implementation"
    assert reference.agent_id == "developer"
    assert reference.path == "src/example.py"
    assert reference.type == "python"
    assert reference.checksum

    artifact_path = tmp_path / "src" / "example.py"
    metadata_path = tmp_path / "src" / "example.py.metadata.yaml"

    assert artifact_path.is_file()
    assert metadata_path.is_file()
    assert artifact_path.read_text(encoding="utf-8") == (
        'print("ASEP")\n'
    )


def test_collector_ignores_execution_without_agent_result(
    tmp_path: Path,
) -> None:
    execution_result = AgentExecutionResult(
        
        execution_id="execution-without-result",
        agent_id=AgentId(value="developer"),
        status=AgentExecutionStatus.FAILED,
        output={},
        started_at=NOW,
        completed_at=NOW,
        duration_seconds=0,
        attempts=1,
        error=AgentError(
            code="execution_failed",
            message="Falha esperada no teste.",
),
        metadata={},
        agent_result=None,
    )

    coordination_result = CoordinationResult(
        plan_id="plan-empty",
        run_id="run-empty",
        status=CoordinationStatus.FAILED,
        assignments=(),
        results=(execution_result,),
        output={},
        statistics=CoordinationStatistics(
            assignments_total=1,
            completed_total=0,
            failed_total=1,
            agents_used=1,
            duration_seconds=0,
            aggregation_duration_seconds=0,
        ),
    )

    references = CoordinationArtifactCollector().persist(
        coordination_result,
        tmp_path,
        run_id="run-empty",
        project_id="project-1",
    )

    assert references == ()
    assert tuple(tmp_path.rglob("*")) == ()


def test_collector_preserves_artifact_collision_policy(
    tmp_path: Path,
) -> None:
    collector = CoordinationArtifactCollector(
        artifact_manager=ArtifactManager(),
    )
    coordination_result = coordination_result_with_artifact()

    collector.persist(
        coordination_result,
        tmp_path,
        run_id="run-intelligent",
        project_id="project-1",
    )

    with pytest.raises(ArtifactError):
        collector.persist(
            coordination_result,
            tmp_path,
            run_id="run-intelligent",
            project_id="project-1",
        )

from asep.business_engineering import (
    BusinessDescription,
    ProjectBlueprint,
)
from asep.orchestrator.intelligent import IntelligentOrchestratorService
from asep.orchestrator.models import (
    IntelligentExecutionRequest,
    IntelligentExecutionStatus,
)
from asep.planning import (
    ExecutionPlan,
    PlanningResult,
    PlanningStatistics,
    PlanStep,
)

class SpyPlanningAdapter:
    """Planning Adapter determinístico para testar o orquestrador."""

    def __init__(self) -> None:
        self.received_blueprint: ProjectBlueprint | None = None

    def create_execution_plan(
        self,
        blueprint: ProjectBlueprint,
    ) -> PlanningResult:
        self.received_blueprint = blueprint

        return PlanningResult(
            plan=ExecutionPlan(
                plan_id="plan-intelligent",
                goal=blueprint.description,
                steps=(),
                estimated_cost=0,
                estimated_duration_seconds=0,
                created_at=NOW,
            ),
            warnings=(),
            validation_messages=("Plano validado.",),
            statistics=PlanningStatistics(
                total_steps=0,
                dependency_count=0,
                maximum_depth=0,
                estimated_cost=0,
                estimated_duration_seconds=0,
                memory_entries_considered=0,
            ),
        )


class SpyCoordinatorAdapter:
    """Coordinator Adapter determinístico para testar o orquestrador."""

    def __init__(self) -> None:
        self.received_planning_result: PlanningResult | None = None

    def coordinate(
        self,
        planning_result: PlanningResult,
    ) -> CoordinationResult:
        self.received_planning_result = planning_result

        return CoordinationResult(
            plan_id=planning_result.plan.plan_id,
            run_id="run-intelligent",
            status=CoordinationStatus.COMPLETED,
            assignments=(),
            results=(),
            output={},
            statistics=CoordinationStatistics(
                assignments_total=0,
                completed_total=0,
                failed_total=0,
                agents_used=0,
                duration_seconds=0,
                aggregation_duration_seconds=0,
            ),
        )


class SpyArtifactCollector:
    """Artifact Collector determinístico para testar o orquestrador."""

    def __init__(self) -> None:
        self.received_coordination_result: CoordinationResult | None = None
        self.received_artifacts_root: Path | None = None
        self.received_run_id: str | None = None
        self.received_project_id: str | None = None

    def persist(
        self,
        coordination_result: CoordinationResult,
        artifacts_root: Path,
        *,
        run_id: str,
        project_id: str,
    ) -> tuple:
        self.received_coordination_result = coordination_result
        self.received_artifacts_root = artifacts_root
        self.received_run_id = run_id
        self.received_project_id = project_id

        return ()


def test_intelligent_orchestrator_executes_pipeline(
    tmp_path: Path,
) -> None:
    planning_adapter = SpyPlanningAdapter()
    coordinator_adapter = SpyCoordinatorAdapter()
    artifact_collector = SpyArtifactCollector()

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=planning_adapter,
        coordinator_adapter=coordinator_adapter,
        artifact_collector=artifact_collector,
    )

    request = IntelligentExecutionRequest(
        run_id="run-intelligent",
        project_id="project-1",
        project_name="CRM",
        gate_id="default-quality-gate",
        description=BusinessDescription(
            text="O sistema deve cadastrar clientes."
        ),
        artifacts_root=tmp_path,
        metadata={
            "source": "test",
        },
    )

    result = orchestrator.execute(request)

    assert planning_adapter.received_blueprint is not None
    assert planning_adapter.received_blueprint.project_name == "CRM"

    assert coordinator_adapter.received_planning_result is not None
    assert (
        coordinator_adapter.received_planning_result.plan.plan_id
        == "plan-intelligent"
    )

    assert artifact_collector.received_coordination_result is not None
    assert (
        artifact_collector.received_coordination_result.plan_id
        == "plan-intelligent"
    )
    assert artifact_collector.received_artifacts_root == tmp_path
    assert artifact_collector.received_run_id == "run-intelligent"
    assert artifact_collector.received_project_id == "project-1"

    assert result.run_id == "run-intelligent"
    assert result.project_id == "project-1"
    assert result.status is IntelligentExecutionStatus.COMPLETED

    assert result.blueprint is not None
    assert result.blueprint.project_name == "CRM"

    assert result.planning_result is not None
    assert result.planning_result.plan.plan_id == "plan-intelligent"

    assert result.coordination_result is not None
    assert result.coordination_result.status is CoordinationStatus.COMPLETED

    assert result.artifact_references == ()
    assert result.errors == ()
    assert result.metadata == {
        "source": "test",
    }

def test_intelligent_orchestrator_is_blocked_when_quality_gate_blocks(
    tmp_path: Path,
) -> None:
    planning_adapter = SpyPlanningAdapter()

    class BlockingCoordinatorAdapter:
        def coordinate(
            self,
            planning_result: PlanningResult,
        ) -> CoordinationResult:
            del planning_result
            return coordination_result_with_artifact()

    class EmptyArtifactCollector:
        def persist(
            self,
            coordination_result: CoordinationResult,
            artifacts_root: Path,
            *,
            run_id: str,
            project_id: str,
        ) -> tuple:
            del (
                coordination_result,
                artifacts_root,
                run_id,
                project_id,
            )
            return ()

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=planning_adapter,
        coordinator_adapter=BlockingCoordinatorAdapter(),
        artifact_collector=EmptyArtifactCollector(),
    )

    request = IntelligentExecutionRequest(
        run_id="run-intelligent",
        project_id="project-1",
        project_name="CRM",
        gate_id="default-quality-gate",
        description=BusinessDescription(
            text="O sistema deve cadastrar clientes."
        ),
        artifacts_root=tmp_path,
    )

    result = orchestrator.execute(request)

    assert len(result.gate_results) == 1
    assert result.gate_results[0].decision is GateDecision.BLOCKED
    assert result.status is IntelligentExecutionStatus.BLOCKED

def test_intelligent_orchestrator_maps_failed_coordination_to_failed(
    tmp_path: Path,
) -> None:
    planning_adapter = SpyPlanningAdapter()

    class FailedCoordinatorAdapter:
        def coordinate(
            self,
            planning_result: PlanningResult,
        ) -> CoordinationResult:
            return CoordinationResult(
                plan_id=planning_result.plan.plan_id,
                run_id="run-failed",
                status=CoordinationStatus.FAILED,
                assignments=(),
                results=(),
                output={},
                statistics=CoordinationStatistics(
                    assignments_total=0,
                    completed_total=0,
                    failed_total=1,
                    agents_used=0,
                    duration_seconds=0,
                    aggregation_duration_seconds=0,
                ),
            )

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=planning_adapter,
        coordinator_adapter=FailedCoordinatorAdapter(),
        artifact_collector=SpyArtifactCollector(),
    )

    request = IntelligentExecutionRequest(
        run_id="run-failed",
        project_id="project-1",
        project_name="CRM",
        gate_id="default-quality-gate",
        description=BusinessDescription(
            text="O sistema deve cadastrar clientes."
        ),
        artifacts_root=tmp_path,
    )

    result = orchestrator.execute(request)

    assert result.status is IntelligentExecutionStatus.FAILED


def test_intelligent_orchestrator_maps_partial_coordination_to_partial(
    tmp_path: Path,
) -> None:
    planning_adapter = SpyPlanningAdapter()

    class PartialCoordinatorAdapter:
        def coordinate(
            self,
            planning_result: PlanningResult,
        ) -> CoordinationResult:
            return CoordinationResult(
                plan_id=planning_result.plan.plan_id,
                run_id="run-partial",
                status=CoordinationStatus.PARTIAL,
                assignments=(),
                results=(),
                output={},
                statistics=CoordinationStatistics(
                    assignments_total=1,
                    completed_total=0,
                    failed_total=1,
                    agents_used=1,
                    duration_seconds=0,
                    aggregation_duration_seconds=0,
                ),
            )

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=planning_adapter,
        coordinator_adapter=PartialCoordinatorAdapter(),
        artifact_collector=SpyArtifactCollector(),
    )

    request = IntelligentExecutionRequest(
        run_id="run-partial",
        project_id="project-1",
        project_name="CRM",
        gate_id="default-quality-gate",
        description=BusinessDescription(
            text="O sistema deve cadastrar clientes."
        ),
        artifacts_root=tmp_path,
    )

    result = orchestrator.execute(request)

    assert result.status is IntelligentExecutionStatus.PARTIAL   

def test_intelligent_orchestrator_executes_real_pipeline_end_to_end(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    artifacts_root = tmp_path / "artifacts"

    workspace.mkdir()
    artifacts_root.mkdir()

    (workspace / "README.md").write_text(
        "# Projeto gerado pela ASEP",
        encoding="utf-8",
    )

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(ListDirectoryTool())

    timeline_repository = InMemoryTimelineRepository()
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-e2e-{counter}"

    timeline_recorder = TimelineRecorder(
        timeline_repository,
        clock=lambda: NOW,
        id_generator=event_id,
    )

    tool_executor = ToolExecutionService(
        tool_registry,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    developer = DeveloperAgent(
        tool_executor=tool_executor,
    )

    agent_registry = InMemoryAgentRegistry()
    agent_registry.register(developer)

    runtime = AgentExecutionService(
        agent_registry,
        timeline=timeline_recorder,
        tool_executor=tool_executor,
        clock=lambda: NOW,
    )

    coordinator = AgentCoordinator(
        agent_registry,
        runtime,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    coordinator_adapter = AgentCoordinatorAdapter(
        coordinator=coordinator,
    )

    class ToolPlanningAdapter:
        def create_execution_plan(
            self,
            blueprint: ProjectBlueprint,
        ) -> PlanningResult:
            return PlanningResult(
                plan=ExecutionPlan(
                    plan_id="plan-intelligent-e2e",
                    goal=blueprint.description,
                    steps=(
                        PlanStep(
                            step_id="inspect-workspace",
                            description="Listar arquivos do projeto",
                            required_capability="directory",
                            tool_id=ToolId(
                                value="list-directory",
                            ),
                            agent_id=AgentId(
                                value="developer",
                            ),
                        ),
                    ),
                    estimated_cost=1,
                    estimated_duration_seconds=60,
                    created_at=NOW,
                    metadata={
                        "workspace": str(workspace),
                        "options": {
                            "directory": ".",
                        },
                    },
                ),
                warnings=(),
                validation_messages=(
                    "Plano E2E validado.",
                ),
                statistics=PlanningStatistics(
                    total_steps=1,
                    dependency_count=0,
                    maximum_depth=1,
                    estimated_cost=1,
                    estimated_duration_seconds=60,
                    memory_entries_considered=0,
                ),
            )

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=ToolPlanningAdapter(),
        coordinator_adapter=coordinator_adapter,
    )

    request = IntelligentExecutionRequest(
        run_id="run-intelligent-e2e",
        project_id="project-e2e",
        project_name="Projeto E2E",
        gate_id="quality-gate-e2e",
        description=BusinessDescription(
            text="Inspecionar os arquivos do projeto."
        ),
        artifacts_root=artifacts_root,
    )

    result = orchestrator.execute(request)

    assert result.status is IntelligentExecutionStatus.COMPLETED

    assert result.blueprint is not None
    assert result.blueprint.project_name == "Projeto E2E"

    assert result.planning_result is not None
    assert (
        result.planning_result.plan.plan_id
        == "plan-intelligent-e2e"
    )

    assert result.coordination_result is not None
    assert (
        result.coordination_result.status
        is CoordinationStatus.COMPLETED
    )

    assert len(result.artifact_references) == 1

    artifact_reference = result.artifact_references[0]

    assert artifact_reference.project_id == "project-e2e"
    assert artifact_reference.stage_id == "inspect-workspace"
    assert artifact_reference.agent_id == "developer"
    assert artifact_reference.path == (
        "pipeline/inspect-workspace.json"
    )

    persisted_artifact = (
        artifacts_root
        / "pipeline"
        / "inspect-workspace.json"
    )

    assert persisted_artifact.is_file()

    artifact_content = json.loads(
        persisted_artifact.read_text(encoding="utf-8")
    )

    assert {
        "path": "README.md",
        "type": "file",
    } in artifact_content["entries"]

    assert len(result.gate_results) == 1
    assert (
        result.gate_results[0].decision
        is GateDecision.APPROVED
    )
def test_intelligent_orchestrator_blocks_generated_code_when_tests_fail(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    artifacts_root = tmp_path / "artifacts"

    workspace.mkdir()
    artifacts_root.mkdir()

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(WriteFileTool())
    tool_registry.register(RunTestsTool())

    timeline_repository = InMemoryTimelineRepository()
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-generation-gate-{counter}"

    timeline_recorder = TimelineRecorder(
        timeline_repository,
        clock=lambda: NOW,
        id_generator=event_id,
    )

    tool_executor = ToolExecutionService(
        tool_registry,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    developer = DeveloperAgent(
        tool_executor=tool_executor,
    )

    agent_registry = InMemoryAgentRegistry()
    agent_registry.register(developer)

    runtime = AgentExecutionService(
        agent_registry,
        timeline=timeline_recorder,
        tool_executor=tool_executor,
        clock=lambda: NOW,
    )

    coordinator = AgentCoordinator(
        agent_registry,
        runtime,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    coordinator_adapter = AgentCoordinatorAdapter(
        coordinator=coordinator,
    )

    class FailingGenerationPlanningAdapter:
        def create_execution_plan(
            self,
            blueprint: ProjectBlueprint,
        ) -> PlanningResult:
            return PlanningResult(
                plan=ExecutionPlan(
                    plan_id="plan-generation-gate",
                    goal=blueprint.description,
                    steps=(
                        PlanStep(
                            step_id="create-calculator",
                            description="Criar calculadora",
                            required_capability="write_file",
                            tool_id=ToolId(
                                value="write-file",
                            ),
                            agent_id=AgentId(
                                value="developer",
                            ),
                            metadata={
                                "write_path": "calculator.py",
                                "content": (
                                    "def add(a: int, b: int) -> int:\n"
                                    "    return a - b\n"
                                ),
                                "overwrite": False,
                            },
                        ),
                        PlanStep(
                            step_id="create-calculator-test",
                            description="Criar teste da calculadora",
                            required_capability="write_file",
                            tool_id=ToolId(
                                value="write-file",
                            ),
                            agent_id=AgentId(
                                value="developer",
                            ),
                            metadata={
                                "write_path": (
                                    "tests/test_calculator.py"
                                ),
                                "content": (
                                    "from calculator import add\n\n\n"
                                    "def test_add() -> None:\n"
                                    "    assert add(2, 3) == 5\n"
                                ),
                                "overwrite": False,
                            },
                        ),
                        PlanStep(
                            step_id="run-generated-tests",
                            description="Validar o software gerado",
                            required_capability="test",
                            tool_id=ToolId(
                                value="run-tests",
                            ),
                            agent_id=AgentId(
                                value="developer",
                            ),
                            metadata={
                                "test_paths": [
                                    "tests/test_calculator.py",
                                ],
                            },
                        ),
                    ),
                    estimated_cost=3,
                    estimated_duration_seconds=180,
                    created_at=NOW,
                    metadata={
                        "workspace": str(workspace),
                        "options": {},
                    },
                ),
                warnings=(),
                validation_messages=(
                    "Plano de geração validado.",
                ),
                statistics=PlanningStatistics(
                    total_steps=3,
                    dependency_count=0,
                    maximum_depth=1,
                    estimated_cost=3,
                    estimated_duration_seconds=180,
                    memory_entries_considered=0,
                ),
            )

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=FailingGenerationPlanningAdapter(),
        coordinator_adapter=coordinator_adapter,
    )

    request = IntelligentExecutionRequest(
        run_id="run-generation-gate",
        project_id="project-generation-gate",
        project_name="Calculator",
        gate_id="generated-software-quality-gate",
        description=BusinessDescription(
            text="Criar uma calculadora com testes automatizados."
        ),
        artifacts_root=artifacts_root,
    )

    result = orchestrator.execute(request)

    assert (workspace / "calculator.py").is_file()

    assert (
        workspace
        / "tests"
        / "test_calculator.py"
    ).is_file()

    assert result.coordination_result is not None
    assert len(result.coordination_result.results) == 3

    test_execution = result.coordination_result.results[2]

    assert test_execution.agent_result is not None
    assert (
        test_execution.agent_result.status
        is AgentResultStatus.FAILED
    )

    assert any(
        gate.decision is GateDecision.BLOCKED
        for gate in result.gate_results
    )

    assert (
        result.status
        is IntelligentExecutionStatus.BLOCKED
    )

def test_intelligent_orchestrator_generates_and_validates_software_end_to_end(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    artifacts_root = tmp_path / "artifacts"

    workspace.mkdir()
    artifacts_root.mkdir()

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(WriteFileTool())
    tool_registry.register(RunTestsTool())

    timeline_repository = InMemoryTimelineRepository()
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-software-generation-{counter}"

    timeline_recorder = TimelineRecorder(
        timeline_repository,
        clock=lambda: NOW,
        id_generator=event_id,
    )

    tool_executor = ToolExecutionService(
        tool_registry,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    developer = DeveloperAgent(
        tool_executor=tool_executor,
    )

    agent_registry = InMemoryAgentRegistry()
    agent_registry.register(developer)

    runtime = AgentExecutionService(
        agent_registry,
        timeline=timeline_recorder,
        tool_executor=tool_executor,
        clock=lambda: NOW,
    )

    coordinator = AgentCoordinator(
        agent_registry,
        runtime,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    coordinator_adapter = AgentCoordinatorAdapter(
        coordinator=coordinator,
    )

    class SoftwareGenerationPlanningAdapter:
        def create_execution_plan(
            self,
            blueprint: ProjectBlueprint,
        ) -> PlanningResult:
            return PlanningResult(
                plan=ExecutionPlan(
                    plan_id="plan-software-generation-e2e",
                    goal=blueprint.description,
                    steps=(
                        PlanStep(
                            step_id="create-calculator",
                            description="Criar calculadora",
                            required_capability="write_file",
                            tool_id=ToolId(value="write-file"),
                            agent_id=AgentId(value="developer"),
                            metadata={
                                "write_path": "calculator.py",
                                "content": (
                                    "def add(a: int, b: int) -> int:\n"
                                    "    return a + b\n"
                                ),
                                "overwrite": False,
                            },
                        ),
                        PlanStep(
                            step_id="create-calculator-test",
                            description="Criar teste da calculadora",
                            required_capability="write_file",
                            tool_id=ToolId(value="write-file"),
                            agent_id=AgentId(value="developer"),
                            metadata={
                                "write_path": (
                                    "tests/test_calculator.py"
                                ),
                                "content": (
                                    "from calculator import add\n\n\n"
                                    "def test_add() -> None:\n"
                                    "    assert add(2, 3) == 5\n"
                                ),
                                "overwrite": False,
                            },
                        ),
                        PlanStep(
                            step_id="run-generated-tests",
                            description="Executar testes do software gerado",
                            required_capability="test",
                            tool_id=ToolId(value="run-tests"),
                            agent_id=AgentId(value="developer"),
                            metadata={
                                "test_paths": [
                                    "tests/test_calculator.py",
                                ],
                            },
                        ),
                    ),
                    estimated_cost=3,
                    estimated_duration_seconds=180,
                    created_at=NOW,
                    metadata={
                        "workspace": str(workspace),
                        "options": {},
                    },
                ),
                warnings=(),
                validation_messages=(
                    "Plano de geração validado.",
                ),
                statistics=PlanningStatistics(
                    total_steps=3,
                    dependency_count=0,
                    maximum_depth=1,
                    estimated_cost=3,
                    estimated_duration_seconds=180,
                    memory_entries_considered=0,
                ),
            )

    orchestrator = IntelligentOrchestratorService(
        planning_adapter=SoftwareGenerationPlanningAdapter(),
        coordinator_adapter=coordinator_adapter,
    )

    request = IntelligentExecutionRequest(
        run_id="run-software-generation-e2e",
        project_id="project-software-generation",
        project_name="Calculator",
        gate_id="software-generation-quality-gate",
        description=BusinessDescription(
            text="Criar uma calculadora com testes automatizados."
        ),
        artifacts_root=artifacts_root,
    )

    result = orchestrator.execute(request)

    assert result.status is IntelligentExecutionStatus.COMPLETED

    assert result.blueprint is not None
    assert result.blueprint.project_name == "Calculator"

    assert result.planning_result is not None
    assert (
        result.planning_result.plan.plan_id
        == "plan-software-generation-e2e"
    )

    assert result.coordination_result is not None
    assert (
        result.coordination_result.status
        is CoordinationStatus.COMPLETED
    )

    calculator = workspace / "calculator.py"
    calculator_test = workspace / "tests" / "test_calculator.py"

    assert calculator.is_file()
    assert calculator_test.is_file()

    assert calculator.read_text(encoding="utf-8") == (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    assert len(result.artifact_references) == 3
    assert len(result.gate_results) == 3

    assert all(
        gate.decision is GateDecision.APPROVED
        for gate in result.gate_results
    )    