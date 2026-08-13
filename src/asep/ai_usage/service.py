from __future__ import annotations
from datetime import UTC, datetime
from uuid import uuid4
from asep.ai_runtime import AIRuntimeResult
from asep.ai_usage.models import AIUsageAggregate, AIUsageOperation, AIUsageRecord, AIUsageStatus
from asep.ai_usage.repository import AIUsageRepository

class AIUsageService:
    """Fail-closed audit ledger: a provider result is not reported as success if its audit write fails."""
    def __init__(self, repository: AIUsageRepository): self.repository=repository
    def record(self, *, organization_id:str,user_id:str,project_id:str,session_id:str,execution_id:str,
               runtime_id:str,provider:str,model:str|None,operation:AIUsageOperation,started_at:datetime,
               status:AIUsageStatus,result:AIRuntimeResult|None=None,provider_request_id:str|None=None) -> AIUsageRecord:
        usage=result.usage if result is not None else None
        request_id=provider_request_id
        if request_id is None and result is not None:
            candidate=result.metadata.get("provider_request_id") or result.metadata.get("request_id")
            request_id=candidate if isinstance(candidate,str) else None
        item=AIUsageRecord(usage_id=str(uuid4()),organization_id=organization_id,user_id=user_id,project_id=project_id,
            session_id=session_id,execution_id=execution_id,runtime_id=runtime_id,provider=provider,model=model,
            operation=operation,input_tokens=None if usage is None else usage.input_units,
            output_tokens=None if usage is None else usage.output_units,total_tokens=None if usage is None else usage.total_units,
            provider_request_id=request_id,started_at=started_at,completed_at=datetime.now(UTC),status=status)
        self.repository.append(item); return item
    def query(self, organization_id:str, **filters): return self.repository.query(organization_id,**filters)
    def aggregate(self, organization_id:str, **filters) -> AIUsageAggregate:
        items=self.query(organization_id,**filters)
        return AIUsageAggregate(calls=len(items),known_input_tokens=sum(x.input_tokens or 0 for x in items),
            known_output_tokens=sum(x.output_tokens or 0 for x in items),known_total_tokens=sum(x.total_tokens or 0 for x in items),
            calls_with_unknown_usage=sum(x.input_tokens is None or x.output_tokens is None or x.total_tokens is None for x in items))

