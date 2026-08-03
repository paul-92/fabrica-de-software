"""Testes end-to-end da coordenação, runtime e Tools."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from asep.agents import (
    AgentCapability,
    AgentExecutionService,
    AgentId,
    AgentMetadata,
    AgentStatus,
    InMemoryAgentRegistry,
)
from asep.agents.coordination import (
    AgentCoordinator,
    AgentCoordinatorAdapter,
    AssignmentStatus,
    CoordinationStatus,
)
from asep.agents.developer import DeveloperAgent
from asep.execution.models import AgentContext, AgentResult
from asep.planning import (
    ExecutionPlan,
    PlanningResult,
    PlanningStatistics,
    PlanStep,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
    TimelineRecorder,
)
from asep.tools.builtin import (
    ListDirectoryTool,
    ReadFileTool,
    RunTestsTool,
    WriteFileTool,
)
from asep.tools.execution_service import ToolExecutionService
from asep.tools.models import ToolId
from asep.tools.registry import InMemoryToolRegistry

NOW = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)


class ImplementationAgent:
    """Agente determinístico executado pelo runtime real."""

    def __init__(self) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value="developer"),
            name="Developer",
            description="Agente determinístico de implementação.",
            version="1.0",
            capabilities=(
                AgentCapability(id="implement_requirement"),
            ),
        )
        self.contexts: list[AgentContext] = []

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(
        self,
        request,
        context: AgentContext,
    ) -> AgentResult:
        del request
        self.contexts.append(context)

        return AgentResult(
            status=AgentStatus.COMPLETED,
            agent_id=self.metadata.id.value,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=NOW,
            messages=["Requisito implementado."],
        )


def timeline() -> tuple[
    InMemoryTimelineRepository,
    TimelineRecorder,
]:
    repository = InMemoryTimelineRepository()
    counter = 0

    def event_id() -> str:
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    recorder = TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=event_id,
    )

    return repository, recorder


def planning_result() -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-runtime-e2e",
        goal="Implementar cadastro de clientes.",
        steps=(
            PlanStep(
                step_id="REQ-001",
                description="Implementar cadastro de clientes",
                required_capability="implement_requirement",
            ),
        ),
        estimated_cost=1,
        estimated_duration_seconds=60,
        created_at=NOW,
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=("Plano validado.",),
        statistics=PlanningStatistics(
            total_steps=1,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=1,
            estimated_duration_seconds=60,
            memory_entries_considered=0,
        ),
    )


def tool_planning_result(workspace: Path) -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-tool-e2e",
        goal="Inspecionar o workspace do projeto.",
        steps=(
            PlanStep(
                step_id="inspect-workspace",
                description="Listar os arquivos do projeto",
                required_capability="directory",
                tool_id=ToolId(value="list-directory"),
                agent_id=AgentId(value="developer"),
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
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=("Plano validado.",),
        statistics=PlanningStatistics(
            total_steps=1,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=1,
            estimated_duration_seconds=60,
            memory_entries_considered=0,
        ),
    )


def test_coordination_executes_agent_through_real_runtime() -> None:
    agent = ImplementationAgent()
    registry = InMemoryAgentRegistry()
    registry.register(agent)

    timeline_repository, timeline_recorder = timeline()

    runtime = AgentExecutionService(
        registry,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    coordinator = AgentCoordinator(
        registry,
        runtime,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    adapter = AgentCoordinatorAdapter(
        coordinator=coordinator,
    )

    result = adapter.coordinate(planning_result())

    assert result.status is CoordinationStatus.COMPLETED
    assert result.plan_id == "plan-runtime-e2e"
    assert len(result.assignments) == 1
    assert result.assignments[0].status is AssignmentStatus.COMPLETED
    assert result.assignments[0].agent_id == AgentId(value="developer")

    assert len(result.results) == 1
    assert result.results[0].agent_result is not None
    assert result.results[0].agent_result.messages == [
        "Requisito implementado."
    ]

    assert len(agent.contexts) == 1
    assert agent.contexts[0].run_id == "plan-runtime-e2e"
    assert agent.contexts[0].stage_id == "REQ-001"
    assert agent.contexts[0].objective == (
        "Implementar cadastro de clientes"
    )

    event_types = tuple(
        event.type
        for event in timeline_repository.list_by_run(
            "plan-runtime-e2e"
        )
    )

    assert TimelineEventType.COORDINATION_STARTED in event_types
    assert TimelineEventType.AGENT_EXECUTION_REQUESTED in event_types
    assert TimelineEventType.AGENT_EXECUTION_SUCCEEDED in event_types
    assert TimelineEventType.COORDINATION_COMPLETED in event_types


def test_developer_agent_executes_real_tool_and_creates_artifact(
    tmp_path: Path,
) -> None:
    project_file = tmp_path / "README.md"
    project_file.write_text("# Projeto do cliente", encoding="utf-8")

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(ListDirectoryTool())

    timeline_repository, timeline_recorder = timeline()

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

    result = AgentCoordinatorAdapter(
        coordinator=coordinator,
    ).coordinate(
        tool_planning_result(tmp_path)
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert len(result.assignments) == 1
    assert result.assignments[0].status is AssignmentStatus.COMPLETED

    execution_result = result.results[0]

    assert execution_result.agent_result is not None
    assert len(execution_result.agent_result.artifacts) == 1

    artifact = execution_result.agent_result.artifacts[0]

    assert artifact.relative_path == (
        "pipeline/inspect-workspace.json"
    )
    assert artifact.type == "json"

    artifact_content = json.loads(artifact.content)

    assert {
        "path": "README.md",
        "type": "file",
    } in artifact_content["entries"]

    event_types = tuple(
        event.type
        for event in timeline_repository.list_by_run(
            "plan-tool-e2e"
        )
    )

    assert TimelineEventType.TOOL_REQUESTED in event_types
    assert TimelineEventType.TOOL_VALIDATED in event_types
    assert TimelineEventType.TOOL_SUCCEEDED in event_types
    assert TimelineEventType.AGENT_EXECUTION_SUCCEEDED in event_types
    assert TimelineEventType.COORDINATION_COMPLETED in event_types

def write_file_planning_result(
    workspace: Path,
) -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-write-file-e2e",
        goal="Criar arquivo Python no projeto.",
        steps=(
            PlanStep(
                step_id="create-main",
                description="Criar arquivo principal da aplicação",
                required_capability="write_file",
                tool_id=ToolId(value="write-file"),
                agent_id=AgentId(value="developer"),
            ),
        ),
        estimated_cost=1,
        estimated_duration_seconds=60,
        created_at=NOW,
        metadata={
            "workspace": str(workspace),
            "options": {
                "write_path": "src/main.py",
                "content": (
                    'def main():\n'
                    '    return "ASEP"\n'
                ),
                "overwrite": False,
            },
        },
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=("Plano de escrita validado.",),
        statistics=PlanningStatistics(
            total_steps=1,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=1,
            estimated_duration_seconds=60,
            memory_entries_considered=0,
        ),
    )


def test_developer_agent_writes_real_file_to_workspace(
    tmp_path: Path,
) -> None:
    tool_registry = InMemoryToolRegistry()
    tool_registry.register(WriteFileTool())

    _, timeline_recorder = timeline()

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

    result = AgentCoordinatorAdapter(
        coordinator=coordinator,
    ).coordinate(
        write_file_planning_result(tmp_path)
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert len(result.assignments) == 1
    assert result.assignments[0].status is AssignmentStatus.COMPLETED

    created_file = tmp_path / "src" / "main.py"

    assert created_file.is_file()
    assert created_file.read_text(encoding="utf-8") == (
        'def main():\n'
        '    return "ASEP"\n'
    )

    execution_result = result.results[0]

    assert execution_result.agent_result is not None
    assert execution_result.agent_result.metadata == {
        "tool_id": "write-file",
        "capability": "write_file",
    }    

def multi_file_planning_result(
    workspace: Path,
) -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-multi-file-e2e",
        goal="Criar estrutura inicial do projeto.",
        steps=(
            PlanStep(
                step_id="create-main",
                description="Criar arquivo principal",
                required_capability="write_file",
                tool_id=ToolId(value="write-file"),
                agent_id=AgentId(value="developer"),
                metadata={
                    "write_path": "src/main.py",
                    "content": (
                        'from services.customer_service import '
                        'CustomerService\n\n'
                        'def main():\n'
                        '    return CustomerService()\n'
                    ),
                    "overwrite": False,
                },
            ),
            PlanStep(
                step_id="create-customer-model",
                description="Criar modelo de cliente",
                required_capability="write_file",
                tool_id=ToolId(value="write-file"),
                agent_id=AgentId(value="developer"),
                metadata={
                    "write_path": "src/domain/customer.py",
                    "content": (
                        "class Customer:\n"
                        "    pass\n"
                    ),
                    "overwrite": False,
                },
            ),
            PlanStep(
                step_id="create-customer-service",
                description="Criar serviço de cliente",
                required_capability="write_file",
                tool_id=ToolId(value="write-file"),
                agent_id=AgentId(value="developer"),
                metadata={
                    "write_path": "src/services/customer_service.py",
                    "content": (
                        "class CustomerService:\n"
                        "    pass\n"
                    ),
                    "overwrite": False,
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
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=(
            "Plano de múltiplos arquivos validado.",
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

def test_developer_agent_creates_multiple_project_files(
    tmp_path: Path,
) -> None:
    tool_registry = InMemoryToolRegistry()
    tool_registry.register(WriteFileTool())

    _, timeline_recorder = timeline()

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

    result = AgentCoordinatorAdapter(
        coordinator=coordinator,
    ).coordinate(
        multi_file_planning_result(tmp_path)
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert len(result.assignments) == 3
    assert all(
        assignment.status is AssignmentStatus.COMPLETED
        for assignment in result.assignments
    )

    expected_files = {
        "src/main.py": (
            'from services.customer_service import '
            'CustomerService\n\n'
            'def main():\n'
            '    return CustomerService()\n'
        ),
        "src/domain/customer.py": (
            "class Customer:\n"
            "    pass\n"
        ),
        "src/services/customer_service.py": (
            "class CustomerService:\n"
            "    pass\n"
        ),
    }

    for relative_path, expected_content in expected_files.items():
        target = tmp_path / relative_path

        assert target.is_file()
        assert target.read_text(
            encoding="utf-8"
        ) == expected_content

    assert len(result.results) == 3

    for execution_result in result.results:
        assert execution_result.agent_result is not None
        assert execution_result.agent_result.metadata[
            "tool_id"
        ] == "write-file"
        assert execution_result.agent_result.metadata[
            "capability"
        ] == "write_file"    

def modify_file_planning_result(
    workspace: Path,
) -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-modify-file-e2e",
        goal="Ler e atualizar arquivo existente.",
        steps=(
            PlanStep(
                step_id="read-existing-main",
                description="Ler arquivo principal existente",
                required_capability="read_file",
                tool_id=ToolId(value="read-file"),
                agent_id=AgentId(value="developer"),
                metadata={
                    "read_path": "src/main.py",
                },
            ),
            PlanStep(
                step_id="update-main",
                description="Atualizar arquivo principal",
                required_capability="write_file",
                tool_id=ToolId(value="write-file"),
                agent_id=AgentId(value="developer"),
                metadata={
                    "write_path": "src/main.py",
                    "content": (
                        'def main():\n'
                        '    return "ASEP v2"\n'
                    ),
                    "overwrite": True,
                },
            ),
        ),
        estimated_cost=2,
        estimated_duration_seconds=120,
        created_at=NOW,
        metadata={
            "workspace": str(workspace),
            "options": {},
        },
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=(
            "Plano de alteração de arquivo validado.",
        ),
        statistics=PlanningStatistics(
            total_steps=2,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=2,
            estimated_duration_seconds=120,
            memory_entries_considered=0,
        ),
    )        

def test_developer_agent_reads_and_updates_existing_file(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    target = source_dir / "main.py"
    target.write_text(
        'def main():\n'
        '    return "ASEP v1"\n',
        encoding="utf-8",
    )

    tool_registry = InMemoryToolRegistry()
    tool_registry.register(ReadFileTool())
    tool_registry.register(WriteFileTool())

    _, timeline_recorder = timeline()

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

    result = AgentCoordinatorAdapter(
        coordinator=coordinator,
    ).coordinate(
        modify_file_planning_result(tmp_path)
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert len(result.assignments) == 2

    assert all(
        assignment.status is AssignmentStatus.COMPLETED
        for assignment in result.assignments
    )

    assert target.read_text(encoding="utf-8") == (
        'def main():\n'
        '    return "ASEP v2"\n'
    )

    assert len(result.results) == 2

    read_result = result.results[0].agent_result
    write_result = result.results[1].agent_result

    assert read_result is not None
    assert write_result is not None

    assert read_result.metadata == {
        "tool_id": "read-file",
        "capability": "read_file",
    }

    assert write_result.metadata == {
        "tool_id": "write-file",
        "capability": "write_file",
    }    

class PreviousResultsProbeAgent:
    def __init__(self) -> None:
        self._metadata = AgentMetadata(
            id=AgentId(value="probe"),
            name="Previous Results Probe",
            description="Inspeciona previous_results recebidos pelo runtime.",
            version="1.0",
            capabilities=(
                AgentCapability(id="probe"),
            ),
        )
        self.requests = []

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    def execute(
        self,
        request,
        context: AgentContext,
    ) -> AgentResult:
        self.requests.append(request)

        previous_results = request.inputs.get(
            "previous_results",
            [],
        )

        return AgentResult(
            status=AgentStatus.COMPLETED,
            agent_id=self.metadata.id.value,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=NOW,
            messages=[
                f"previous_results={len(previous_results)}"
            ],
        )    

def previous_results_planning_result() -> PlanningResult:
    return PlanningResult(
        plan=ExecutionPlan(
            plan_id="plan-previous-results-e2e",
            goal="Validar propagação de resultados anteriores.",
            steps=(
                PlanStep(
                    step_id="probe-first",
                    description="Executar primeiro probe",
                    required_capability="probe",
                    agent_id=AgentId(value="probe"),
                ),
                PlanStep(
                    step_id="probe-second",
                    description="Executar segundo probe",
                    required_capability="probe",
                    agent_id=AgentId(value="probe"),
                ),
            ),
            estimated_cost=2,
            estimated_duration_seconds=2,
            created_at=NOW,
        ),
        warnings=(),
        validation_messages=("Plano validado.",),
        statistics=PlanningStatistics(
            total_steps=2,
            dependency_count=0,
            maximum_depth=1,
            estimated_cost=2,
            estimated_duration_seconds=2,
            memory_entries_considered=0,
        ),
    )        

def test_coordinator_propagates_previous_results_between_steps() -> None:
    agent = PreviousResultsProbeAgent()

    registry = InMemoryAgentRegistry()
    registry.register(agent)

    _, timeline_recorder = timeline()

    runtime = AgentExecutionService(
        registry,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    coordinator = AgentCoordinator(
        registry,
        runtime,
        timeline=timeline_recorder,
        clock=lambda: NOW,
    )

    result = AgentCoordinatorAdapter(
        coordinator=coordinator,
    ).coordinate(
        previous_results_planning_result()
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert len(agent.requests) == 2

    first_request = agent.requests[0]
    second_request = agent.requests[1]

    assert first_request.inputs["previous_results"] == []

    assert len(
        second_request.inputs["previous_results"]
    ) == 1

    previous = second_request.inputs[
        "previous_results"
    ][0]

    assert previous["status"] == "succeeded"
    assert previous["agent_id"]["value"] == "probe"   

def write_and_test_planning_result(
    workspace: Path,
) -> PlanningResult:
    plan = ExecutionPlan(
        plan_id="plan-write-and-test-e2e",
        goal="Criar código e validar com pytest.",
        steps=(
            PlanStep(
                step_id="create-calculator",
                description="Criar módulo calculadora",
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
                    "write_path": "tests/test_calculator.py",
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
                description="Executar testes do código gerado",
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
    )

    return PlanningResult(
        plan=plan,
        warnings=(),
        validation_messages=(
            "Plano de geração e testes validado.",
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

def test_developer_agent_generates_code_and_runs_tests(
    tmp_path: Path,
) -> None:
    tool_registry = InMemoryToolRegistry()
    tool_registry.register(WriteFileTool())
    tool_registry.register(RunTestsTool())

    _, timeline_recorder = timeline()

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

    result = AgentCoordinatorAdapter(
        coordinator=coordinator,
    ).coordinate(
        write_and_test_planning_result(tmp_path)
    )

    assert result.status is CoordinationStatus.COMPLETED
    assert len(result.assignments) == 3

    assert all(
        assignment.status is AssignmentStatus.COMPLETED
        for assignment in result.assignments
    )

    calculator = tmp_path / "calculator.py"
    calculator_test = (
        tmp_path
        / "tests"
        / "test_calculator.py"
    )

    assert calculator.is_file()
    assert calculator_test.is_file()

    assert len(result.results) == 3

    test_execution = result.results[2]

    assert test_execution.agent_result is not None
    assert test_execution.agent_result.metadata == {
        "tool_id": "run-tests",
        "capability": "test",
    }      