from pathlib import Path

from fastapi.testclient import TestClient

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeIdentity, InMemoryAIRuntimeRegistry
from asep.api import create_project_engineering_operational_composition
from asep.application import (
    EngineeringDecomposition,
    EngineeringFileChange,
    ProjectAIRuntimeExecutionRequest,
)
from asep.configuration import ApplicationSettings
from asep.projects import (
    ProjectOperationalPlanOperation,
    ProjectOperationalPlanSource,
    ProjectOperationalPlanStep,
)
from asep.repair import RepairChange, RepairPlan


class NeverRuntime:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="unused")

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("external runtime must not duplicate internal steps")


class CrossLayerDecomposer:
    def decompose(self, context):
        # Deliberately not topologically ordered: execution must honor dependencies.
        steps = (
            ProjectOperationalPlanStep(
                step_id="update-api",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Update Task API serialization.",
                dependencies=("update-persistence",),
                target_hints=("task_api.py",),
            ),
            ProjectOperationalPlanStep(
                step_id="update-model",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Add optional description to Task.",
                target_hints=("task_model.py",),
            ),
            ProjectOperationalPlanStep(
                step_id="update-tests",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Add compatibility and description tests.",
                dependencies=("update-api",),
                target_hints=("tests",),
            ),
            ProjectOperationalPlanStep(
                step_id="update-persistence",
                operation=ProjectOperationalPlanOperation.IMPLEMENT,
                description="Reconstruct legacy and new Task records.",
                dependencies=("update-model",),
                target_hints=("task_repository.py",),
            ),
            ProjectOperationalPlanStep(
                step_id="validate",
                operation=ProjectOperationalPlanOperation.VALIDATE,
                description="Run pytest.",
                dependencies=("update-tests",),
                validation_hints=("compileall", "pytest"),
            ),
        )
        return EngineeringDecomposition(
            steps=steps, source=ProjectOperationalPlanSource.AI
        )


class TaskImplementationProvider:
    def __init__(self) -> None:
        self.order: list[str] = []
        self.contexts = []

    def supports(self, step):
        return True

    def changes_for(self, context):
        self.order.append(context.step.step_id)
        self.contexts.append(context)
        changes = {
            "update-model": (
                EngineeringFileChange(
                    relative_path="task_model.py",
                    content=(
                        "from dataclasses import dataclass\n\n"
                        "@dataclass(frozen=True)\n"
                        "class Task:\n"
                        "    task_id: str\n"
                        "    title: str\n"
                        "    description: str | None = None\n"
                    ),
                ),
            ),
            "update-persistence": (
                EngineeringFileChange(
                    relative_path="task_repository.py",
                    content=(
                        "from task_model import Task\n\n"
                        "def restore(payload):\n"
                        "    return Task(task_id=payload['task_id'], title=payload['title'], "
                        "description=payload.get('description'))\n\n"
                        "def dump(task):\n"
                        "    return {'task_id': task.task_id, 'title': task.title, "
                        "'description': task.description}\n"
                    ),
                ),
            ),
            "update-api": (
                EngineeringFileChange(
                    relative_path="task_api.py",
                    content=(
                        "from task_model import Task\n"
                        "from task_repository import dump\n\n"
                        "def create_task(request):\n"
                        "    task = Task(task_id=request['task_id'], title=request['title'], "
                        "description=request.get('description'))\n"
                        "    return dump(task)\n"
                    ),
                ),
                EngineeringFileChange(
                    relative_path="task_schema.py",
                    content="TASK_FIELDS = ('task_id', 'title', 'description')\n",
                ),
            ),
            "update-tests": (
                EngineeringFileChange(
                    relative_path="tests/test_description.py",
                    content=(
                        "from task_api import create_task\n"
                        "from task_repository import restore\n\n"
                        "def test_old_record_and_request_remain_valid():\n"
                        "    old = {'task_id': '1', 'title': 'Old'}\n"
                        "    assert restore(old).description is None\n"
                        "    response = create_task(old)\n"
                        "    assert response['task_id'] == '1'\n"
                        "    assert response['title'] == 'Old'\n"
                        "    assert response['description'] is None\n\n"
                        "def test_description_is_additive():\n"
                        "    response = create_task({'task_id': '2', 'title': 'New', "
                        "'description': 'Details'})\n"
                        "    assert response == {'task_id': '2', 'title': 'New', "
                        "'description': 'Details'}\n"
                    ),
                ),
            ),
        }
        return changes[context.step.step_id]


