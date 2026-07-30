from datetime import UTC, datetime
from pathlib import Path

from asep.agents import (
    AgentCapability,
    AgentExecutionRequest,
    AgentExecutionService,
    AgentId,
    AgentMetadata,
    AgentRequest,
    AgentResult,
    AgentStatus,
    AgentStepAdapter,
    InMemoryAgentRegistry,
)
from asep.configuration import ApplicationSettings, StorageBackend
from asep.execution.models import AgentContext
from asep.memory import (
    ContextBuilder,
    InMemoryMemoryStore,
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryService,
    SQLiteMemoryStore,
)
from asep.repositories import RepositoryFactory
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder
from asep.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecutor,
    WorkflowStatus,
    WorkflowValidator,
)

NOW = datetime(2026, 7, 30, 16, 0, tzinfo=UTC)


class MemoryAwareAgent:
    metadata = AgentMetadata(
        id=AgentId(value="memory-agent"),
        name="Memory Agent",
        description="Captures runtime input.",
        version="1",
        capabilities=(AgentCapability(id="review"),),
    )

    def __init__(self) -> None:
        self.request: AgentRequest | None = None

    def execute(
        self, request: AgentRequest, context: AgentContext
    ) -> AgentResult:
        self.request = request
        return AgentResult(
            status=AgentStatus.COMPLETED,
            agent_id=context.agent_id,
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=context.started_at,
            finished_at=context.started_at,
        )


def runtime_with_memory(agent: MemoryAwareAgent):
    agent_registry = InMemoryAgentRegistry()
    agent_registry.register(agent)
    timeline = TimelineRecorder(InMemoryTimelineRepository())
    memory_service = MemoryService(
        InMemoryMemoryStore(), timeline=timeline
    )
    memory_service.save(
        MemoryEntry(
            memory_id=MemoryId(value="memory-1"),
            agent_id=agent.metadata.id,
            execution_id="previous",
            workflow_execution_id="run-1",
            category=MemoryCategory.DECISION,
            content="Reuse validated architecture",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    builder = ContextBuilder(memory_service, timeline=timeline)
    runtime = AgentExecutionService(
        agent_registry,
        timeline=timeline,
        context_provider=builder,
    )
    request = AgentExecutionRequest(
        execution_id="execution-2",
        agent_id=agent.metadata.id,
        capability=AgentCapability(id="review"),
        workflow_execution_id="run-1",
        workflow_step_id="review",
        context={"objective": "Review", "scope_received": "Sprint"},
    )
    return runtime, request


def test_agent_runtime_injects_reusable_memory_context() -> None:
    agent = MemoryAwareAgent()
    runtime, request = runtime_with_memory(agent)

    result = runtime.execute(request)

    assert result.status.value == "succeeded"
    memory_context = agent.request.inputs["memory_context"]
    assert memory_context["memories"][0]["content"] == (
        "Reuse validated architecture"
    )


def test_workflow_uses_runtime_with_context_builder() -> None:
    agent = MemoryAwareAgent()
    runtime, request = runtime_with_memory(agent)
    workflow = WorkflowDefinition(
        id="memory-workflow",
        steps=(
            AgentStepAdapter(
                step_id="review",
                runtime=runtime,
                execution_request=request,
            ),
        ),
    )

    result = WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(
            TimelineRecorder(InMemoryTimelineRepository())
        ),
    ).execute(workflow, WorkflowContext(run_id="run-1"))

    assert result.status is WorkflowStatus.COMPLETED
    assert "memory_context" in agent.request.inputs


def test_repository_factory_selects_memory_store(tmp_path: Path) -> None:
    memory_bundle = RepositoryFactory(
        ApplicationSettings(storage_backend=StorageBackend.MEMORY)
    ).create()
    sqlite_bundle = RepositoryFactory(
        ApplicationSettings(
            storage_backend=StorageBackend.SQLITE,
            sqlite_database=tmp_path / "asep.db",
        )
    ).create()
    file_bundle = RepositoryFactory(
        ApplicationSettings(
            storage_backend=StorageBackend.FILE,
            storage_directory=tmp_path / "file",
        )
    ).create()

    assert isinstance(memory_bundle.memory_store, InMemoryMemoryStore)
    assert isinstance(file_bundle.memory_store, InMemoryMemoryStore)
    assert isinstance(sqlite_bundle.memory_store, SQLiteMemoryStore)

