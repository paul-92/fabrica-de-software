from datetime import UTC, datetime

import pytest

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeIdentity, AIRuntimeRequest, AIRuntimeResult
from asep.ai_usage import AIUsageOperation
from asep.application.project_ai_runtime import ProjectAIRuntimeExecutionService
from asep.dependency_provisioning import DependencyRequestDecision, SQLiteDependencyRequestRepository
from asep.projects import ProjectExecution, ProjectExecutionStatus


class RuntimeSpy:
    identity = AIRuntimeIdentity(runtime_id="codex", model_id="model")
    def __init__(self): self.calls = 0
    def execute(self, request):
        self.calls += 1
        return AIRuntimeResult(output="ok", identity=self.identity)

class ProvisioningSpy:
    def __init__(self, error=None): self.error=error; self.calls=0
    def provision_node(self, workspace, broker):
        self.calls += 1
        if self.error: raise RuntimeError(self.error)

def subject(tmp_path, repo, provisioning):
    service=object.__new__(ProjectAIRuntimeExecutionService)
    service._clock=lambda:datetime.now(UTC); service._usage=None; service._quotas=None
    service._dependency_requests=repo; service._dependency_provisioning=provisioning
    service._dependency_broker=object(); service._provisioning_evidence=None
    execution=ProjectExecution(execution_id="e",session_id="s",project_id="p",runtime_id="codex",instruction="x",execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE,status=ProjectExecutionStatus.RUNNING,dependency_requests=({"package":"react","requested_version":"19.0.0","reason":"UI"},),created_at=datetime.now(UTC))
    request=AIRuntimeRequest(instruction="x",workspace=tmp_path,execution_mode=AIRuntimeExecutionMode.WORKSPACE_WRITE)
    return service,execution,request

def stored(repo, decision=None):
    item=repo.create(project_id="p",session_id="s",execution_id="e",package="react",requested_version="19.0.0",reason="UI",registry="https://registry.npmjs.org/")
    return item if decision is None else repo.resolve("p",item.request_id,decision,"user",1)

@pytest.mark.parametrize("decision",[None,DependencyRequestDecision.REJECTED])
def test_pending_and_rejected_never_call_runtime(tmp_path,decision):
    (tmp_path/"package.json").write_text('{"packageManager":"pnpm@9.15.0"}',encoding="utf-8")
    repo=SQLiteDependencyRequestRepository(tmp_path/"requests.db"); stored(repo,decision)
    service,execution,request=subject(tmp_path,repo,ProvisioningSpy()); runtime=RuntimeSpy()
    with pytest.raises(RuntimeError): service._invoke_runtime(runtime,request,execution,None,AIUsageOperation.IMPLEMENTATION)
    assert runtime.calls==0

@pytest.mark.parametrize("error",["dependency_policy_blocked","dependency_registry_unavailable","dependency_provisioning_failed"])
def test_provisioning_failures_never_call_runtime(tmp_path,error):
    (tmp_path/"package.json").write_text('{"packageManager":"pnpm@9.15.0"}',encoding="utf-8")
    repo=SQLiteDependencyRequestRepository(tmp_path/"requests.db"); stored(repo,DependencyRequestDecision.APPROVED)
    service,execution,request=subject(tmp_path,repo,ProvisioningSpy(error)); runtime=RuntimeSpy()
    with pytest.raises(RuntimeError,match=error): service._invoke_runtime(runtime,request,execution,None,AIUsageOperation.IMPLEMENTATION)
    assert runtime.calls==0

def test_approved_and_valid_provisioning_calls_runtime_once(tmp_path):
    (tmp_path/"package.json").write_text('{"packageManager":"pnpm@9.15.0"}',encoding="utf-8")
    repo=SQLiteDependencyRequestRepository(tmp_path/"requests.db"); stored(repo,DependencyRequestDecision.APPROVED)
    provisioning=ProvisioningSpy(); service,execution,request=subject(tmp_path,repo,provisioning); runtime=RuntimeSpy()
    result=service._invoke_runtime(runtime,request,execution,None,AIUsageOperation.IMPLEMENTATION)
    assert result.output=="ok" and provisioning.calls==1 and runtime.calls==1
