from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field

class QuotaPeriod(StrEnum): MONTHLY = "monthly"

class AIQuota(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    organization_id: str
    user_id: str
    enabled: bool = True
    token_limit: int | None = Field(default=None, ge=0)
    call_limit: int | None = Field(default=None, ge=0)
    period: QuotaPeriod = QuotaPeriod.MONTHLY
    created_at: datetime
    updated_at: datetime

class AIQuotaUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    calls: int
    known_total_tokens: int
    calls_with_unknown_usage: int
    reserved_calls: int = 0
    period_started_at: datetime
    period_ends_at: datetime

class AIQuotaAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reservation_id: str | None = None
    quota: AIQuota | None = None
    usage: AIQuotaUsage

