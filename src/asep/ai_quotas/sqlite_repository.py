import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from asep.ai_quotas.models import AIQuota, AIQuotaAdmission, AIQuotaUsage
from asep.sqlite import SQLiteDatabase

class SQLiteAIQuotaRepository:
    def __init__(self,path:Path): self.db=SQLiteDatabase(path)
    def get(self,organization_id,user_id):
        with self.db.connect() as c: row=c.execute("SELECT payload FROM ai_quotas WHERE organization_id=? AND user_id=?",(organization_id,user_id)).fetchone()
        return None if row is None else AIQuota.model_validate_json(row["payload"])
    def save(self,q):
        with self.db.connect() as c: c.execute("INSERT OR REPLACE INTO ai_quotas (organization_id,user_id,payload) VALUES (?,?,?)",(q.organization_id,q.user_id,q.model_dump_json()))
        return q
    def delete(self,o,u):
        with self.db.connect() as c: c.execute("DELETE FROM ai_quotas WHERE organization_id=? AND user_id=?",(o,u))
    def admit(self,o,u,start,end):
        return self._snapshot(o,u,start,end,True)
    def inspect(self,o,u,start,end):
        return self._snapshot(o,u,start,end,False)
    def _snapshot(self,o,u,start,end,reserve):
        rid=str(uuid4())
        with self.db.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT payload FROM ai_quotas WHERE organization_id=? AND user_id=?",(o,u)).fetchone(); q=None if row is None else AIQuota.model_validate_json(row["payload"])
            rows=c.execute("SELECT payload FROM ai_usage_ledger WHERE organization_id=? AND user_id=? AND started_at>=? AND started_at<?",(o,u,start.isoformat(),end.isoformat())).fetchall()
            calls=len(rows); totals=[]
            for row in rows:
                value=json.loads(row["payload"]).get("total_tokens")
                if value is not None: totals.append(value)
            reserved=c.execute("SELECT COUNT(*) FROM ai_quota_reservations WHERE organization_id=? AND user_id=? AND period_started_at=? AND status='reserved'",(o,u,start.isoformat())).fetchone()[0]
            if reserve and q is not None and q.enabled: c.execute("INSERT INTO ai_quota_reservations (id,organization_id,user_id,period_started_at,status,created_at) VALUES (?,?,?,?,?,?)",(rid,o,u,start.isoformat(),"reserved",datetime.now(start.tzinfo).isoformat()))
            else: rid=None
        return AIQuotaAdmission(reservation_id=rid,quota=q,usage=AIQuotaUsage(calls=calls,known_total_tokens=sum(totals),calls_with_unknown_usage=calls-len(totals),reserved_calls=reserved+(1 if rid else 0),period_started_at=start,period_ends_at=end))
    def reconcile(self,rid): self._finish(rid,"reconciled")
    def release(self,rid): self._finish(rid,"released")
    def _finish(self,rid,status):
        with self.db.connect() as c: c.execute("UPDATE ai_quota_reservations SET status=? WHERE id=? AND status='reserved'",(status,rid))
