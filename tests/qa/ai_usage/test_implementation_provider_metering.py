from datetime import UTC, datetime

import pytest

from asep.ai_runtime import AIRuntimeIdentity, AIRuntimeUsage
from asep.ai_usage import AIUsageService, InMemoryAIUsageRepository
from asep.application import (
    AIBackedEngineeringImplementationProvider, AIImplementationResult, BoundedProjectAnalysis, EngineeringFileChange,
    EngineeringImplementationContext, MeteredEngineeringImplementationProvider,
)
from asep.projects import ProjectOperationalPlan, ProjectOperationalPlanOperation, ProjectOperationalPlanSource, ProjectOperationalPlanStep

NOW=datetime.now(UTC)
STEP=ProjectOperationalPlanStep(step_id="implement",operation=ProjectOperationalPlanOperation.IMPLEMENT,description="Implement")
PLAN=ProjectOperationalPlan(execution_id="exec-1",steps=(STEP,),created_at=NOW,source=ProjectOperationalPlanSource.AI)

def context(org="org-a"):
    return EngineeringImplementationContext(execution_id="exec-1",organization_id=org,user_id="user-a",project_id="project-a",session_id="session-a",task="task",analysis=BoundedProjectAnalysis(),plan=PLAN,step=STEP)

class AIProvider:
    identity=AIRuntimeIdentity(runtime_id="provider-runtime",model_id="model")
    def __init__(self, *, fail=False, already_metered=False): self.fail=fail; self.already_metered=already_metered
    def supports(self,step): return True
    def invoke_ai(self,ctx):
        if self.fail: raise RuntimeError("provider failed")
        return AIImplementationResult(changes=(EngineeringFileChange(relative_path="app.py",content="x"),),identity=self.identity,provider="provider",usage=AIRuntimeUsage(input_units=7,output_units=3,total_units=10),provider_request_id="req-1",already_metered=self.already_metered)

def test_ai_backed_provider_is_metered_once_with_trusted_context():
    repository=InMemoryAIUsageRepository(); provider=MeteredEngineeringImplementationProvider(AIProvider(),AIUsageService(repository))
    assert provider.changes_for(context())[0].relative_path == "app.py"
    items=repository.query("org-a",execution_id="exec-1")
    assert len(items)==1 and items[0].operation.value=="implementation" and items[0].total_tokens==10
    assert items[0].user_id=="user-a" and items[0].project_id=="project-a" and items[0].session_id=="session-a"
    assert repository.query("org-b",execution_id="exec-1") == ()

def test_already_metered_provider_is_not_double_counted():
    repository=InMemoryAIUsageRepository()
    MeteredEngineeringImplementationProvider(AIProvider(already_metered=True),AIUsageService(repository)).changes_for(context())
    assert repository.query("org-a") == ()

def test_failed_ai_provider_records_failed_once_and_reraises():
    repository=InMemoryAIUsageRepository(); provider=MeteredEngineeringImplementationProvider(AIProvider(fail=True),AIUsageService(repository))
    with pytest.raises(RuntimeError,match="provider failed"): provider.changes_for(context())
    items=repository.query("org-a")
    assert len(items)==1 and items[0].status.value=="failed" and items[0].execution_id=="exec-1"

def test_non_ai_provider_is_not_a_metered_boundary():
    class Deterministic:
        def supports(self,step): return True
        def changes_for(self,ctx): return ()
    assert not isinstance(Deterministic(), AIBackedEngineeringImplementationProvider)
