import logging
import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.activity import ActivityType
from app.models.cadence import ReminderCadence
from app.models.invoice import Invoice, InvoiceStatus
from app.providers.notification import NotificationProvider, get_notification_provider
from app.repositories.activity_repo import ActivityRepository
from app.repositories.cadence_repo import CadenceRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.schemas.cadence import (
    CadenceDispatchSummary,
    ReminderCadenceCreate,
    ReminderCadenceResponse,
    ReminderCadenceUpdate,
)
from app.services.activity_service import CollectionActivityService

logger = logging.getLogger("app.services.cadence")


class CadenceService:
    """
    Domain service governing automated payment reminder cadences,
    overdue rule evaluation, duplicate communication throttling,
    and Jinja2-rendered email dispatch. Enforces Rule 02, Rule 03, and Rule 05.
    """

    def __init__(
        self,
        session: AsyncSession,
        cadence_repo: Optional[CadenceRepository] = None,
        invoice_repo: Optional[InvoiceRepository] = None,
        activity_service: Optional[CollectionActivityService] = None,
        activity_repo: Optional[ActivityRepository] = None,
        notification_provider: Optional[NotificationProvider] = None,
    ):
        self.session = session
        self.cadence_repo = cadence_repo or CadenceRepository(session)
        self.invoice_repo = invoice_repo or InvoiceRepository(session)
        self.activity_repo = activity_repo or ActivityRepository(session)
        self.activity_service = activity_service or CollectionActivityService(session, self.activity_repo)
        self.notification_provider = notification_provider or get_notification_provider()

    async def create_cadence(self, data: ReminderCadenceCreate) -> ReminderCadenceResponse:
        """Create a new automated reminder rule and email template."""
        cadence = ReminderCadence(
            id=uuid.uuid4(),
            name=data.name.strip(),
            trigger_offset_days=data.trigger_offset_days,
            reminder_tone=data.reminder_tone,
            email_subject_template=data.email_subject_template.strip(),
            email_body_template=data.email_body_template.strip(),
            is_active=data.is_active,
        )
        self.session.add(cadence)
        await self.session.flush()
        await self.session.refresh(cadence)
        logger.info(f"Created cadence rule '{cadence.name}' (offset: {cadence.trigger_offset_days}d)")
        return ReminderCadenceResponse.model_validate(cadence)

    async def get_cadence(self, cadence_id: uuid.UUID) -> ReminderCadenceResponse:
        """Retrieve cadence rule by ID."""
        cadence = await self.cadence_repo.get(cadence_id)
        if not cadence:
            raise NotFoundError(f"ReminderCadence with ID {cadence_id} not found.")
        return ReminderCadenceResponse.model_validate(cadence)

    async def list_cadences(self) -> List[ReminderCadenceResponse]:
        """List all reminder cadences ordered by trigger schedule."""
        records = await self.cadence_repo.get_multi(limit=100)
        return [ReminderCadenceResponse.model_validate(r) for r in records]

    async def update_cadence(
        self,
        cadence_id: uuid.UUID,
        data: ReminderCadenceUpdate,
    ) -> ReminderCadenceResponse:
        """Update cadence rule parameters or templates."""
        cadence = await self.cadence_repo.get(cadence_id)
        if not cadence:
            raise NotFoundError(f"ReminderCadence with ID {cadence_id} not found.")

        update_dict = data.model_dump(exclude_unset=True)
        updated = await self.cadence_repo.update(cadence, update_dict)
        return ReminderCadenceResponse.model_validate(updated)

    async def delete_cadence(self, cadence_id: uuid.UUID) -> bool:
        """Delete a reminder cadence rule."""
        deleted = await self.cadence_repo.delete(cadence_id)
        if not deleted:
            raise NotFoundError(f"ReminderCadence with ID {cadence_id} not found.")
        return True

    async def evaluate_and_dispatch_cadences(
        self,
        as_of_date: Optional[date] = None,
        dry_run: bool = False,
    ) -> CadenceDispatchSummary:
        """
        Evaluate all active cadence rules against active unpaid invoices,
        enforce customer pause overrides and 24-hour duplicate throttling,
        render Jinja2 templates, and dispatch notifications.
        """
        target_date = as_of_date or date.today()
        cadences = await self.cadence_repo.get_active_cadences()

        # Query all active, unpaid invoices with customer relationship loaded
        stmt = (
            select(Invoice)
            .where(Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.VOID]))
            .options(selectinload(Invoice.customer))
        )
        res = await self.session.execute(stmt)
        invoices = res.scalars().all()

        summary = CadenceDispatchSummary(
            evaluated_cadences=len(cadences),
            scanned_invoices=len(invoices),
        )

        # Sort cadences in descending order of trigger offset days so that for any given invoice,
        # the most specific / urgent overdue cadence is evaluated first.
        sorted_cadences = sorted(cadences, key=lambda c: c.trigger_offset_days, reverse=True)

        for cadence in sorted_cadences:
            for invoice in invoices:
                days_diff = (target_date - invoice.due_date).days

                # Rule criteria: Trigger when invoice has reached or passed the rule's offset
                if days_diff < cadence.trigger_offset_days:
                    continue

                # 1. Customer Pause Check: Honor master communication suspension
                if invoice.customer.reminder_paused:
                    summary.skipped_paused += 1
                    logger.debug(
                        f"Skipping reminder for invoice {invoice.invoice_number}: "
                        f"Customer {invoice.customer.name} reminders paused."
                    )
                    continue

                # 2. Duplicate Rule Check: Do not fire the same cadence rule twice for an invoice
                already_fired = await self.activity_repo.has_dispatched_cadence(invoice.id, cadence.id)
                if already_fired:
                    continue

                # 3. Throttling Check: Maximum 1 collection reminder per invoice in 24 hours
                recently_sent = await self.activity_service.has_recent_reminder_sent(invoice.id, hours=24)
                if recently_sent:
                    summary.throttled_count += 1
                    logger.debug(
                        f"Throttling reminder for invoice {invoice.invoice_number}: "
                        "A reminder was already dispatched in the last 24 hours."
                    )
                    continue

                # 4. Context Preparation & Template Rendering
                context = {
                    "customer_name": invoice.customer.name,
                    "customer_email": invoice.customer.email,
                    "invoice_number": invoice.invoice_number,
                    "total_amount": f"{invoice.total_amount:,.2f}",
                    "balance_due": f"{invoice.balance_due:,.2f}",
                    "issue_date": str(invoice.issue_date),
                    "due_date": str(invoice.due_date),
                    "days_overdue": max(0, days_diff),
                    "tone": cadence.reminder_tone.value,
                }

                try:
                    subject = self.notification_provider.render_template(cadence.email_subject_template, context)
                    body = self.notification_provider.render_template(cadence.email_body_template, context)
                except Exception as exc:
                    err = f"Template rendering failed for cadence {cadence.name}: {str(exc)}"
                    logger.error(err)
                    summary.errors.append(err)
                    continue

                # 5. Dispatch Notification
                if not dry_run:
                    dispatch_result = self.notification_provider.send_email(
                        recipient_email=invoice.customer.email,
                        recipient_name=invoice.customer.name,
                        subject=subject,
                        body_text=body,
                        metadata={"invoice_id": str(invoice.id), "cadence_id": str(cadence.id)},
                    )

                    if dispatch_result.success:
                        summary.dispatched_count += 1
                        # Append immutable audit activity
                        await self.activity_service.log_activity(
                            invoice_id=invoice.id,
                            customer_id=invoice.customer_id,
                            activity_type=ActivityType.REMINDER_SENT,
                            performed_by="SYSTEM_AUTOMATION",
                            details={
                                "cadence_id": str(cadence.id),
                                "cadence_name": cadence.name,
                                "trigger_offset_days": cadence.trigger_offset_days,
                                "recipient": invoice.customer.email,
                                "subject": subject,
                                "message_id": dispatch_result.message_id,
                            },
                        )
                    else:
                        err_msg = (
                            f"Notification dispatch failed for invoice {invoice.invoice_number} "
                            f"to {invoice.customer.email}: {dispatch_result.error_message}"
                        )
                        logger.error(err_msg)
                        summary.errors.append(err_msg)
                else:
                    # Dry run mode increments dispatched count without transmitting email
                    summary.dispatched_count += 1

        await self.session.flush()
        logger.info(
            f"Cadence run complete: evaluated {summary.evaluated_cadences} rules on "
            f"{summary.scanned_invoices} invoices -> {summary.dispatched_count} dispatched, "
            f"{summary.skipped_paused} paused, {summary.throttled_count} throttled."
        )

        return summary
