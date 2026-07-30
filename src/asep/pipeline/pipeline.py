"""Pipeline integrado para execução de um objetivo ASEP."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from asep._json_values import json_value
from asep.agents.contracts import AgentId
from asep.agents.coordination.contracts import Coordinator
from asep.agents.coordination.models import (
    CoordinationContext,
    CoordinationResult,
    CoordinationStatus,
)
from asep.memory.filtering import MemoryFilter
from asep.memory.models import (
    MemoryCategory,
    MemoryEntry,
    MemoryId,
    MemoryImportance,
)
from asep.memory.service import MemoryService
from asep.pipeline.exceptions import PipelineExecutionError
from asep.pipeline.models import (
    GoalExecutionContext,
    GoalRequest,
    GoalResult,
    GoalStatus,
)
from asep.pipeline.validator import PipelineComponents, PipelineValidator
from asep.planning.contracts import Planner
from asep.planning.models import (
    ExecutionPlan,
    PlanningContext,
    PlanningRequest,
)
from asep.timeline.repository import TimelineRepository
from asep.tools.registry import ToolRegistry
from asep.workflow.models import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowStatus,
)
from asep.workflow.orchestrator import WorkflowOrchestrator

Clock = Callable[[], datetime]
Timer = Callable[[], float]
RunIdGenerator = Callable[[], str]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PipelineMetricSources:
    planning: object
    coordination: object
    recovery: object
    agents: object
    tools: object
    memory: object

    def snapshot(self) -> dict[str, Any]:
        return {
            name: asdict(source.snapshot())
            for name, source in (
                ("planning", self.planning),
                ("coordination", self.coordination),
                ("recovery", self.recovery),
                ("agents", self.agents),
                ("tools", self.tools),
                ("memory", self.memory),
            )
        }


class _GoalPipelineStep:
    id = "execute-goal"

    def __init__(self, pipeline: ExecutionPipeline, request: GoalRequest):
        self._pipeline = pipeline
        self._request = request

    def execute(self, context: WorkflowContext) -> None:
        self._pipeline._execute_goal(self._request, context)


class ExecutionPipeline:
    def __init__(
        self,
        *,
        workflow: WorkflowOrchestrator,
        planner: Planner,
        coordinator: Coordinator,
        tools: ToolRegistry,
        memory: MemoryService,
        timeline: TimelineRepository,
        metrics: PipelineMetricSources,
        validator: PipelineValidator | None = None,
        clock: Clock | None = None,
        timer: Timer | None = None,
        run_id_generator: RunIdGenerator | None = None,
    ) -> None:
        self._workflow = workflow
        self._planner = planner
        self._coordinator = coordinator
        self._tools = tools
        self._memory = memory
        self._timeline = timeline
        self._metrics = metrics
        self._validator = validator or PipelineValidator()
        self._clock = clock or _utc_now
        self._timer = timer or perf_counter
        self._run_id_generator = run_id_generator or (
            lambda: str(uuid4())
        )
        self._last_context: GoalExecutionContext | None = None
        self._validator.validate_components(
            PipelineComponents(
                workflow=workflow,
                planner=planner,
                coordinator=coordinator,
                tools=tools,
                memory=memory,
                timeline=timeline,
                metrics=metrics,
            )
        )

    @property
    def last_context(self) -> GoalExecutionContext | None:
        return self._last_context

    def execute(self, request: GoalRequest) -> GoalResult:
        self._validator.validate_request(request)
        started = self._timer()
        run_id = self._run_id_generator()
        workflow = WorkflowDefinition(
            id="asep-goal-execution",
            name="ASEP End-to-End Goal Execution",
            description=request.goal,
            steps=(_GoalPipelineStep(self, request),),
            metadata={"pipeline": "1.0"},
        )
        workflow_result = self._workflow.execute(
            workflow, WorkflowContext(run_id=run_id)
        )
        values = workflow_result.context.values
        coordination_raw = values.get("coordination")
        coordination = (
            CoordinationResult.model_validate(coordination_raw)
            if coordination_raw is not None
            else None
        )
        duration = max(0.0, self._timer() - started)
        timeline = self._timeline.list_by_run(run_id)
        metrics = {
            **self._metrics.snapshot(),
            "pipeline": {
                "execution_time": duration,
                "workflow": workflow.id,
            },
            "workflow": dict(workflow_result.metrics),
        }
        if (
            workflow_result.status is WorkflowStatus.COMPLETED
            and coordination is not None
        ):
            status = GoalStatus.SUCCEEDED
            summary = str(values["summary"])
            steps = tuple(values["steps"])
            artifacts = tuple(values["artifacts"])
        else:
            status = (
                GoalStatus.CANCELLED
                if workflow_result.status is WorkflowStatus.CANCELLED
                else GoalStatus.FAILED
            )
            summary = (
                workflow_result.error.message
                if workflow_result.error is not None
                else "Execução do objetivo não foi concluída."
            )
            steps = ()
            artifacts = ()
        _, safe_metadata, _ = MemoryFilter().sanitize(
            "", request.metadata
        )
        self._last_context = GoalExecutionContext(
            run_id=run_id,
            workflow={
                "id": workflow.id,
                "status": workflow_result.status.value,
            },
            execution_plan=(
                None
                if values.get("execution_plan") is None
                else ExecutionPlan.model_validate(
                    values["execution_plan"]
                )
            ),
            memory=tuple(
                MemoryEntry.model_validate(item)
                for item in values.get("memory", ())
            ),
            assignments=tuple(
                coordination.assignments if coordination is not None else ()
            ),
            timeline=timeline,
            metrics=json_value(metrics),
            workspace=request.workspace.resolve(),
        )
        return GoalResult(
            run_id=run_id,
            status=status,
            summary=summary,
            steps=steps,
            timeline=timeline,
            metrics=json_value(metrics),
            execution_time=duration,
            artifacts=artifacts,
            metadata={
                **safe_metadata,
                "workflow_id": workflow.id,
            },
        )

    def _execute_goal(
        self, request: GoalRequest, workflow_context: WorkflowContext
    ) -> None:
        run_id = workflow_context.run_id
        agent_id = AgentId(value="developer")
        self._save_memory(
            run_id,
            agent_id,
            MemoryCategory.TASK,
            request.goal,
            "goal",
            MemoryImportance.HIGH,
        )
        planning_result = self._planner.plan(
            PlanningRequest(
                goal=request.goal,
                context=PlanningContext(
                    objective=request.goal,
                    workflow=self._planning_workflow(request.options),
                    metadata=request.metadata,
                    available_capabilities=tuple(
                        sorted(
                            {
                                capability.id
                                for tool in self._tools.list()
                                for capability in tool.metadata.capabilities
                            }
                        )
                    ),
                ),
                workflow_execution_id=run_id,
                agent_id=agent_id,
                metadata=request.metadata,
            )
        )
        self._save_memory(
            run_id,
            agent_id,
            MemoryCategory.PLAN,
            f"Plano {planning_result.plan.plan_id} com "
            f"{len(planning_result.plan.steps)} etapas.",
            "plan",
            MemoryImportance.HIGH,
        )
        memories = self._memory.find_by_agent(agent_id)
        coordination = self._coordinator.coordinate(
            CoordinationContext(
                execution_plan=planning_result.plan,
                workflow={"id": "asep-goal-execution"},
                memory=memories,
                metadata={
                    **request.metadata,
                    "run_id": run_id,
                    "workspace": str(request.workspace.resolve()),
                    "options": dict(request.options),
                },
            )
        )
        if coordination.status is not CoordinationStatus.COMPLETED:
            raise PipelineExecutionError(
                f"Coordenação terminou em {coordination.status.value}."
            )
        summary = self._summary(request.goal, coordination.results)
        self._save_memory(
            run_id,
            agent_id,
            MemoryCategory.RESULT,
            summary,
            "result",
            MemoryImportance.HIGH,
        )
        self._save_memory(
            run_id,
            agent_id,
            MemoryCategory.OBSERVATION,
            "Pipeline executado deterministicamente com Tools registradas.",
            "observation",
        )
        artifacts = tuple(
            artifact.model_dump(mode="json")
            for result in coordination.results
            if result.agent_result is not None
            for artifact in result.agent_result.artifacts
        )
        workflow_context.values.update(
            {
                "execution_plan": planning_result.plan.model_dump(
                    mode="json"
                ),
                "coordination": coordination.model_dump(mode="json"),
                "memory": tuple(
                    item.model_dump(mode="json")
                    for item in self._memory.find_by_agent(agent_id)
                ),
                "summary": summary,
                "steps": tuple(
                    {
                        "assignment": assignment.model_dump(mode="json"),
                        "duration_seconds": result.duration_seconds,
                        "status": result.status.value,
                    }
                    for assignment, result in zip(
                        coordination.assignments,
                        coordination.results,
                        strict=True,
                    )
                ),
                "artifacts": artifacts,
                "result": summary,
            }
        )

    @staticmethod
    def _planning_workflow(
        options: Mapping[str, Any],
    ) -> dict[str, Any]:
        del options
        return {
            "id": "architecture-analysis",
            "steps": [
                {
                    "id": "list-directories",
                    "description": "Listar o diretório do projeto.",
                    "required_capability": "directory",
                },
                {
                    "id": "find-source-files",
                    "description": "Encontrar arquivos-fonte Python.",
                    "required_capability": "search",
                },
                {
                    "id": "read-project-readme",
                    "description": "Ler o README principal.",
                    "required_capability": "read_file",
                },
                {
                    "id": "read-architecture",
                    "description": "Ler a documentação arquitetural.",
                    "required_capability": "documentation",
                },
            ],
        }

    def _save_memory(
        self,
        run_id: str,
        agent_id: AgentId,
        category: MemoryCategory,
        content: str,
        suffix: str,
        importance: MemoryImportance = MemoryImportance.NORMAL,
    ) -> MemoryEntry:
        now = self._clock()
        return self._memory.save(
            MemoryEntry(
                memory_id=MemoryId(
                    value=str(
                        uuid5(
                            NAMESPACE_URL,
                            f"asep:{run_id}:{suffix}",
                        )
                    )
                ),
                agent_id=agent_id,
                execution_id=run_id,
                workflow_execution_id=run_id,
                category=category,
                importance=importance,
                content=content,
                metadata={"source": "execution-pipeline"},
                created_at=now,
                updated_at=now,
            )
        )

    @staticmethod
    def _summary(goal: str, results) -> str:
        tools = [
            result.agent_result.metadata.get("tool_id")
            for result in results
            if result.agent_result is not None
        ]
        return (
            f"Objetivo concluído: {goal} "
            f"Foram executadas {len(results)} etapas com as Tools "
            f"{', '.join(str(item) for item in tools)}."
        )


__all__ = ["ExecutionPipeline", "PipelineMetricSources"]
