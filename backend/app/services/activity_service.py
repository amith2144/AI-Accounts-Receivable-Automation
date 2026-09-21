import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityType, CollectionActivity
from app.repositories.activity_repo import ActivityRepository
from app.schemas.activity import (
    CollectionActivityCreate,
    CollectionActivityListResponse,
    CollectionActivityResponse,
)

logger = logging.getLogger("app.services.activity")


class CollectionActivityService:
    """
    Domain service for immutable audit logging of collection communications,
    status transitions, payment remittances, and operator collection notes.
    Enforces Rule 02 and Rule 03.
    """

    def __init__(
        self,
        session: AsyncSession,
        activity_repo: Optional[ActivityRepository] = None,
    ):
        self.session = session
        self.activity_repo = activity_repo or ActivityRepository(session)

    async def log_activity(
        self,
        invoice_id: uuid.UUID,
        customer_id: uuid.UUID,
        activity_type: ActivityType,
        performed_by: str = "SYSTEM_AUTOMATION",
        details: Optional[Dict[str, Any]] = None,
    ) -> CollectionActivityResponse:
        """Persist an immutable audit activity record into the collection timeline."""
        activity = CollectionActivity(
            id=uuid.uuid4(),
            invoice_id=invoice_id,
            customer_id=customer_id,
            activity_type=activity_type,
            performed_by=performed_by,
            details=details or {},
        )
        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)

        logger.debug(
            f"Recorded {activity_type.value} activity for invoice {invoice_id} "
            f"performed by {performed_by}"
        )
        return CollectionActivityResponse.model_validate(activity)

    async def get_invoice_activities(
        self,
        invoice_id: uuid.UUID,
        limit: int = 50,
    ) -> CollectionActivityListResponse:
        """Retrieve collection activity timeline for a specific invoice."""
        records = await self.activity_repo.get_by_invoice(invoice_id, limit=limit)
        items = [CollectionActivityResponse.model_validate(r) for r in records]
        return CollectionActivityListResponse(items=items, total=len(items), offset=0, limit=limit)

    async def get_customer_activities(
        self,
        customer_id: uuid.UUID,
        limit: int = 50,
    ) -> CollectionActivityListResponse:
        """Retrieve all collection activities across all invoices for a customer."""
        records = await self.activity_repo.get_by_customer(customer_id, limit=limit)
        items = [CollectionActivityResponse.model_validate(r) for r in records]
        return CollectionActivityListResponse(items=items, total=len(items), offset=0, limit=limit)

    async def get_recent_activities(
        self,
        limit: int = 50,
        activity_type: Optional[ActivityType] = None,
    ) -> CollectionActivityListResponse:
        """Retrieve recent collection activity stream for dashboard telemetry."""
        records = await self.activity_repo.list_recent(limit=limit, activity_type=activity_type)
        items = [CollectionActivityResponse.model_validate(r) for r in records]
        return CollectionActivityListResponse(items=items, total=len(items), offset=0, limit=limit)

    async def has_recent_reminder_sent(
        self,
        invoice_id: uuid.UUID,
        hours: int = 24,
    ) -> bool:
        """Check whether a reminder email was already dispatched to this invoice in the last N hours."""
        since = datetime.now() - timedelta(hours=hours)
        return await self.activity_repo.has_recent_reminder(invoice_id, since)
