from datetime import UTC, datetime
from uuid import uuid4
from asep.access import AccessDeniedError, AccessRepository, OrganizationRole, RequestPrincipal, UserStatus
from asep.ai_quotas.models import AIQuota, QuotaPeriod
from asep.ai_quotas.repository import AIQuotaRepository

class AIQuotaExceededError(RuntimeError):
    code = "AI_QUOTA_EXCEEDED"
    def __init__(self): super().__init__("AI quota exceeded.")

class AIQuotaService:
    def __init__(self, repository: AIQuotaRepository, access: AccessRepository):
        self.repository, self.access = repository, access
    @staticmethod
    def window(now: datetime):
        now=now.astimezone(UTC); start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        end=start.replace(year=start.year+(start.month==12),month=1 if start.month==12 else start.month+1)
        return start,end
    def admit(self, organization_id: str, user_id: str):
        user=self.access.get_user(organization_id,user_id)
        if user is None or user.status is not UserStatus.ACTIVE: raise AccessDeniedError("access denied")
        start,end=self.window(datetime.now(UTC))
        admission=self.repository.admit(organization_id,user_id,start,end)
        q,u=admission.quota,admission.usage
        if q and q.enabled and ((q.call_limit is not None and u.calls+u.reserved_calls > q.call_limit) or (q.token_limit is not None and u.known_total_tokens >= q.token_limit)):
            if admission.reservation_id: self.repository.release(admission.reservation_id)
            raise AIQuotaExceededError()
        return admission
    def reconcile(self, admission):
        if admission.reservation_id: self.repository.reconcile(admission.reservation_id)
    def release(self, admission):
        if admission.reservation_id: self.repository.release(admission.reservation_id)
    def get(self, principal: RequestPrincipal, user_id: str | None=None):
        target=user_id or principal.user_id
        if target != principal.user_id and principal.role is not OrganizationRole.ADMIN: raise AccessDeniedError("administrator access required")
        if self.access.get_user(principal.organization_id,target) is None: raise KeyError(target)
        start,end=self.window(datetime.now(UTC))
        return self.repository.inspect(principal.organization_id,target,start,end)
    def set(self, principal: RequestPrincipal, user_id: str, *, enabled: bool, token_limit: int|None, call_limit:int|None):
        if principal.role is not OrganizationRole.ADMIN: raise AccessDeniedError("administrator access required")
        if self.access.get_user(principal.organization_id,user_id) is None: raise KeyError(user_id)
        now=datetime.now(UTC); old=self.repository.get(principal.organization_id,user_id)
        return self.repository.save(AIQuota(organization_id=principal.organization_id,user_id=user_id,enabled=enabled,token_limit=token_limit,call_limit=call_limit,period=QuotaPeriod.MONTHLY,created_at=old.created_at if old else now,updated_at=now))
    def remove(self, principal, user_id):
        if principal.role is not OrganizationRole.ADMIN: raise AccessDeniedError("administrator access required")
        if self.access.get_user(principal.organization_id,user_id) is None: raise KeyError(user_id)
        self.repository.delete(principal.organization_id,user_id)
