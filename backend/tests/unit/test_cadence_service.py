import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.activity import ActivityType
from app.models.base import Base
from app.models.cadence import ReminderTone
from app.models.invoice import InvoiceStatus
from app.providers.notification.memory_provider import MemoryNotificationProvider
from app.schemas.cadence import ReminderCadenceCreate, ReminderCadenceUpdate
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import InvoiceCreate
from app.services.cadence_service import CadenceService
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_cadence_crud_operations(async_session: AsyncSession):
    service = CadenceService(async_session)

    # Create cadence
    create_data = ReminderCadenceCreate(
        name="Net 30 Friendly Reminder",
        trigger_offset_days=0,
        reminder_tone=ReminderTone.FRIENDLY,
        email_subject_template="Invoice #{{ invoice_number }} is due today",
        email_body_template="Hi {{ customer_name }}, balance ${{ balance_due }} is due.",
        is_active=True,
    )
    cadence = await service.create_cadence(create_data)
    assert cadence.id is not None
    assert cadence.name == "Net 30 Friendly Reminder"

    # Get cadence
    fetched = await service.get_cadence(cadence.id)
    assert fetched.id == cadence.id

    # Update cadence
    updated = await service.update_cadence(cadence.id, ReminderCadenceUpdate(is_active=False))
    assert updated.is_active is False

    # List cadences
    cadences = await service.list_cadences()
    assert len(cadences) == 1

    # Delete cadence
    deleted = await service.delete_cadence(cadence.id)
    assert deleted is True


@pytest.mark.asyncio
async def test_cadence_evaluation_and_dispatch(async_session: AsyncSession):
    memory_provider = MemoryNotificationProvider()
    cadence_service = CadenceService(async_session, notification_provider=memory_provider)
    cust_service = CustomerService(async_session)
    inv_service = InvoiceService(async_session)

    # 1. Setup Customer A (active) and Customer B (paused)
    cust_active = await cust_service.create_customer(
        CustomerCreate(name="Acme Active", email="active@acme.com", reminder_paused=False)
    )
    cust_paused = await cust_service.create_customer(
        CustomerCreate(name="Beta Paused", email="paused@beta.com", reminder_paused=True)
    )

    # 2. Setup Invoices: due date 2026-03-01
    inv_active = await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust_active.id,
            invoice_number="INV-ACT-01",
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 3, 1),
            total_amount=Decimal("1500.00"),
        )
    )
    inv_paused = await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust_paused.id,
            invoice_number="INV-PSD-01",
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 3, 1),
            total_amount=Decimal("2000.00"),
        )
    )

    # 3. Create active cadence rule: 7 days overdue
    await cadence_service.create_cadence(
        ReminderCadenceCreate(
            name="7 Day Overdue Notice",
            trigger_offset_days=7,
            reminder_tone=ReminderTone.STANDARD,
            email_subject_template="Past Due Notice: {{ invoice_number }}",
            email_body_template="Dear {{ customer_name }}, your invoice {{ invoice_number }} for ${{ balance_due }} is overdue by {{ days_overdue }} days.",
            is_active=True,
        )
    )

    # 4. Run evaluation as of 2026-03-08 (exactly 7 days overdue)
    run_date = date(2026, 3, 8)
    summary = await cadence_service.evaluate_and_dispatch_cadences(as_of_date=run_date)

    assert summary.evaluated_cadences == 1
    assert summary.scanned_invoices == 2
    assert summary.dispatched_count == 1  # only active customer
    assert summary.skipped_paused == 1    # paused customer was skipped

    # Verify memory provider captured rendered email
    assert len(memory_provider.sent_messages) == 1
    msg = memory_provider.sent_messages[0]
    assert msg["recipient_email"] == "active@acme.com"
    assert msg["subject"] == "Past Due Notice: INV-ACT-01"
    assert "1,500.00 is overdue by 7 days" in msg["body_text"]

    # 5. Immediate rerun: Should be throttled (24-hour throttle or already dispatched)
    summary_rerun = await cadence_service.evaluate_and_dispatch_cadences(as_of_date=run_date)
    assert summary_rerun.dispatched_count == 0
    # No duplicate email sent
    assert len(memory_provider.sent_messages) == 1
