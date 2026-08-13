from datetime import UTC, datetime
from threading import Barrier, Thread
from asep.access import InMemoryAccessRepository, Membership, OrganizationRole, RequestPrincipal, User, UserStatus
from asep.ai_quotas import AIQuotaExceededError, AIQuotaService, InMemoryAIQuotaRepository, SQLiteAIQuotaRepository
from asep.ai_usage import AIUsageOperation, AIUsageService, AIUsageStatus, InMemoryAIUsageRepository
from asep.ai_runtime import AIRuntimeIdentity, AIRuntimeResult, AIRuntimeUsage

NOW=datetime.now(UTC)
def services(tmp_path=None):
    access=InMemoryAccessRepository(); user=User(user_id="u",email="u@example.com",status=UserStatus.ACTIVE,created_at=NOW,updated_at=NOW); access.save_user(user,"hash"); access.save_membership(Membership(organization_id="o",user_id="u",role=OrganizationRole.ADMIN,created_at=NOW))
    usage_repo=InMemoryAIUsageRepository(); quota_repo=InMemoryAIQuotaRepository(usage_repo) if tmp_path is None else SQLiteAIQuotaRepository(tmp_path/"db.sqlite")
    return AIQuotaService(quota_repo,access),AIUsageService(usage_repo),access
def principal(role=OrganizationRole.ADMIN): return RequestPrincipal(user_id="u",organization_id="o",role=role)

def test_call_limit_and_unknown_usage(tmp_path):
    quotas,usage,_=services(); quotas.set(principal(),"u",enabled=True,token_limit=None,call_limit=1)
    a=quotas.admit("o","u"); usage.record(organization_id="o",user_id="u",project_id="p",session_id="s",execution_id="e",runtime_id="r",provider="r",model=None,operation=AIUsageOperation.PLANNING,started_at=NOW,status=AIUsageStatus.SUCCEEDED); quotas.reconcile(a)
    assert quotas.get(principal()).usage.calls_with_unknown_usage==1
    try: quotas.admit("o","u")
    except AIQuotaExceededError as error: assert error.code=="AI_QUOTA_EXCEEDED"
    else: assert False

def test_token_limit_uses_only_known_tokens():
    quotas,usage,_=services(); quotas.set(principal(),"u",enabled=True,token_limit=3,call_limit=None)
    result=AIRuntimeResult(output="ok",identity=AIRuntimeIdentity(runtime_id="r",model_id="m"),usage=AIRuntimeUsage(input_units=1,output_units=2,total_units=3))
    usage.record(organization_id="o",user_id="u",project_id="p",session_id="s",execution_id="e",runtime_id="r",provider="r",model=None,operation=AIUsageOperation.IMPLEMENTATION,started_at=NOW,status=AIUsageStatus.SUCCEEDED,result=result)
    try: quotas.admit("o","u")
    except AIQuotaExceededError: pass
    else: assert False

def test_member_cannot_change_and_cross_tenant_is_hidden():
    quotas,_,_=services()
    for p in (principal(OrganizationRole.MEMBER),RequestPrincipal(user_id="x",organization_id="other",role=OrganizationRole.ADMIN)):
        try: quotas.set(p,"u",enabled=True,token_limit=1,call_limit=1)
        except (Exception,): pass
        else: assert False

def test_suspended_user_is_rejected():
    quotas,_,access=services(); user=access.get_user("o","u"); access.update_user(user.model_copy(update={"status":UserStatus.SUSPENDED}))
    try: quotas.admit("o","u")
    except Exception: pass
    else: assert False

def test_atomic_reservation_allows_only_one():
    quotas,_,_=services(); quotas.set(principal(),"u",enabled=True,token_limit=None,call_limit=1); barrier=Barrier(2); results=[]
    def run():
        barrier.wait()
        try: quotas.admit("o","u"); results.append("allowed")
        except AIQuotaExceededError: results.append("blocked")
    threads=[Thread(target=run) for _ in range(2)]; [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results)==["allowed","blocked"]

def test_sqlite_quota_survives_restart(tmp_path):
    quotas,_,_=services(tmp_path); quotas.set(principal(),"u",enabled=True,token_limit=10,call_limit=2)
    restarted,_,_=services(tmp_path); assert restarted.get(principal()).quota.call_limit==2

def test_no_quota_is_unlimited():
    quotas,_,_=services(); assert quotas.admit("o","u").reservation_id is None
