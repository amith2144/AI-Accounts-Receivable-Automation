import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityType, CollectionActivity
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[CollectionActivity]):
    """
    Repository providing immutable append-only persistence and querying
    for collection communications, notes, and lifecycle audit activities.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(CollectionActivity, session)

    async def get_by_invoice(
        self,
        invoice_id: uuid.UUID,
        limit: int = 50,
    ) -> Sequence[CollectionActivity]:
        """Retrieve collection activity timeline for a specific invoice."""
        stmt = (
            select(CollectionActivity)
            .where(CollectionActivity.invoice_id == invoice_id)
            .order_by(CollectionActivity.created_at.desc(), CollectionActivity.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_customer(
        self,
        customer_id: uuid.UUID,
        limit: int = 50,
    ) -> Sequence[CollectionActivity]:
        """Retrieve complete audit history across all invoices for a customer."""
        stmt = (
            select(CollectionActivity)
            .where(CollectionActivity.customer_id == customer_id)
            .order_by(CollectionActivity.created_at.desc(), CollectionActivity.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_recent(
        self,
        limit: int = 50,
        activity_type: Optional[ActivityType] = None,
    ) -> Sequence[CollectionActivity]:
        """Retrieve recent collection activities across tenant for operational dashboard."""
        stmt = select(CollectionActivity)
        if activity_type:
            stmt = stmt.where(CollectionActivity.activity_type == activity_type)
        stmt = stmt.order_by(CollectionActivity.created_at.desc(), CollectionActivity.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def has_recent_reminder(
        self,
        invoice_id: uuid.UUID,
        since: datetime,
    ) -> bool:
        """Check whether a reminder email was already dispatched to this invoice since the given timestamp."""
        stmt = (
            select(func.count())
            .select_from(CollectionActivity)
            .where(
                CollectionActivity.invoice_id == invoice_id,
                CollectionActivity.activity_type == ActivityType.REMINDER_SENT,
                CollectionActivity.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def has_dispatched_cadence(
        self,
        invoice_id: uuid.UUID,
        cadence_id: uuid.UUID,
    ) -> bool:
        """
        Check whether a specific cadence rule has already fired for this invoice.
        Uses database-level JSON filtering compatible with SQLite and Postgres.
        """
        stmt = (
            select(CollectionActivity)
            .where(
                CollectionActivity.invoice_id == invoice_id,
                CollectionActivity.activity_type == ActivityType.REMINDER_SENT,
            )
        )
        result = await self.session.execute(stmt)
        activities = result.scalars().all()
        for act in activities:
            if act.details and act.details.get("cadence_id") == str(cadence_id):
                return True
        return False
