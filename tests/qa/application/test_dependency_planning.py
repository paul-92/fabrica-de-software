from datetime import UTC, datetime

from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application.project_ai_runtime import ProjectAIRuntimeExecutionService
from asep.dependency_provisioning import SQLiteDependencyRequestRepository
from asep.projects import ProjectExecution, ProjectExecutionStatus


def execution(dependencies=()):
    return ProjectExecution(
        execution_id="prep-1", session_id="session-1", project_id="project-1",
        runtime_id="codex", instruction="free text must not be inspected",
        execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,
        status=ProjectExecutionStatus.PENDING, dependency_requests=dependencies,
        sprint_id="sprint-1", engineering_phase="development",
        created_at=datetime.now(UTC),
    )


def service(tmp_path):
    result=object.__new__(ProjectAIRuntimeExecutionService)
    result._clock=lambda:datetime.now(UTC)
    result._dependency_requests=SQLiteDependencyRequestRepository(tmp_path/"requests.db")
    return result


def test_plan_uses_structured_sprint_preparation_and_preserves_source(tmp_path):
    item={"ecosystem":"node","package":"typescript","requested_version":"5.9.2","reason":"Approved technical foundation"}
    plan=service(tmp_path)._dependency_plan(execution((item,item)),tmp_path)
    assert len(plan.items)==1
    assert plan.items[0].source=="sprint_preparation"
    assert plan.items[0].source_reference=="sprint-1"
    assert plan.items[0].requested_version=="5.9.2"
    assert plan.items[0].dependency_request_id
    assert plan.items[0].status=="pending"


def test_plan_uses_approved_structured_baseline(tmp_path):
    source=tmp_path/".asep"/"dependency-baseline.json"
    source.parent.mkdir()
    source.write_text('{"status":"approved","dependencies":[{"package":"typescript","requested_version":"5.9.2","reason":"Approved compiler","source_reference":"BASELINE-1"}]}',encoding="utf-8")
    plan=service(tmp_path)._dependency_plan(execution(),tmp_path)
    assert [(item.package,item.requested_version,item.source,item.source_reference) for item in plan.items]==[
        ("typescript","5.9.2","baseline","BASELINE-1")
    ]


def test_missing_version_requires_structured_selection(tmp_path):
    source=tmp_path/".asep"/"dependency-baseline.json"
    source.parent.mkdir()
    source.write_text('{"status":"approved","dependencies":[{"package":"typescript","reason":"Approved compiler"}]}',encoding="utf-8")
    plan=service(tmp_path)._dependency_plan(execution(),tmp_path)
    assert plan.items[0].status=="version_selection_required"
    assert plan.items[0].dependency_request_id is None


def test_plan_uses_deterministic_workspace_and_not_instruction(tmp_path):
    (tmp_path/"package.json").write_text('{"dependencies":{"react":"19.2.0"}}',encoding="utf-8")
    plan=service(tmp_path)._dependency_plan(execution(),tmp_path)
    assert [(item.package,item.requested_version,item.source,item.source_reference) for item in plan.items]==[
        ("react","19.2.0","workspace_analysis","package.json#dependencies")
    ]
    assert all("free text" not in item.reason for item in plan.items)


def test_plan_output_cannot_become_a_dependency_source(tmp_path):
    plan=service(tmp_path)._dependency_plan(execution(),tmp_path)
    assert plan.items==()
