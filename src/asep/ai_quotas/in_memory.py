from threading import Lock
from uuid import uuid4
from asep.ai_quotas.models import AIQuotaAdmission, AIQuotaUsage

class InMemoryAIQuotaRepository:
    def __init__(self, usage_repository): self.quotas={}; self.reservations={}; self.usage=usage_repository; self.lock=Lock()
    def get(self,o,u): return self.quotas.get((o,u))
    def save(self,q): self.quotas[(q.organization_id,q.user_id)]=q; return q
    def delete(self,o,u): self.quotas.pop((o,u),None)
    def admit(self,o,u,start,end):
        return self._snapshot(o,u,start,end,True)
    def inspect(self,o,u,start,end):
        return self._snapshot(o,u,start,end,False)
    def _snapshot(self,o,u,start,end,reserve):
        with self.lock:
            q=self.get(o,u); items=self.usage.query(o,user_id=u,started_from=start,started_to=end)
            reserved=sum(v[:3]==(o,u,start) and v[3]=="reserved" for v in self.reservations.values()); rid=None
            if reserve and q and q.enabled: rid=str(uuid4()); self.reservations[rid]=(o,u,start,"reserved")
            known=[x.total_tokens for x in items if x.total_tokens is not None]
            return AIQuotaAdmission(reservation_id=rid,quota=q,usage=AIQuotaUsage(calls=len(items),known_total_tokens=sum(known),calls_with_unknown_usage=len(items)-len(known),reserved_calls=reserved+(1 if rid else 0),period_started_at=start,period_ends_at=end))
    def reconcile(self,rid): self._finish(rid,"reconciled")
    def release(self,rid): self._finish(rid,"released")
    def _finish(self,rid,status):
        with self.lock:
            if rid in self.reservations:
                o,u,s,_=self.reservations[rid]; self.reservations[rid]=(o,u,s,status)
