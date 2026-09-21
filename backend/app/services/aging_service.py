import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.aging import AgingBucket, AgingSchedule
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.aging_repo import AgingRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.schemas.aging import (
    AgingBucketSummary,
    AgingDistributionResponse,
    AgingScheduleResponse,
)

logger = logging.getLogger("app.services.aging")

BUCKET_LABELS = {
    AgingBucket.CURRENT: "Current (Not Due)",
    AgingBucket.DAYS_1_30: "1–30 Days Overdue",
    AgingBucket.DAYS_31_60: "31–60 Days Overdue",
    AgingBucket.DAYS_61_90: "61–90 Days Overdue",
    AgingBucket.DAYS_90_PLUS: "90+ Days Overdue",
}


class AgingService:
    """
    Domain service for Accounts Receivable aging schedule calculation,
    5-tier overdue bucket assignment, and dashboard telemetry aggregation.
    Enforces Rule 02 by encapsulating all mathematical and categorization rules.
    """

    def __init__(
        self,
        session: AsyncSession,
        aging_repo: Optional[AgingRepository] = None,
        invoice_repo: Optional[InvoiceRepository] = None,
    ):
        self.session = session
        self.aging_repo = aging_repo or AgingRepository(session)
        self.invoice_repo = invoice_repo or InvoiceRepository(session)

    @staticmethod
    def classify_bucket(days_diff: int) -> Tuple[int, AgingBucket]:
        """
        Categorize an invoice based on elapsed days past its due date.
        Returns (days_overdue, AgingBucket).
        """
        days_overdue = max(0, days_diff)
        if days_diff <= 0:
            return 0, AgingBucket.CURRENT
        elif 1 <= days_diff <= 30:
            return days_overdue, AgingBucket.DAYS_1_30
        elif 31 <= days_diff <= 60:
            return days_overdue, AgingBucket.DAYS_31_60
        elif 61 <= days_diff <= 90:
            return days_overdue, AgingBucket.DAYS_61_90
        else:
            return days_overdue, AgingBucket.DAYS_90_PLUS

    async def calculate_invoice_aging(
        self,
        invoice_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> AgingScheduleResponse:
        """Calculate and persist aging schedule for a single invoice."""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice with ID {invoice_id} not found.")

        target_date = as_of_date or date.today()
        days_diff = (target_date - invoice.due_date).days
        days_overdue, bucket = self.classify_bucket(days_diff)

        # Update invoice lifecycle state if overdue
        if invoice.status not in [InvoiceStatus.PAID, InvoiceStatus.VOID]:
            if days_diff > 0 and invoice.status in [InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]:
                invoice.status = InvoiceStatus.OVERDUE
            elif days_diff <= 0 and invoice.status == InvoiceStatus.OVERDUE:
                invoice.status = (
                    InvoiceStatus.PARTIALLY_PAID
                    if invoice.balance_due < invoice.total_amount
                    else InvoiceStatus.ISSUED
                )

        schedule = await self.aging_repo.upsert_schedule(
            invoice_id=invoice.id,
            days_overdue=days_overdue,
            bucket=bucket,
        )
        await self.session.flush()

        logger.debug(
            f"Calculated aging for invoice {invoice.invoice_number}: "
            f"{days_overdue} days overdue -> {bucket.value}"
        )
        return AgingScheduleResponse.model_validate(schedule)

    async def recalculate_all_active_invoices(
        self,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Batch process all active, uncollected invoices and update their aging snapshots.
        Executed nightly by Celery Beat scheduler.
        """
        target_date = as_of_date or date.today()
        invoices = await self.aging_repo.get_active_invoices_for_aging()

        counts = {b.value: 0 for b in AgingBucket}
        overdue_invoices = 0

        for invoice in invoices:
            days_diff = (target_date - invoice.due_date).days
            days_overdue, bucket = self.classify_bucket(days_diff)

            if days_diff > 0 and invoice.status in [InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]:
                invoice.status = InvoiceStatus.OVERDUE
            elif days_diff <= 0 and invoice.status == InvoiceStatus.OVERDUE:
                invoice.status = (
                    InvoiceStatus.PARTIALLY_PAID
                    if invoice.balance_due < invoice.total_amount
                    else InvoiceStatus.ISSUED
                )

            await self.aging_repo.upsert_schedule(invoice.id, days_overdue, bucket)
            counts[bucket.value] += 1
            if days_overdue > 0:
                overdue_invoices += 1

        await self.session.flush()
        logger.info(
            f"Aging recalculation complete for {len(invoices)} invoices as of {target_date}. "
            f"Overdue: {overdue_invoices}, Buckets: {counts}"
        )

        return {
            "evaluated_total": len(invoices),
            "overdue_total": overdue_invoices,
            "as_of_date": str(target_date),
            "bucket_counts": counts,
        }

    async def get_aging_distribution(
        self,
        as_of_date: Optional[date] = None,
    ) -> AgingDistributionResponse:
        """
        Retrieve complete aging distribution breakdown across all 5 buckets
        including aggregate balance, count, total receivables, and DSO estimation.
        """
        # Ensure fresh calculation
        await self.recalculate_all_active_invoices(as_of_date)

        dist_data = await self.aging_repo.get_aging_distribution()
        metrics = await self.aging_repo.get_metrics_summary(as_of_date)

        bucket_summaries: Dict[str, AgingBucketSummary] = {}
        for bucket in AgingBucket:
            data = dist_data.get(bucket, {"invoice_count": 0, "total_balance": Decimal("0.00")})
            bucket_summaries[bucket.value] = AgingBucketSummary(
                bucket=bucket,
                label=BUCKET_LABELS[bucket],
                invoice_count=data["invoice_count"],
                total_balance=data["total_balance"],
            )

        return AgingDistributionResponse(
            buckets=bucket_summaries,
            total_receivables=metrics["total_receivables"],
            total_overdue=metrics["total_overdue"],
            dso_days=metrics["dso_days"],
        )

    async def get_metrics_summary(self, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Compute and return high-level operational metrics (receivables, overdue, DSO)."""
        await self.recalculate_all_active_invoices(as_of_date)
        metrics = await self.aging_repo.get_metrics_summary(as_of_date)
        metrics["as_of_date"] = as_of_date or date.today()
        return metrics
