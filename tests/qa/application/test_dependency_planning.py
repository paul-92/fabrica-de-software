from datetime import UTC, datetime, timedelta
import sqlite3

import pytest

from asep.ai_runtime import AIRuntimeExecutionMode
from asep.application.project_ai_runtime import ProjectAIRuntimeExecutionService
from asep.dependency_provisioning import (
    DependencyRequestDecision,
    SQLiteDependencyRequestRepository,
)
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


class ReversedListDependencyRequestRepository(SQLiteDependencyRequestRepository):
    def list(self,project_id):
        return tuple(reversed(super().list(project_id)))


def service(tmp_path, repository_type=SQLiteDependencyRequestRepository):
    result=object.__new__(ProjectAIRuntimeExecutionService)
    result._clock=lambda:datetime.now(UTC)
    result._dependency_requests=repository_type(tmp_path/"requests.db")
    return result


def baseline_without_version(tmp_path, *, version=None):
    source=tmp_path/".asep"/"dependency-baseline.json"
    source.parent.mkdir(exist_ok=True)
    requested_version = "" if version is None else f',"requested_version":"{version}"'
    source.write_text(
        '{"status":"approved","dependencies":[{"package":"typescript",'
        f'"reason":"Approved compiler"{requested_version}}}' + "]}",
        encoding="utf-8",
    )


def historical_request(repo, *, project_id="project-1", version="5.9.2",
                       decision=DependencyRequestDecision.APPROVED,
                       registry="https://registry.npmjs.org/", created_at=None):
    item=repo.create(
        project_id=project_id,session_id="old-session",execution_id="old-prep",
        package="typescript",requested_version=version,reason="Approved compiler",
        registry=registry,
    )
    if created_at is not None:
        item=item.model_copy(update={"created_at":created_at})
        with sqlite3.connect(repo.database) as database:
            database.execute(
                "UPDATE dependency_request SET payload=? WHERE request_id=?",
                (item.model_dump_json(),item.request_id),
            )
    if decision is DependencyRequestDecision.PENDING:
        return item
    return repo.resolve(project_id,item.request_id,decision,"approver",1)


def test_plan_uses_structured_sprint_preparation_and_preserves_source(tmp_path):
    item={"ecosystem":"node","package":"typescript","requested_version":"5.9.2","reason":"Approved technical foundation"}
    plan=service(tmp_path)._dependency_plan(execution((item,item)),tmp_path)
    assert len(plan.items)==1
    assert plan.items[0].source=="sprint_preparation"
    assert plan.items[0].source_reference=="sprint-1"
    assert plan.items[0].requested_version=="5.9.2"
    assert plan.items[0].dependency_request_id
    assert plan.items[0].status=="pending"


def test_structured_request_preserves_explicit_dev_dependency_group(tmp_path):
    item={
        "ecosystem":"node", "package":"@types/node",
        "requested_version":"24.13.3", "reason":"Node types",
        "manifest_group":"devDependencies",
    }

    planned=service(tmp_path)._dependency_plan(execution((item,)),tmp_path)

    assert len(planned.items)==1
    assert planned.items[0].package=="@types/node"
    assert planned.items[0].requested_version=="24.13.3"
    assert planned.items[0].manifest_group=="devDependencies"


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


def test_missing_baseline_version_reuses_latest_approved_project_request(tmp_path):
    baseline_without_version(tmp_path)
    baseline=tmp_path/".asep"/"dependency-baseline.json"
    original=baseline.read_text(encoding="utf-8")
    subject=service(tmp_path)
    approved=historical_request(subject._dependency_requests)

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].requested_version=="5.9.2"
    assert plan.items[0].status=="approved"
    assert plan.items[0].dependency_request_id==approved.request_id
    assert baseline.read_text(encoding="utf-8")==original


@pytest.mark.parametrize(
    "decision",
    [DependencyRequestDecision.PENDING, DependencyRequestDecision.REJECTED],
)
def test_missing_baseline_version_does_not_reuse_unapproved_request(tmp_path,decision):
    baseline_without_version(tmp_path)
    subject=service(tmp_path)
    historical_request(subject._dependency_requests,decision=decision)

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"
    assert plan.items[0].requested_version is None
    assert plan.items[0].dependency_request_id is None


def test_missing_baseline_version_does_not_cross_project_boundary(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path)
    historical_request(subject._dependency_requests,project_id="other-project")

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"


