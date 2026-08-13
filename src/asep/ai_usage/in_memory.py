from datetime import datetime
from asep.ai_usage.models import AIUsageRecord

class InMemoryAIUsageRepository:
    def __init__(self): self._items: dict[str, AIUsageRecord] = {}
    def append(self, record: AIUsageRecord) -> None:
        if record.usage_id in self._items: raise ValueError("usage record already exists")
        self._items[record.usage_id] = record.model_copy(deep=True)
    def query(self, organization_id: str, *, user_id: str | None = None,
              project_id: str | None = None, execution_id: str | None = None,
              started_from: datetime | None = None, started_to: datetime | None = None):
        return tuple(item.model_copy(deep=True) for item in sorted(self._items.values(), key=lambda x:(x.started_at,x.usage_id))
                     if item.organization_id == organization_id
                     and (user_id is None or item.user_id == user_id)
                     and (project_id is None or item.project_id == project_id)
                     and (execution_id is None or item.execution_id == execution_id)
                     and (started_from is None or item.started_at >= started_from)
                     and (started_to is None or item.started_at <= started_to))

