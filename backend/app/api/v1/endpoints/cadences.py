import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_activity_service,
    get_cadence_service,
    get_current_user,
)
from app.models.activity import ActivityType
from app.schemas.activity import CollectionActivityListResponse
from app.schemas.auth import UserProfile
from app.schemas.cadence import (
    CadenceDispatchSummary,
    ReminderCadenceCreate,
    ReminderCadenceResponse,
    ReminderCadenceUpdate,
)
from app.services.activity_service import CollectionActivityService
from app.services.cadence_service import CadenceService

router = APIRouter(prefix="/cadences", tags=["Cadences"])
activities_router = APIRouter(prefix="/activities", tags=["Collection Activities"])


# --- Cadence Administration Endpoints ---


@router.get("", response_model=List[ReminderCadenceResponse])
async def list_cadences(
    cadence_service: CadenceService = Depends(get_cadence_service),
    current_user: UserProfile = Depends(get_current_user),
) -> List[ReminderCadenceResponse]:
    """List all configured automated payment reminder cadences."""
    return await cadence_service.list_cadences()


@router.post("", response_model=ReminderCadenceResponse, status_code=status.HTTP_201_CREATED)
async def create_cadence(
    data: ReminderCadenceCreate,
    cadence_service: CadenceService = Depends(get_cadence_service),
    current_user: UserProfile = Depends(get_current_user),
) -> ReminderCadenceResponse:
    """Create a new automated reminder rule, offset trigger, and Jinja2 email template."""
    return await cadence_service.create_cadence(data)


@router.get("/{cadence_id}", response_model=ReminderCadenceResponse)
async def get_cadence(
    cadence_id: uuid.UUID,
    cadence_service: CadenceService = Depends(get_cadence_service),
    current_user: UserProfile = Depends(get_current_user),
) -> ReminderCadenceResponse:
    """Retrieve cadence rule configuration by ID."""
    return await cadence_service.get_cadence(cadence_id)


@router.put("/{cadence_id}", response_model=ReminderCadenceResponse)
async def update_cadence(
    cadence_id: uuid.UUID,
    data: ReminderCadenceUpdate,
    cadence_service: CadenceService = Depends(get_cadence_service),
    current_user: UserProfile = Depends(get_current_user),
) -> ReminderCadenceResponse:
    """Update cadence rule parameters, trigger schedule, tone, or email templates."""
    return await cadence_service.update_cadence(cadence_id, data)


@router.delete("/{cadence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cadence(
    cadence_id: uuid.UUID,
    cadence_service: CadenceService = Depends(get_cadence_service),
    current_user: UserProfile = Depends(get_current_user),
) -> None:
    """Delete a reminder cadence rule."""
    await cadence_service.delete_cadence(cadence_id)


@router.post("/trigger-run", response_model=CadenceDispatchSummary)
async def trigger_cadence_run(
    as_of_date: Optional[date] = Query(None, description="Evaluation date (defaults to today)"),
    dry_run: bool = Query(False, description="Preview dispatch without transmitting emails"),
    cadence_service: CadenceService = Depends(get_cadence_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CadenceDispatchSummary:
    """
    Manually trigger on-demand evaluation and dispatch of overdue reminders.
    Enforces customer pause overrides, 24-hour duplicate throttling, and Jinja2 rendering.
    """
    return await cadence_service.evaluate_and_dispatch_cadences(
        as_of_date=as_of_date,
        dry_run=dry_run,
    )


# --- Collection Activities Audit Trail Endpoint ---


@activities_router.get("", response_model=CollectionActivityListResponse)
async def list_collection_activities(
    customer_id: Optional[uuid.UUID] = Query(None, description="Filter activities by customer"),
    invoice_id: Optional[uuid.UUID] = Query(None, description="Filter activities by invoice"),
    activity_type: Optional[ActivityType] = Query(None, description="Filter by activity category"),
    limit: int = Query(50, ge=1, le=100, description="Max records to retrieve"),
    activity_service: CollectionActivityService = Depends(get_activity_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CollectionActivityListResponse:
    """Query comprehensive collection activity audit trail across invoices and customers."""
    if invoice_id:
        return await activity_service.get_invoice_activities(invoice_id, limit=limit)
    elif customer_id:
        return await activity_service.get_customer_activities(customer_id, limit=limit)
    else:
        return await activity_service.get_recent_activities(limit=limit, activity_type=activity_type)
