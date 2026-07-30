from dataclasses import dataclass
from datetime import UTC, datetime

from asep.agents import (
    AgentCapability,
    AgentExecutionRequest,
    AgentExecutionService,
    AgentId,
    AgentMetadata,
    AgentStatus,
    InMemoryAgentRegistry,
)
from asep.execution.models import AgentResult
from asep.planning import (
    PlanningContext,
    PlanningEngine,
    PlanningRequest,
)
from asep.timeline import InMemoryTimelineRepository, TimelineRecorder
from asep.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecutor,
    WorkflowValidator,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def recorder():
    counter = 0

    def event_id():
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    return TimelineRecorder(
        InMemoryTimelineRepository(),
        clock=lambda: NOW,
        id_generator=event_id,
    )


@dataclass
class Step:
    id: str

    def execute(self, context: WorkflowContext) -> None:
        assert context.values["execution_plan"]["steps"][0]["step_id"] == self.id
        context.values["executed"] = True


def test_workflow_requests_plan_before_executing_steps() -> None:
    planning_engine = PlanningEngine(
        timeline=recorder(), clock=lambda: NOW
    )
    engine = WorkflowEngine(
        WorkflowValidator(),
        WorkflowExecutor(recorder(), clock=lambda: NOW),
        planner=planning_engine,
    )
    context = WorkflowContext(run_id="run-workflow")

    result = engine.execute(
        WorkflowDefinition(id="workflow", steps=(Step("first"),)),
        context,
    )

    assert result.context.values["executed"] is True
    assert result.context.values["execution_plan"]["goal"] == "workflow"


class CapturingAgent:
    def __init__(self) -> None:
        self.request = None
        self.metadata = AgentMetadata(
            id=AgentId(value="worker"),
            name="Worker",
            description="Agent for integration testing.",
            version="1.0",
            capabilities=(AgentCapability(id="analysis"),),
        )

    def execute(self, request, context):
        self.request = request
        return AgentResult(
            status=AgentStatus.COMPLETED,
            agent_id="worker",
            stage_id=context.stage_id,
            run_id=context.run_id,
            started_at=NOW,
            finished_at=NOW,
        )


def test_agent_runtime_receives_plan_without_executing_tools() -> None:
    agent = CapturingAgent()
    registry = InMemoryAgentRegistry()
    registry.register(agent)
    runtime = AgentExecutionService(
        registry,
        timeline=recorder(),
        planner=PlanningEngine(timeline=recorder(), clock=lambda: NOW),
        clock=lambda: NOW,
    )
    request = AgentExecutionRequest(
        execution_id="execution-1",
        agent_id=AgentId(value="worker"),
        capability=AgentCapability(id="analysis"),
        input={"source": "brief"},
        context={"objective": "Analyze brief"},
        workflow_execution_id="run-agent",
        workflow_step_id="analyze",
    )

    result = runtime.execute(request)

    assert result.status.value == "succeeded"
    assert agent.request.inputs["execution_plan"]["steps"][0]["step_id"] == (
        "analyze"
    )
