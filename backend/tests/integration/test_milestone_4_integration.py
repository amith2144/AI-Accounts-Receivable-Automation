import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.activity import ActivityType
from app.models.aging import AgingBucket
from app.models.base import Base
from app.models.cadence import ReminderTone
from app.models.invoice import InvoiceStatus
from app.providers.notification.memory_provider import MemoryNotificationProvider
from app.schemas.cadence import ReminderCadenceCreate
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import InvoiceCreate
from app.services.activity_service import CollectionActivityService
from app.services.aging_service import AgingService
from app.services.cadence_service import CadenceService
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def milestone_4_env():
    """Sets up an integrated in-memory test database across all Milestone 4 domain services."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_milestone_4_aging_and_cadence_integration(milestone_4_env: AsyncSession):
    """
    Milestone 4 Layer Integration Verification:
    Tests the complete automated workflow across AgingService, NotificationProvider,
    CollectionActivityService, and CadenceService with duplicate throttling and pause overrides.
    """
    session = milestone_4_env

    # 1. Initialize layered domain services
    memory_notification = MemoryNotificationProvider()
    customer_service = CustomerService(session)
    invoice_service = InvoiceService(session)
    activity_service = CollectionActivityService(session)
    aging_service = AgingService(session)
    cadence_service = CadenceService(
        session=session,
        activity_service=activity_service,
        notification_provider=memory_notification,
    )

    # 2. Setup Customers: One active, one paused
    cust_active = await customer_service.create_customer(
        CustomerCreate(
            name="Vanguard Logistics",
            email="ap@vanguardlogistics.com",
            payment_terms_days=30,
            reminder_paused=False,
        )
    )
    cust_paused = await customer_service.create_customer(
        CustomerCreate(
            name="Orion Aerospace",
            email="ap@orionaero.com",
            payment_terms_days=30,
            reminder_paused=True,
        )
    )

    # 3. Setup Multi-Tier Invoices across Aging Buckets (As of 2026-04-15)
    # Target simulation date: 2026-04-15
    sim_date = date(2026, 4, 15)

    # Invoice A: Current (due 2026-04-20, not overdue)
    inv_current = await invoice_service.create_invoice(
        InvoiceCreate(
            customer_id=cust_active.id,
            invoice_number="INV-VAN-01",
            issue_date=date(2026, 3, 20),
            due_date=date(2026, 4, 20),
            total_amount=Decimal("2000.00"),
        )
    )

    # Invoice B: 15 Days Overdue (due 2026-03-31 -> 15d overdue)
    inv_15d = await invoice_service.create_invoice(
        InvoiceCreate(
            customer_id=cust_active.id,
            invoice_number="INV-VAN-02",
            issue_date=date(2026, 3, 1),
            due_date=date(2026, 3, 31),
            total_amount=Decimal("3500.00"),
        )
    )

    # Invoice C: 45 Days Overdue (due 2026-03-01 -> 45d overdue)
    inv_45d = await invoice_service.create_invoice(
        InvoiceCreate(
            customer_id=cust_active.id,
            invoice_number="INV-VAN-03",
            issue_date=date(2026, 1, 30),
            due_date=date(2026, 3, 1),
            total_amount=Decimal("4500.00"),
        )
    )

    # Invoice D: Paused Customer Invoice (due 2026-03-31 -> 15d overdue)
    inv_paused = await invoice_service.create_invoice(
        InvoiceCreate(
            customer_id=cust_paused.id,
            invoice_number="INV-ORI-01",
            issue_date=date(2026, 3, 1),
            due_date=date(2026, 3, 31),
            total_amount=Decimal("6000.00"),
        )
    )

    # 4. Execute Aging Evaluation Batch
    aging_batch = await aging_service.recalculate_all_active_invoices(as_of_date=sim_date)
    assert aging_batch["evaluated_total"] == 4
    assert aging_batch["overdue_total"] == 3

    # Verify invoice status transition to OVERDUE
    reloaded_inv_15d = await invoice_service.get_invoice(inv_15d.id)
    assert reloaded_inv_15d.status == InvoiceStatus.OVERDUE

    reloaded_inv_current = await invoice_service.get_invoice(inv_current.id)
    assert reloaded_inv_current.status == InvoiceStatus.ISSUED

    # 5. Verify Aging Distribution Aggregation
    dist = await aging_service.get_aging_distribution(as_of_date=sim_date)
    assert dist.total_receivables == Decimal("16000.00")  # 2000 + 3500 + 4500 + 6000
    assert dist.total_overdue == Decimal("14000.00")      # 3500 + 4500 + 6000
    assert dist.buckets[AgingBucket.CURRENT.value].invoice_count == 1
    assert dist.buckets[AgingBucket.DAYS_1_30.value].invoice_count == 2
    assert dist.buckets[AgingBucket.DAYS_31_60.value].invoice_count == 1

    # 6. Configure Cadence Rules
    # Rule 1: Net 15 Overdue Notice
    rule_15 = await cadence_service.create_cadence(
        ReminderCadenceCreate(
            name="15-Day Overdue Outreach",
            trigger_offset_days=15,
            reminder_tone=ReminderTone.FIRM,
            email_subject_template="Past Due Reminder: Invoice {{ invoice_number }}",
            email_body_template="Dear {{ customer_name }}, invoice {{ invoice_number }} of ${{ balance_due }} is overdue by {{ days_overdue }} days.",
            is_active=True,
        )
    )

    # Rule 2: 45-Day Urgent Escalation
    rule_45 = await cadence_service.create_cadence(
        ReminderCadenceCreate(
            name="45-Day Urgent Escalation",
            trigger_offset_days=45,
            reminder_tone=ReminderTone.URGENT,
            email_subject_template="URGENT: Outstanding Balance on {{ invoice_number }}",
            email_body_template="FINAL NOTICE: {{ customer_name }}, balance ${{ balance_due }} must be paid immediately.",
            is_active=True,
        )
    )

    # 7. Execute Automated Cadence Evaluation
    dispatch_summary = await cadence_service.evaluate_and_dispatch_cadences(as_of_date=sim_date)

    assert dispatch_summary.evaluated_cadences == 2
    assert dispatch_summary.scanned_invoices == 4
    # Expected dispatches:
    # - Rule 15 matches inv_15d (Vanguard) -> Dispatched
    # - Rule 15 matches inv_paused (Orion) -> Skipped (Paused)
    # - Rule 45 matches inv_45d (Vanguard) -> Dispatched
    assert dispatch_summary.dispatched_count == 2
    assert dispatch_summary.skipped_paused >= 1

    # 8. Assert Notifications Delivered via Provider
    assert len(memory_notification.sent_messages) == 2
    recipients = [m["recipient_email"] for m in memory_notification.sent_messages]
    assert recipients == ["ap@vanguardlogistics.com", "ap@vanguardlogistics.com"]

    subjects = [m["subject"] for m in memory_notification.sent_messages]
    assert "Past Due Reminder: Invoice INV-VAN-02" in subjects
    assert "URGENT: Outstanding Balance on INV-VAN-03" in subjects

    # 9. Verify Audit Trail in CollectionActivity
    inv_15_activities = await activity_service.get_invoice_activities(inv_15d.id)
    assert inv_15_activities.total >= 1
    assert inv_15_activities.items[0].activity_type == ActivityType.REMINDER_SENT
    assert inv_15_activities.items[0].details["cadence_id"] == str(rule_15.id)

    # 10. Verify Duplicate Throttling on Immediate Rerun
    rerun_summary = await cadence_service.evaluate_and_dispatch_cadences(as_of_date=sim_date)
    assert rerun_summary.dispatched_count == 0
    # Notification provider has received no new messages
    assert len(memory_notification.sent_messages) == 2
