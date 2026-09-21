import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.customer_service import CustomerService


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
async def test_customer_creation_and_retrieval(async_session: AsyncSession):
    service = CustomerService(async_session)

    create_data = CustomerCreate(
        name="Acme Corporation",
        email="billing@acme.com",
        phone="+1-555-0199",
        payment_terms_days=30,
        reminder_paused=False,
    )
    customer = await service.create_customer(create_data)
    assert customer.id is not None
    assert customer.name == "Acme Corporation"
    assert customer.email == "billing@acme.com"
    assert customer.total_invoiced == 0
    assert customer.outstanding_balance == 0

    fetched = await service.get_customer(customer.id)
    assert fetched.id == customer.id
    assert fetched.name == "Acme Corporation"


@pytest.mark.asyncio
async def test_customer_duplicate_email_rejection(async_session: AsyncSession):
    service = CustomerService(async_session)

    create_data = CustomerCreate(
        name="Acme Corp",
        email="duplicate@acme.com",
    )
    await service.create_customer(create_data)

    with pytest.raises(ConflictError) as exc_info:
        await service.create_customer(
            CustomerCreate(
                name="Another Acme",
                email="DUPLICATE@acme.com",  # case-insensitive duplicate
            )
        )
    assert "already exists" in str(exc_info.value)


from pydantic import ValidationError as PydanticValidationError

@pytest.mark.asyncio
async def test_customer_validation_errors(async_session: AsyncSession):
    service = CustomerService(async_session)

    # Boundary schema validation rejection
    with pytest.raises(PydanticValidationError):
        CustomerCreate(
            name="Invalid Terms Co",
            email="terms@invalid.com",
            payment_terms_days=-5,
        )

    # Domain validation error on update
    cust = await service.create_customer(CustomerCreate(name="Terms Co", email="terms@valid.com"))
    with pytest.raises(ValidationError):
        # Passing invalid dictionary or schema bypass to service
        await service.update_customer(cust.id, CustomerUpdate.model_construct(payment_terms_days=-1))



@pytest.mark.asyncio
async def test_customer_search_and_pagination(async_session: AsyncSession):
    service = CustomerService(async_session)

    for i in range(5):
        await service.create_customer(
            CustomerCreate(
                name=f"Vendor {chr(65 + i)}",
                email=f"vendor{i}@test.com",
                phone=f"555-000{i}",
            )
        )

    # Search by name substring
    result = await service.list_customers(query="Vendor B", offset=0, limit=10)
    assert result.total == 1
    assert result.items[0].name == "Vendor B"

    # Search by email domain
    result = await service.list_customers(query="test.com", offset=0, limit=3)
    assert result.total == 5
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_customer_toggle_reminder_pause(async_session: AsyncSession):
    service = CustomerService(async_session)

    cust = await service.create_customer(
        CustomerCreate(name="Pause Test", email="pause@test.com", reminder_paused=False)
    )
    assert cust.reminder_paused is False

    updated = await service.toggle_reminder_pause(cust.id, pause=True)
    assert updated.reminder_paused is True

    updated_again = await service.toggle_reminder_pause(cust.id, pause=False)
    assert updated_again.reminder_paused is False


@pytest.mark.asyncio
async def test_customer_deletion_guard(async_session: AsyncSession):
    service = CustomerService(async_session)

    cust = await service.create_customer(
        CustomerCreate(name="Delete Protected Co", email="protected@test.com")
    )

    # Attach an active invoice directly
    inv = Invoice(
        id=uuid.uuid4(),
        customer_id=cust.id,
        invoice_number="INV-GUARD-01",
        issue_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31),
        currency="USD",
        total_amount=Decimal("1500.00"),
        balance_due=Decimal("1500.00"),
        status=InvoiceStatus.ISSUED,
    )
    async_session.add(inv)
    await async_session.flush()

    # Deletion should be blocked
    with pytest.raises(ConflictError) as exc_info:
        await service.delete_customer(cust.id)
    assert "active invoice" in str(exc_info.value)

    # If invoice is voided, deletion succeeds
    inv.status = InvoiceStatus.VOID
    inv.balance_due = Decimal("0.00")
    await async_session.flush()

    deleted = await service.delete_customer(cust.id)
    assert deleted is True

    # Confirm customer is gone
    with pytest.raises(NotFoundError):
        await service.get_customer(cust.id)