def test_explicit_baseline_version_remains_authoritative(tmp_path):
    baseline_without_version(tmp_path,version="5.9.2")
    subject=service(tmp_path)
    historical_request(subject._dependency_requests,version="5.8.0")

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].requested_version=="5.9.2"
    assert plan.items[0].status=="pending"
    assert plan.items[0].dependency_request_id is not None


def test_latest_rejected_request_blocks_reuse_of_older_approval(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path,ReversedListDependencyRequestRepository)
    now=datetime.now(UTC)
    historical_request(
        subject._dependency_requests,version="5.8.0",created_at=now-timedelta(days=1),
    )
    historical_request(
        subject._dependency_requests,version="5.9.2",
        decision=DependencyRequestDecision.REJECTED,created_at=now,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"
    assert plan.items[0].requested_version is None


def test_latest_approved_request_is_selected_deterministically(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path,ReversedListDependencyRequestRepository)
    now=datetime.now(UTC)
    historical_request(
        subject._dependency_requests,version="5.8.0",
        decision=DependencyRequestDecision.REJECTED,created_at=now-timedelta(days=1),
    )
    latest=historical_request(
        subject._dependency_requests,version="5.9.2",created_at=now,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].requested_version=="5.9.2"
    assert plan.items[0].dependency_request_id==latest.request_id


def test_equal_latest_creation_times_fail_closed(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path,ReversedListDependencyRequestRepository)
    created_at=datetime.now(UTC)
    historical_request(
        subject._dependency_requests,version="5.8.0",created_at=created_at,
    )
    historical_request(
        subject._dependency_requests,version="5.9.2",created_at=created_at,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"
    assert plan.items[0].requested_version is None


def test_missing_baseline_version_does_not_reuse_other_registry(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path)
    historical_request(subject._dependency_requests,registry="https://registry.example/")

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"


def test_explicit_version_keeps_existing_approved_request_link(tmp_path):
    baseline_without_version(tmp_path,version="5.9.2")
    subject=service(tmp_path)
    approved=historical_request(subject._dependency_requests)

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="approved"
    assert plan.items[0].dependency_request_id==approved.request_id



def test_pending_duplicate_same_version_does_not_hide_approved_decision(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path,ReversedListDependencyRequestRepository)
    now=datetime.now(UTC)

    approved=historical_request(
        subject._dependency_requests,
        version="5.9.2",
        created_at=now-timedelta(minutes=1),
    )
    historical_request(
        subject._dependency_requests,
        version="5.9.2",
        decision=DependencyRequestDecision.PENDING,
        created_at=now,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].requested_version=="5.9.2"
    assert plan.items[0].status=="approved"
    assert plan.items[0].dependency_request_id==approved.request_id


def test_rejected_same_version_after_approval_blocks_reuse(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path)
    now=datetime.now(UTC)

    historical_request(
        subject._dependency_requests,
        version="5.9.2",
        created_at=now-timedelta(minutes=1),
    )
    historical_request(
        subject._dependency_requests,
        version="5.9.2",
        decision=DependencyRequestDecision.REJECTED,
        created_at=now,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"
    assert plan.items[0].requested_version is None


def test_pending_different_version_after_approval_blocks_reuse(tmp_path):
    baseline_without_version(tmp_path)
    subject=service(tmp_path)
    now=datetime.now(UTC)

    historical_request(
        subject._dependency_requests,
        version="5.9.2",
        created_at=now-timedelta(minutes=1),
    )
    historical_request(
        subject._dependency_requests,
        version="6.0.0",
        decision=DependencyRequestDecision.PENDING,
        created_at=now,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="version_selection_required"
    assert plan.items[0].requested_version is None


def test_explicit_version_reuses_approved_request_despite_later_duplicate_pending(tmp_path):
    baseline_without_version(tmp_path,version="5.9.2")
    subject=service(tmp_path)
    now=datetime.now(UTC)

    approved=historical_request(
        subject._dependency_requests,
        version="5.9.2",
        created_at=now-timedelta(minutes=1),
    )
    historical_request(
        subject._dependency_requests,
        version="5.9.2",
        decision=DependencyRequestDecision.PENDING,
        created_at=now,
    )

    plan=subject._dependency_plan(execution(),tmp_path)

    assert plan.items[0].status=="approved"
    assert plan.items[0].dependency_request_id==approved.request_id

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
