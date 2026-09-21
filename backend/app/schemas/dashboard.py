from datetime import date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.activity import CollectionActivityResponse
from app.schemas.aging import AgingDistributionResponse


class DashboardMetricsResponse(BaseModel):
    total_receivables: Decimal = Field(..., description="Outstanding balance across all unpaid invoices")
    total_overdue: Decimal = Field(..., description="Outstanding balance across past-due invoices")
    dso_days: float = Field(0.0, description="Estimated Days Sales Outstanding (DSO)")
    as_of_date: date = Field(default_factory=date.today, description="Calculation effective date")


class DashboardActivityListResponse(BaseModel):
    items: List[CollectionActivityResponse]
    total: int