def write_initial_fixture(root: Path) -> None:
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "task_model.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass(frozen=True)\n"
        "class Task:\n    task_id: str\n    title: str\n",
        encoding="utf-8",
    )
    (root / "task_repository.py").write_text(
        "from task_model import Task\n\ndef restore(payload):\n"
        "    return Task(task_id=payload['task_id'], title=payload['title'])\n",
        encoding="utf-8",
    )
    (root / "task_api.py").write_text(
        "from task_model import Task\n\ndef create_task(request):\n"
        "    task = Task(task_id=request['task_id'], title=request['title'])\n"
        "    return {'task_id': task.task_id, 'title': task.title}\n",
        encoding="utf-8",
    )
    (root / "tests/test_legacy.py").write_text(
        "from task_api import create_task\n\ndef test_legacy():\n"
        "    assert create_task({'task_id': '1', 'title': 'Old'})['title'] == 'Old'\n",
        encoding="utf-8",
    )


class BrokenImplementationProvider(TaskImplementationProvider):
    def __init__(self, failure: str) -> None:
        super().__init__()
        self.failure = failure

    def changes_for(self, context):
        changes = super().changes_for(context)
        if self.failure == "compile" and context.step.step_id == "update-model":
            return (EngineeringFileChange(
                relative_path="task_model.py",
                content="def broken(:\n",
            ),)
        if self.failure == "test" and context.step.step_id == "update-tests":
            return (EngineeringFileChange(
                relative_path="tests/test_description.py",
                content="def test_failure():\n    assert False\n",
            ),)
        return changes


class FixedRepairPlanner:
    def __init__(self, failure: str, *, remains_broken: bool = False) -> None:
        self.failure = failure
        self.remains_broken = remains_broken
        self.analyses = []

    def plan(self, analysis):
        self.analyses.append(analysis)
        if self.failure == "compile":
            path = "task_model.py"
            content = (
                "def broken(:\n" if self.remains_broken else
                "from dataclasses import dataclass\n\n@dataclass(frozen=True)\n"
                "class Task:\n    task_id: str\n    title: str\n"
                "    description: str | None = None\n"
            )
        else:
            path = "tests/test_description.py"
            content = (
                "def test_failure():\n    assert False\n" if self.remains_broken else
                "from task_api import create_task\n\n"
                "def test_description():\n"
                "    assert create_task({'task_id': '1', 'title': 'T'})['title'] == 'T'\n"
            )
        return RepairPlan(
            analysis=analysis,
            changes=(RepairChange(
                path=path, content=content, reason="Repair observed validator failure."
            ),),
            test_paths=("tests",),
        )


def execute_repair_scenario(tmp_path: Path, failure: str, *, exhausted: bool = False):
    write_initial_fixture(tmp_path)
    registry = InMemoryAIRuntimeRegistry()
    registry.register(NeverRuntime())
    planner = FixedRepairPlanner(failure, remains_broken=exhausted)
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(),
        runtime_registry=registry,
        engineering_decomposer=CrossLayerDecomposer(),
        implementation_provider=BrokenImplementationProvider(failure),
        repair_planner=planner,
    )
    client = TestClient(composition.app)
    project = client.post("/api/v1/projects", json={
        "name": "Repair", "workspace_path": str(tmp_path)
    }).json()
    session = client.post(
        f"/api/v1/projects/{project['project_id']}/sessions",
        json={"title": "Repair"},
    ).json()
    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project["project_id"],
            session_id=session["session_id"],
            runtime_id="codex",
            instruction="Repair the observed validation failure.",
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )
    return result.execution, planner


