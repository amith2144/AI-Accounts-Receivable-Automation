import pytest
import uuid
from datetime import date
from decimal import Decimal
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.database.session import get_async_db
from app.main import app
from app.models import (
    ActivityType,
    AgingBucket,
    AgingSchedule,
    Base,
    CollectionActivity,
    Customer,
    DocumentSource,
    ExtractionStatus,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    PaymentMethod,
    PaymentRecord,
    ReminderCadence,
    ReminderTone,
)
from app.repositories.base import BaseRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def milestone_test_env():
    """Sets up an integrated in-memory SQLite database across all 8 models."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_milestone_1_full_integrated_layer(milestone_test_env: AsyncSession):
    """
    Milestone 1 Layer Integration Verification:
    Tests relational persistence across all 8 core entities, repository abstraction,
    and foreign key constraints in a single unified workflow.
    """
    session = milestone_test_env

    customer_repo = BaseRepository(Customer, session)
    invoice_repo = BaseRepository(Invoice, session)
    item_repo = BaseRepository(InvoiceLineItem, session)
    payment_repo = BaseRepository(PaymentRecord, session)
    aging_repo = BaseRepository(AgingSchedule, session)
    activity_repo = BaseRepository(CollectionActivity, session)
    cadence_repo = BaseRepository(ReminderCadence, session)
    document_repo = BaseRepository(DocumentSource, session)

    # 1. Staged Document Source
    doc = await document_repo.create({
        "original_filename": "inv_2026_09_001.pdf",
        "storage_path": "s3://ar-documents/2026/09/inv_2026_09_001.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1048576,
        "extraction_status": ExtractionStatus.SUCCESS,
        "details_data": {"detected_total": "2500.00"},
    })
    assert doc.id is not None

    # 2. Customer
    customer = await customer_repo.create({
        "name": "Global Enterprise Logistics",
        "email": "ap@globalenterprise.com",
        "phone": "+1-800-555-0144",
        "payment_terms_days": 30,
        "reminder_paused": False,
    })
    assert customer.id is not None

    # 3. Invoice
    invoice = await invoice_repo.create({
        "customer_id": customer.id,
        "invoice_number": "INV-2026-901",
        "issue_date": date(2026, 9, 1),
        "due_date": date(2026, 10, 1),
        "currency": "USD",
        "total_amount": Decimal("2500.00"),
        "balance_due": Decimal("2500.00"),
        "status": InvoiceStatus.ISSUED,
        "document_source_id": doc.id,
    })
    assert invoice.id is not None

    # 4. Line Items
    item1 = await item_repo.create({
        "invoice_id": invoice.id,
        "description": "Freight logistics service - Zone A",
        "quantity": Decimal("2.00"),
        "unit_price": Decimal("1000.00"),
        "line_total": Decimal("2000.00"),
    })
    item2 = await item_repo.create({
        "invoice_id": invoice.id,
        "description": "Handling and fuel surcharge",
        "quantity": Decimal("1.00"),
        "unit_price": Decimal("500.00"),
        "line_total": Decimal("500.00"),
    })
    assert (item1.line_total + item2.line_total) == Decimal("2500.00")

    # 5. Payment Record & Balance Update
    payment = await payment_repo.create({
        "invoice_id": invoice.id,
        "amount": Decimal("1000.00"),
        "payment_date": date(2026, 9, 15),
        "payment_method": PaymentMethod.WIRE,
        "reference_number": "WIRE-REF-88392",
        "notes": "Partial wire received",
    })
    assert payment.id is not None

    # Update invoice balance and status
    new_balance = invoice.total_amount - payment.amount
    invoice = await invoice_repo.update(invoice, {
        "balance_due": new_balance,
        "status": InvoiceStatus.PARTIALLY_PAID,
    })
    assert invoice.balance_due == Decimal("1500.00")
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID

    # 6. Aging Schedule
    aging = await aging_repo.create({
        "invoice_id": invoice.id,
        "days_overdue": 0,
        "bucket": AgingBucket.CURRENT,
    })
    assert aging.bucket == AgingBucket.CURRENT

    # 7. Collection Activity Log
    activity = await activity_repo.create({
        "invoice_id": invoice.id,
        "customer_id": customer.id,
        "activity_type": ActivityType.PAYMENT_APPLIED,
        "performed_by": "SYSTEM_AUTOMATION",
        "details": {"amount_paid": "1000.00", "remaining_balance": "1500.00"},
    })
    assert activity.activity_type == ActivityType.PAYMENT_APPLIED

    # 8. Reminder Cadence Rule
    cadence = await cadence_repo.create({
        "name": "Standard Net 30 Post-Due Notice",
        "trigger_offset_days": 7,
        "reminder_tone": ReminderTone.STANDARD,
        "email_subject_template": "Notice of overdue balance for Invoice {{invoice_number}}",
        "email_body_template": "Dear {{customer_name}}, balance of {{balance_due}} is overdue.",
        "is_active": True,
    })
    assert cadence.trigger_offset_days == 7

    # Verify counts across all repositories
    assert await customer_repo.count() == 1
    assert await invoice_repo.count() == 1
    assert await item_repo.count() == 2
    assert await payment_repo.count() == 1
    assert await aging_repo.count() == 1
    assert await activity_repo.count() == 1
    assert await cadence_repo.count() == 1
    assert await document_repo.count() == 1
