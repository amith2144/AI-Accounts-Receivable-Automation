import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.aging import AgingBucket, AgingSchedule
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.base import BaseRepository


class AgingRepository(BaseRepository[AgingSchedule]):
    """Repository managing AgingSchedule calculation snapshots and bucket aggregations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AgingSchedule, session)

    async def get_by_invoice(self, invoice_id: uuid.UUID) -> Optional[AgingSchedule]:
        """Retrieve existing aging schedule record for an invoice."""
        stmt = select(AgingSchedule).where(AgingSchedule.invoice_id == invoice_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_schedule(
        self,
        invoice_id: uuid.UUID,
        days_overdue: int,
        bucket: AgingBucket,
    ) -> AgingSchedule:
        """Create or update aging schedule snapshot for an invoice."""
        schedule = await self.get_by_invoice(invoice_id)
        if schedule:
            schedule.days_overdue = days_overdue
            schedule.bucket = bucket
            schedule.last_calculated_at = datetime.now()
            self.session.add(schedule)
        else:
            schedule = AgingSchedule(
                id=uuid.uuid4(),
                invoice_id=invoice_id,
                days_overdue=days_overdue,
                bucket=bucket,
                last_calculated_at=datetime.now(),
            )
            self.session.add(schedule)

        await self.session.flush()
        await self.session.refresh(schedule)
        return schedule

    async def get_aging_distribution(self) -> Dict[AgingBucket, Dict[str, Any]]:
        """
        Aggregate active unpaid invoices grouped by aging bucket.
        Returns invoice counts and outstanding balances per bucket.
        """
        stmt = (
            select(
                AgingSchedule.bucket,
                func.count(Invoice.id),
                func.coalesce(func.sum(Invoice.balance_due), 0),
            )
            .join(Invoice, Invoice.id == AgingSchedule.invoice_id)
            .where(Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.VOID]))
            .group_by(AgingSchedule.bucket)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        distribution = {b: {"invoice_count": 0, "total_balance": Decimal("0.00")} for b in AgingBucket}
        for row in rows:
            bucket, count, balance = row[0], row[1], Decimal(str(row[2]))
            distribution[bucket] = {
                "invoice_count": count,
                "total_balance": balance,
            }
        return distribution

    async def get_active_invoices_for_aging(self) -> Sequence[Invoice]:
        """Query all active, non-void, non-paid invoices requiring aging evaluation."""
        stmt = (
            select(Invoice)
            .where(Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.VOID]))
            .options(selectinload(Invoice.aging_schedule))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_metrics_summary(self, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Compute aggregate AR metrics: total receivables, total overdue, and DSO estimation."""
        target_date = as_of_date or date.today()

        # Total Receivables (unpaid, non-void invoices)
        stmt_receivables = select(func.coalesce(func.sum(Invoice.balance_due), 0)).where(
            Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.VOID])
        )
        res_rec = await self.session.execute(stmt_receivables)
        total_receivables = Decimal(str(res_rec.scalar() or 0))

        # Total Overdue (due_date < target_date)
        stmt_overdue = select(func.coalesce(func.sum(Invoice.balance_due), 0)).where(
            Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.VOID]),
            Invoice.due_date < target_date,
        )
        res_ovd = await self.session.execute(stmt_overdue)
        total_overdue = Decimal(str(res_ovd.scalar() or 0))

        # Total Invoiced across all non-void invoices (for DSO baseline)
        stmt_invoiced = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.status != InvoiceStatus.VOID
        )
        res_inv = await self.session.execute(stmt_invoiced)
        total_invoiced = Decimal(str(res_inv.scalar() or 0))

        # DSO formula: (Total Receivables / Total Invoiced) * 90 (if invoiced > 0)
        dso = 0.0
        if total_invoiced > Decimal("0.00"):
            dso = round(float(total_receivables / total_invoiced) * 90.0, 1)

        return {
            "total_receivables": total_receivables,
            "total_overdue": total_overdue,
            "dso_days": dso,
        }