def test_compile_failure_is_repaired_and_selectively_revalidated(tmp_path: Path) -> None:
    execution, planner = execute_repair_scenario(tmp_path, "compile")

    assert [item.validator for item in execution.validations] == [
        "compileall", "compileall", "pytest"
    ]
    assert execution.failure_analyses[0].category.value == "syntax_or_compile_error"
    assert execution.status.value == "succeeded"
    assert execution.quality_gate.decision.value == "APPROVED"
    assert len(planner.analyses) == 1


def test_pytest_failure_is_repaired_and_selectively_revalidated(tmp_path: Path) -> None:
    execution, planner = execute_repair_scenario(tmp_path, "test")

    assert [item.validator for item in execution.validations] == [
        "compileall", "pytest", "pytest"
    ]
    assert execution.failure_analyses[0].category.value == "assertion_failure"
    assert execution.status.value == "succeeded"
    assert execution.quality_gate.decision.value == "APPROVED"
    assert len(planner.analyses) == 1


def test_repair_exhaustion_never_approves_quality(tmp_path: Path) -> None:
    execution, planner = execute_repair_scenario(
        tmp_path, "test", exhausted=True
    )

    assert execution.status.value == "failed"
    assert execution.error_code == "REPAIR_EXHAUSTED"
    assert execution.quality_gate.decision.value == "BLOCKED"
    assert len(planner.analyses) == 1
def test_cross_layer_task_description_acceptance(tmp_path: Path) -> None:
    write_initial_fixture(tmp_path)
    runtime = NeverRuntime()
    registry = InMemoryAIRuntimeRegistry()
    registry.register(runtime)
    provider = TaskImplementationProvider()
    composition = create_project_engineering_operational_composition(
        ApplicationSettings(),
        runtime_registry=registry,
        engineering_decomposer=CrossLayerDecomposer(),
        implementation_provider=provider,
    )
    client = TestClient(composition.app)
    project = client.post("/api/v1/projects", json={
        "name": "Tasks", "workspace_path": str(tmp_path)
    }).json()
    session = client.post(
        f"/api/v1/projects/{project['project_id']}/sessions",
        json={"title": "Task description"},
    ).json()
    client.post(
        f"/api/v1/projects/{project['project_id']}/sessions/{session['session_id']}/memory",
        json={"kind": "fact", "content": "Preserve Task API compatibility."},
    )

    result = composition.project_engineering_execution.execute(
        ProjectAIRuntimeExecutionRequest(
            project_id=project["project_id"],
            session_id=session["session_id"],
            runtime_id="codex",
            instruction=(
                "Add optional description to Task, update persistence, API and tests."
            ),
            execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        )
    )

    execution = result.execution
    assert runtime.calls == 0
    assert provider.order == [
        "update-model", "update-persistence", "update-api", "update-tests"
    ]
    api_context = next(
        item for item in provider.contexts if item.step.step_id == "update-api"
    )
    assert {item.step_id for item in api_context.dependency_results} == {
        "update-persistence"
    }
    assert api_context.task == execution.instruction
    assert not hasattr(api_context.analysis, "root_path")
    assert len(execution.step_results) == 5
    assert [item.step_id for item in execution.step_results] == [
        "update-model", "update-persistence", "update-api", "update-api",
        "update-tests",
    ]
    assert len(execution.changes) == 5
    assert execution.status.value == "succeeded"
    assert execution.validation_strategy.validators == ("compileall", "pytest")
    assert [item.validator for item in execution.validations] == [
        "compileall", "pytest"
    ]
    assert execution.validations[-1].status.value == "passed"
    assert execution.quality_gate.decision.value == "APPROVED"
    assert execution.quality_gate.run_id == execution.execution_id
    history = client.get(
        f"/api/v1/projects/{project['project_id']}/sessions/{session['session_id']}/executions"
    ).json()["items"]
    memories = client.get(
        f"/api/v1/projects/{project['project_id']}/sessions/{session['session_id']}/memory"
    ).json()["items"]
    assert len(history) == 1
    assert history[0]["execution_id"] == execution.execution_id
    assert len(history[0]["step_results"]) == 5
    assert any(item["source_execution_id"] == execution.execution_id for item in memories)
