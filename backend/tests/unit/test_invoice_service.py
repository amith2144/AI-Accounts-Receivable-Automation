import pytest
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import InvoiceStatus
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceUpdate,
)
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


@pytest.fixture
async def sample_customer(async_session: AsyncSession):
    cust_service = CustomerService(async_session)
    return await cust_service.create_customer(
        CustomerCreate(name="Beta Tech Corp", email="ap@betatech.com", payment_terms_days=30)
    )


@pytest.mark.asyncio
async def test_invoice_creation_with_line_items(async_session: AsyncSession, sample_customer):
    service = InvoiceService(async_session)

    data = InvoiceCreate(
        customer_id=sample_customer.id,
        invoice_number="INV-2026-001",
        issue_date=date(2026, 3, 1),
        due_date=date(2026, 3, 31),
        currency="USD",
        line_items=[
            InvoiceLineItemCreate(description="Consulting Hours", quantity=Decimal("10.00"), unit_price=Decimal("150.00")),
            InvoiceLineItemCreate(description="Server Setup", quantity=Decimal("1.00"), unit_price=Decimal("500.00")),
        ],
    )

    inv = await service.create_invoice(data)
    assert inv.id is not None
    assert inv.invoice_number == "INV-2026-001"
    assert inv.total_amount == Decimal("2000.00")
    assert inv.balance_due == Decimal("2000.00")
    assert inv.status == InvoiceStatus.ISSUED
    assert len(inv.line_items) == 2
    assert inv.line_items[0].line_total == Decimal("1500.00")
    assert inv.line_items[1].line_total == Decimal("500.00")


@pytest.mark.asyncio
async def test_invoice_duplicate_number_rejection(async_session: AsyncSession, sample_customer):
    service = InvoiceService(async_session)

    data = InvoiceCreate(
        customer_id=sample_customer.id,
        invoice_number="INV-DUP-01",
        issue_date=date(2026, 3, 1),
        due_date=date(2026, 3, 31),
        total_amount=Decimal("500.00"),
    )
    await service.create_invoice(data)

    with pytest.raises(ConflictError) as exc_info:
        await service.create_invoice(data)
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invoice_invalid_dates_rejection(async_session: AsyncSession, sample_customer):
    service = InvoiceService(async_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.create_invoice(
            InvoiceCreate(
                customer_id=sample_customer.id,
                invoice_number="INV-DATE-ERR",
                issue_date=date(2026, 4, 15),
                due_date=date(2026, 4, 1),  # earlier than issue date
                total_amount=Decimal("100.00"),
            )
        )
    assert "earlier than issue date" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invoice_mismatched_line_item_total_rejection(async_session: AsyncSession, sample_customer):
    service = InvoiceService(async_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.create_invoice(
            InvoiceCreate(
                customer_id=sample_customer.id,
                invoice_number="INV-MISMATCH",
                issue_date=date(2026, 3, 1),
                due_date=date(2026, 3, 31),
                total_amount=Decimal("1000.00"),  # claims 1000, items equal 200
                line_items=[
                    InvoiceLineItemCreate(description="Service", quantity=Decimal("2"), unit_price=Decimal("100.00"))
                ],
            )
        )
    assert "does not match sum of line items" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invoice_voiding_safeguards(async_session: AsyncSession, sample_customer):
    service = InvoiceService(async_session)

    inv = await service.create_invoice(
        InvoiceCreate(
            customer_id=sample_customer.id,
            invoice_number="INV-VOID-TEST",
            issue_date=date(2026, 3, 1),
            due_date=date(2026, 3, 31),
            total_amount=Decimal("750.00"),
        )
    )

    voided = await service.void_invoice(inv.id, reason="Customer cancelled contract")
    assert voided.status == InvoiceStatus.VOID
    assert voided.balance_due == Decimal("0.00")

    # Cannot void again
    with pytest.raises(ValidationError):
        await service.void_invoice(inv.id)

    # Cannot update voided invoice
    with pytest.raises(ValidationError):
        await service.update_invoice(inv.id, InvoiceUpdate(currency="EUR"))


@pytest.mark.asyncio
async def test_invoice_status_transition_rules(async_session: AsyncSession, sample_customer):
    service = InvoiceService(async_session)

    inv = await service.create_invoice(
        InvoiceCreate(
            customer_id=sample_customer.id,
            invoice_number="INV-TRANS-01",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            total_amount=Decimal("300.00"),
        )
    )

    # Overdue transition
    overdue_inv = await service.transition_status(inv.id, InvoiceStatus.OVERDUE)
    assert overdue_inv.status == InvoiceStatus.OVERDUE

    # Cannot mark as PAID when balance due is > 0
    with pytest.raises(ValidationError) as exc_info:
        await service.transition_status(inv.id, InvoiceStatus.PAID)
    assert "Cannot mark invoice as PAID while balance due" in str(exc_info.value)
