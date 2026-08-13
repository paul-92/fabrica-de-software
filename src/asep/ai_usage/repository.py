from __future__ import annotations
from datetime import datetime
from typing import Protocol
from asep.ai_usage.models import AIUsageRecord

class AIUsageRepository(Protocol):
    def append(self, record: AIUsageRecord) -> None: ...
    def query(self, organization_id: str, *, user_id: str | None = None,
              project_id: str | None = None, execution_id: str | None = None,
              started_from: datetime | None = None,
              started_to: datetime | None = None) -> tuple[AIUsageRecord, ...]: ...

