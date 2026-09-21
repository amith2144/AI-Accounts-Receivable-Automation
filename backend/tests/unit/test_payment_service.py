import pytest
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import NotFoundError, ValidationError
from app.models.base import Base
from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentMethod
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import InvoiceCreate
from app.schemas.payment import PaymentCreate
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService


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


@pytest.fixture
async def sample_invoice(async_session: AsyncSession):
    cust_service = CustomerService(async_session)
    cust = await cust_service.create_customer(
        CustomerCreate(name="Delta Logistics", email="remittance@delta.com")
    )

    inv_service = InvoiceService(async_session)
    return await inv_service.create_invoice(
        InvoiceCreate(
            customer_id=cust.id,
            invoice_number="INV-DELTA-100",
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 2, 28),
            total_amount=Decimal("1000.00"),
        )
    )


@pytest.mark.asyncio
async def test_partial_and_full_payment_flow(async_session: AsyncSession, sample_invoice):
    payment_service = PaymentService(async_session)
    invoice_service = InvoiceService(async_session)

    # 1. First partial payment: $400.00
    res1 = await payment_service.record_payment(
        PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal("400.00"),
            payment_date=date(2026, 2, 10),
            payment_method=PaymentMethod.ACH,
            reference_number="ACH-889900",
        )
    )
    assert res1.invoice_status == InvoiceStatus.PARTIALLY_PAID
    assert res1.remaining_balance == Decimal("600.00")
    assert res1.payment.amount == Decimal("400.00")

    # Verify invoice state
    inv_check = await invoice_service.get_invoice(sample_invoice.id)
    assert inv_check.status == InvoiceStatus.PARTIALLY_PAID
    assert inv_check.balance_due == Decimal("600.00")

    # 2. Second payment settling the rest: $600.00
    res2 = await payment_service.record_payment(
        PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal("600.00"),
            payment_date=date(2026, 2, 15),
            payment_method=PaymentMethod.WIRE,
            reference_number="WIRE-12345",
        )
    )
    assert res2.invoice_status == InvoiceStatus.PAID
    assert res2.remaining_balance == Decimal("0.00")

    # Verify final invoice state
    inv_final = await invoice_service.get_invoice(sample_invoice.id)
    assert inv_final.status == InvoiceStatus.PAID
    assert inv_final.balance_due == Decimal("0.00")

    # 3. Verify payment history list
    history = await payment_service.list_payments_for_invoice(sample_invoice.id)
    assert history.total == 2
    assert history.items[0].amount == Decimal("600.00")
    assert history.items[1].amount == Decimal("400.00")


@pytest.mark.asyncio
async def test_overpayment_rejection(async_session: AsyncSession, sample_invoice):
    payment_service = PaymentService(async_session)

    # Attempting to pay $1000.01 on a $1000.00 invoice
    with pytest.raises(ValidationError) as exc_info:
        await payment_service.record_payment(
            PaymentCreate(
                invoice_id=sample_invoice.id,
                amount=Decimal("1000.01"),
                payment_date=date(2026, 2, 10),
                payment_method=PaymentMethod.CHECK,
            )
        )
    assert "exceeds outstanding balance due" in str(exc_info.value)


@pytest.mark.asyncio
async def test_payment_on_paid_invoice_rejection(async_session: AsyncSession, sample_invoice):
    payment_service = PaymentService(async_session)

    # Pay in full
    await payment_service.record_payment(
        PaymentCreate(
            invoice_id=sample_invoice.id,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 2, 10),
            payment_method=PaymentMethod.ACH,
        )
    )

    # Attempt additional payment
    with pytest.raises(ValidationError) as exc_info:
        await payment_service.record_payment(
            PaymentCreate(
                invoice_id=sample_invoice.id,
                amount=Decimal("50.00"),
                payment_date=date(2026, 2, 12),
                payment_method=PaymentMethod.ACH,
            )
        )
    assert "already fully paid" in str(exc_info.value)


@pytest.mark.asyncio
async def test_payment_on_voided_invoice_rejection(async_session: AsyncSession, sample_invoice):
    inv_service = InvoiceService(async_session)
    payment_service = PaymentService(async_session)

    await inv_service.void_invoice(sample_invoice.id, reason="Testing payment rejection on void")

    with pytest.raises(ValidationError) as exc_info:
        await payment_service.record_payment(
            PaymentCreate(
                invoice_id=sample_invoice.id,
                amount=Decimal("100.00"),
                payment_date=date(2026, 2, 10),
                payment_method=PaymentMethod.CREDIT_CARD,
            )
        )
    assert "Cannot apply payment to voided invoice" in str(exc_info.value)
