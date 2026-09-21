import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.aging import AgingBucket
from app.models.base import Base
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import InvoiceCreate
from app.services.aging_service import AgingService
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
async def test_classify_bucket_logic():
    assert AgingService.classify_bucket(-5) == (0, AgingBucket.CURRENT)
    assert AgingService.classify_bucket(0) == (0, AgingBucket.CURRENT)
    assert AgingService.classify_bucket(15) == (15, AgingBucket.DAYS_1_30)
    assert AgingService.classify_bucket(45) == (45, AgingBucket.DAYS_31_60)
    assert AgingService.classify_bucket(75) == (75, AgingBucket.DAYS_61_90)
    assert AgingService.classify_bucket(120) == (120, AgingBucket.DAYS_90_PLUS)


@pytest.mark.asyncio
async def test_invoice_aging_calculation_and_overdue_promotion(async_session: AsyncSession):
    cust_service = CustomerService(async_session)
    cust = await cust_service.create_customer(
        CustomerCreate(name="Aging Debtor", email="aging@debtor.com")
    )

    inv_service = InvoiceService(async_session)
    invoice = await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust.id,
            invoice_number="INV-AGING-01",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            total_amount=Decimal("1000.00"),
        )
    )

    aging_service = AgingService(async_session)

    # 1. As of due date -> CURRENT
    schedule_current = await aging_service.calculate_invoice_aging(invoice.id, as_of_date=date(2026, 1, 31))
    assert schedule_current.bucket == AgingBucket.CURRENT
    assert schedule_current.days_overdue == 0

    # 2. As of 15 days later -> DAYS_1_30, invoice status becomes OVERDUE
    schedule_15 = await aging_service.calculate_invoice_aging(invoice.id, as_of_date=date(2026, 2, 15))
    assert schedule_15.bucket == AgingBucket.DAYS_1_30
    assert schedule_15.days_overdue == 15

    reloaded = await inv_service.get_invoice(invoice.id)
    assert reloaded.status == InvoiceStatus.OVERDUE

    # 3. As of 100 days later -> DAYS_90_PLUS
    schedule_100 = await aging_service.calculate_invoice_aging(invoice.id, as_of_date=date(2026, 5, 11))
    assert schedule_100.bucket == AgingBucket.DAYS_90_PLUS
    assert schedule_100.days_overdue == 100


@pytest.mark.asyncio
async def test_aging_distribution_and_dso_calculation(async_session: AsyncSession):
    cust_service = CustomerService(async_session)
    cust = await cust_service.create_customer(
        CustomerCreate(name="Distribution Debtor", email="dist@debtor.com")
    )

    inv_service = InvoiceService(async_session)

    # Invoice 1: Current ($500)
    await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust.id,
            invoice_number="INV-DIST-CURRENT",
            issue_date=date(2026, 3, 1),
            due_date=date(2026, 3, 31),
            total_amount=Decimal("500.00"),
        )
    )

    # Invoice 2: 15 days overdue ($1200)
    await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust.id,
            invoice_number="INV-DIST-30",
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 3, 1),
            total_amount=Decimal("1200.00"),
        )
    )

    # Invoice 3: 40 days overdue ($800)
    await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust.id,
            invoice_number="INV-DIST-60",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 2, 4),
            total_amount=Decimal("800.00"),
        )
    )

    aging_service = AgingService(async_session)
    target_date = date(2026, 3, 16)

    dist = await aging_service.get_aging_distribution(as_of_date=target_date)

    # Total receivables = 500 + 1200 + 800 = 2500
    assert dist.total_receivables == Decimal("2500.00")
    # Total overdue = 1200 + 800 = 2000
    assert dist.total_overdue == Decimal("2000.00")

    # Bucket verification
    assert dist.buckets[AgingBucket.CURRENT.value].invoice_count == 1
    assert dist.buckets[AgingBucket.CURRENT.value].total_balance == Decimal("500.00")

    assert dist.buckets[AgingBucket.DAYS_1_30.value].invoice_count == 1
    assert dist.buckets[AgingBucket.DAYS_1_30.value].total_balance == Decimal("1200.00")

    assert dist.buckets[AgingBucket.DAYS_31_60.value].invoice_count == 1
    assert dist.buckets[AgingBucket.DAYS_31_60.value].total_balance == Decimal("800.00")

    # DSO verification: (2500 / 2500) * 90 = 90.0
    assert dist.dso_days == 90.0
