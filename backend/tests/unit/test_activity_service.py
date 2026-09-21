import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.activity import ActivityType
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.services.activity_service import CollectionActivityService


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
async def test_log_and_query_collection_activity(async_session: AsyncSession):
    service = CollectionActivityService(async_session)

    invoice_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    # 1. Log manual note
    act1 = await service.log_activity(
        invoice_id=invoice_id,
        customer_id=customer_id,
        activity_type=ActivityType.MANUAL_NOTE,
        performed_by="CLERK_ALICE",
        details={"note": "Customer promised check by Friday."},
    )
    assert act1.id is not None
    assert act1.activity_type == ActivityType.MANUAL_NOTE
    assert act1.details["note"] == "Customer promised check by Friday."

    # 2. Log reminder sent
    act2 = await service.log_activity(
        invoice_id=invoice_id,
        customer_id=customer_id,
        activity_type=ActivityType.REMINDER_SENT,
        performed_by="SYSTEM_AUTOMATION",
        details={"recipient": "billing@customer.com", "cadence_name": "Net 30 Overdue"},
    )
    assert act2.activity_type == ActivityType.REMINDER_SENT

    # 3. Query invoice activities
    inv_history = await service.get_invoice_activities(invoice_id)
    assert inv_history.total == 2
    types = [item.activity_type for item in inv_history.items]
    assert ActivityType.REMINDER_SENT in types
    assert ActivityType.MANUAL_NOTE in types

    # 4. Query customer activities
    cust_history = await service.get_customer_activities(customer_id)
    assert cust_history.total == 2

    # 5. Query recent activities with type filter
    recent_notes = await service.get_recent_activities(activity_type=ActivityType.MANUAL_NOTE)
    assert recent_notes.total == 1
    assert recent_notes.items[0].performed_by == "CLERK_ALICE"


@pytest.mark.asyncio
async def test_has_recent_reminder_sent_throttling(async_session: AsyncSession):
    service = CollectionActivityService(async_session)

    invoice_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    # Initially false
    has_recent = await service.has_recent_reminder_sent(invoice_id, hours=24)
    assert has_recent is False

    # Log reminder activity
    await service.log_activity(
        invoice_id=invoice_id,
        customer_id=customer_id,
        activity_type=ActivityType.REMINDER_SENT,
        performed_by="SYSTEM_AUTOMATION",
        details={"recipient": "billing@customer.com"},
    )

    # Now true
    has_recent_after = await service.has_recent_reminder_sent(invoice_id, hours=24)
    assert has_recent_after is True
