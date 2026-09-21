from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_activity_service, get_aging_service, get_current_user
from app.schemas.activity import CollectionActivityListResponse
from app.schemas.aging import AgingDistributionResponse
from app.schemas.auth import UserProfile
from app.schemas.dashboard import DashboardMetricsResponse
from app.services.activity_service import CollectionActivityService
from app.services.aging_service import AgingService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    as_of_date: Optional[date] = Query(None, description="Effective valuation date (defaults to today)"),
    aging_service: AgingService = Depends(get_aging_service),
    current_user: UserProfile = Depends(get_current_user),
) -> DashboardMetricsResponse:
    """
    Retrieve high-level operational metrics:
    total receivables, total overdue balance, and DSO (Days Sales Outstanding) estimation.
    """
    metrics = await aging_service.get_metrics_summary(as_of_date=as_of_date)
    return DashboardMetricsResponse(
        total_receivables=metrics["total_receivables"],
        total_overdue=metrics["total_overdue"],
        dso_days=metrics["dso_days"],
        as_of_date=metrics["as_of_date"],
    )


@router.get("/aging", response_model=AgingDistributionResponse)
async def get_dashboard_aging(
    as_of_date: Optional[date] = Query(None, description="Effective valuation date (defaults to today)"),
    aging_service: AgingService = Depends(get_aging_service),
    current_user: UserProfile = Depends(get_current_user),
) -> AgingDistributionResponse:
    """
    Retrieve aging distribution breakdown across all 5 tiers:
    Current, 1–30 Days, 31–60 Days, 61–90 Days, and 90+ Days Overdue.
    """
    return await aging_service.get_aging_distribution(as_of_date=as_of_date)


@router.get("/recent-activity", response_model=CollectionActivityListResponse)
async def get_dashboard_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of recent activities to retrieve"),
    activity_service: CollectionActivityService = Depends(get_activity_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CollectionActivityListResponse:
    """
    Retrieve latest collection activity timeline:
    payment receipts, reminder emails sent, status transitions, and operator notes.
    """
    return await activity_service.get_recent_activities(limit=limit)
