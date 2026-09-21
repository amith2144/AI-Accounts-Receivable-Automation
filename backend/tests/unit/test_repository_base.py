import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.base import Base
from app.models.customer import Customer
from app.repositories.base import BaseRepository


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
async def test_repository_crud_operations(async_session: AsyncSession):
    repo = BaseRepository(Customer, async_session)

    # 1. Test Create
    customer_data = {
        "name": "Acme Industrial Corp",
        "email": "billing@acmeindustrial.com",
        "phone": "+1-555-0199",
        "payment_terms_days": 30,
        "reminder_paused": False,
    }
    customer = await repo.create(customer_data)
    assert customer.id is not None
    assert customer.name == "Acme Industrial Corp"
    assert customer.email == "billing@acmeindustrial.com"

    # 2. Test Get
    fetched = await repo.get(customer.id)
    assert fetched is not None
    assert fetched.id == customer.id
    assert fetched.name == "Acme Industrial Corp"

    # 3. Test Count
    count = await repo.count()
    assert count == 1

    # 4. Test Update
    updated = await repo.update(fetched, {"name": "Acme Global Solutions", "payment_terms_days": 45})
    assert updated.name == "Acme Global Solutions"
    assert updated.payment_terms_days == 45

    # 5. Test Get Multi
    # Create second customer
    await repo.create({
        "name": "Beta Logistics",
        "email": "ap@betalogistics.com",
        "payment_terms_days": 15,
    })
    customers = await repo.get_multi(offset=0, limit=10)
    assert len(customers) == 2

    # 6. Test Delete
    deleted = await repo.delete(customer.id)
    assert deleted is True

    # Confirm deletion
    re_fetch = await repo.get(customer.id)
    assert re_fetch is None

    # Count after deletion
    remaining_count = await repo.count()
    assert remaining_count == 1
