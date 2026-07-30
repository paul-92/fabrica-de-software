from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from asep.agents import AgentId
from asep.planning import (
    CircularDependencyError,
    ExecutionPlan,
    InMemoryPlanningMetrics,
    InvalidPlanError,
    PlanningContext,
    PlanningEngine,
    PlanningPolicy,
    PlanningRequest,
    PlanningValidator,
    PlanStep,
    SequentialPlanningStrategy,
)
from asep.timeline import (
    InMemoryTimelineRepository,
    TimelineEventType,
    TimelineRecorder,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def request(
    steps=None,
    *,
    capabilities=("analysis", "implementation"),
) -> PlanningRequest:
    return PlanningRequest(
        goal="Entregar incremento",
        context=PlanningContext(
            objective="Entregar incremento",
            workflow={
                "id": "delivery",
                "steps": steps
                if steps is not None
                else [
                    {
                        "id": "analyze",
                        "required_capability": "analysis",
                    },
                    {
                        "id": "implement",
                        "required_capability": "implementation",
                    },
                ],
            },
            available_capabilities=capabilities,
            available_tools={"analysis": "reader"},
        ),
        workflow_execution_id="run-1",
        agent_id=AgentId(value="planner-agent"),
    )


def timeline():
    repository = InMemoryTimelineRepository()
    counter = 0

    def event_id():
        nonlocal counter
        counter += 1
        return f"event-{counter}"

    return repository, TimelineRecorder(
        repository,
        clock=lambda: NOW,
        id_generator=event_id,
    )


def test_models_are_strict_and_immutable() -> None:
    step = PlanStep(
        step_id="one",
        description="First",
        required_capability="analysis",
    )

    with pytest.raises(ValidationError):
        step.step_id = "changed"
    with pytest.raises(ValidationError):
        PlanStep(
            step_id="one",
            description="First",
            required_capability="analysis",
            dependencies=("one",),
        )


def test_strategy_builds_deterministic_sequential_plan_steps() -> None:
    steps = SequentialPlanningStrategy().build_steps(
        request(), PlanningPolicy()
    )

    assert tuple(step.step_id for step in steps) == (
        "analyze",
        "implement",
    )
    assert steps[0].dependencies == ()
    assert steps[1].dependencies == ("analyze",)
    assert steps[0].tool_id.value == "reader"
    assert all(step.agent_id.value == "planner-agent" for step in steps)


def test_strategy_respects_explicit_dependencies_and_policy() -> None:
    planning_request = request(
        [
            {
                "id": "build",
                "required_capability": "implementation",
                "dependencies": [],
            }
        ]
    )
    policy = PlanningPolicy(
        priorities={"build": 7},
        rules={
            "capability_cost": {"implementation": 2.5},
            "capability_duration": {"implementation": 30},
        },
    )

    step = SequentialPlanningStrategy().build_steps(
        planning_request, policy
    )[0]

    assert step.priority == 7
    assert step.estimated_cost == 2.5
    assert step.estimated_duration_seconds == 30


@pytest.mark.parametrize(
    ("steps", "capabilities", "error"),
    [
        ([], ("analysis",), InvalidPlanError),
        (
            [{"id": "one", "required_capability": "missing"}],
            ("analysis",),
            InvalidPlanError,
        ),
        (
            [
                {
                    "id": "one",
                    "required_capability": "analysis",
                    "dependencies": ["unknown"],
                }
            ],
            ("analysis",),
            InvalidPlanError,
        ),
        (
            [
                {
                    "id": "one",
                    "required_capability": "analysis",
                    "dependencies": ["two"],
                },
                {
                    "id": "two",
                    "required_capability": "analysis",
                    "dependencies": ["one"],
                },
            ],
            ("analysis",),
            CircularDependencyError,
        ),
    ],
)
def test_validator_rejects_invalid_plans(
    steps, capabilities, error
) -> None:
    planning_request = request(steps, capabilities=capabilities)
    built = SequentialPlanningStrategy().build_steps(
        planning_request, PlanningPolicy()
    )
    plan = ExecutionPlan(
        plan_id="plan",
        goal=planning_request.goal,
        steps=built,
        estimated_cost=sum(step.estimated_cost for step in built),
        estimated_duration_seconds=0,
        created_at=NOW,
    )

    with pytest.raises(error):
        PlanningValidator().validate_plan(
            plan, planning_request, PlanningPolicy()
        )


def test_engine_creates_deterministic_plan_and_observability() -> None:
    repository, recorder = timeline()
    metrics = InMemoryPlanningMetrics()
    engine = PlanningEngine(
        timeline=recorder,
        metrics=metrics,
        clock=lambda: NOW,
        timer=iter((1.0, 1.2)).__next__,
    )

    result = engine.plan(request())

    assert result.plan.plan_id.startswith("plan-")
    assert result.statistics.total_steps == 2
    assert result.statistics.maximum_depth == 2
    assert metrics.snapshot().plans_created_total == 1
    assert [event.type for event in repository.list_by_run("run-1")] == [
        TimelineEventType.PLANNING_REQUESTED,
        TimelineEventType.PLANNING_STARTED,
        TimelineEventType.PLAN_VALIDATED,
        TimelineEventType.PLANNING_COMPLETED,
    ]


def test_identical_requests_generate_identical_plan_ids() -> None:
    _, first_recorder = timeline()
    _, second_recorder = timeline()

    first = PlanningEngine(
        timeline=first_recorder, clock=lambda: NOW
    ).plan(request())
    second = PlanningEngine(
        timeline=second_recorder, clock=lambda: NOW
    ).plan(request())

    assert first.plan.plan_id == second.plan.plan_id


def test_engine_records_rejected_plan_without_executing_any_step() -> None:
    repository, recorder = timeline()
    metrics = InMemoryPlanningMetrics()
    engine = PlanningEngine(timeline=recorder, metrics=metrics)

    with pytest.raises(InvalidPlanError):
        engine.plan(request([]))

    assert (
        repository.list_by_run("run-1")[-1].type
        is TimelineEventType.PLAN_REJECTED
    )
    assert metrics.snapshot().planning_failures == 1
