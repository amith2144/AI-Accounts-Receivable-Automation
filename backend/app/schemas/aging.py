import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.aging import AgingBucket


class AgingScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    days_overdue: int
    bucket: AgingBucket
    last_calculated_at: datetime


class AgingBucketSummary(BaseModel):
    bucket: AgingBucket
    label: str
    invoice_count: int = 0
    total_balance: Decimal = Decimal("0.00")


class AgingDistributionResponse(BaseModel):
    buckets: Dict[str, AgingBucketSummary]
    total_receivables: Decimal
    total_overdue: Decimal
    dso_days: float = Field(0.0, description="Estimated Days Sales Outstanding")
