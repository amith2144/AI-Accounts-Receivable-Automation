import uuid
from decimal import Decimal
from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentRecord
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[PaymentRecord]):
    """Repository managing remittance ledger records and invoice payment history."""

    def __init__(self, session: AsyncSession):
        super().__init__(PaymentRecord, session)

    async def get_by_invoice(self, invoice_id: uuid.UUID) -> Sequence[PaymentRecord]:
        """Retrieve all remittance records for an invoice, ordered chronologically descending."""
        stmt = (
            select(PaymentRecord)
            .where(PaymentRecord.invoice_id == invoice_id)
            .order_by(PaymentRecord.payment_date.desc(), PaymentRecord.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_total_paid(self, invoice_id: uuid.UUID) -> Decimal:
        """Calculate the sum of all payments recorded for an invoice."""
        stmt = select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.invoice_id == invoice_id
        )
        result = await self.session.execute(stmt)
        total = result.scalar() or 0
        return Decimal(str(total))
