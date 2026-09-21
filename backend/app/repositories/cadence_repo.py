import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cadence import ReminderCadence
from app.repositories.base import BaseRepository


class CadenceRepository(BaseRepository[ReminderCadence]):
    """Repository managing ReminderCadence rules, trigger schedules, and email templates."""

    def __init__(self, session: AsyncSession):
        super().__init__(ReminderCadence, session)

    async def get_active_cadences(self) -> Sequence[ReminderCadence]:
        """Retrieve all active reminder cadences ordered by trigger offset days."""
        stmt = (
            select(ReminderCadence)
            .where(ReminderCadence.is_active == True)
            .order_by(ReminderCadence.trigger_offset_days.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
