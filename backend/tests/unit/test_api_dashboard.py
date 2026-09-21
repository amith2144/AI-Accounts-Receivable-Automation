import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_async_db, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.activity import ActivityType, CollectionActivity
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus


@pytest.fixture
async def dashboard_test_env():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_db():
        async with test_session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_async_db] = override_db
    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, test_session_maker

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
def auth_headers():
    token = create_access_token("operator", role="OPERATOR")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_dashboard_api_endpoints(dashboard_test_env, auth_headers: dict):
    client, session_maker = dashboard_test_env

    # 1. Seed customer and 3 invoices
    customer_id = uuid.uuid4()
    inv_current_id = uuid.uuid4()
    inv_overdue_1_30 = uuid.uuid4()
    inv_overdue_31_60 = uuid.uuid4()

    today = date.today()

    async with session_maker() as session:
        cust = Customer(
            id=customer_id,
            name="Cyberdyne Systems",
            email="billing@cyberdyne.com",
            payment_terms_days=30,
        )
        session.add(cust)

        # Invoice 1: Current (due in 10 days) -> $1000
        inv1 = Invoice(
            id=inv_current_id,
            customer_id=customer_id,
            invoice_number="INV-CBD-001",
            issue_date=today - timedelta(days=20),
            due_date=today + timedelta(days=10),
            currency="USD",
            total_amount=Decimal("1000.00"),
            balance_due=Decimal("1000.00"),
            status=InvoiceStatus.ISSUED,
        )
        # Invoice 2: 15 days overdue -> $2000
        inv2 = Invoice(
            id=inv_overdue_1_30,
            customer_id=customer_id,
            invoice_number="INV-CBD-002",
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=15),
            currency="USD",
            total_amount=Decimal("2000.00"),
            balance_due=Decimal("2000.00"),
            status=InvoiceStatus.ISSUED,
        )
        # Invoice 3: 45 days overdue -> $3000
        inv3 = Invoice(
            id=inv_overdue_31_60,
            customer_id=customer_id,
            invoice_number="INV-CBD-003",
            issue_date=today - timedelta(days=75),
            due_date=today - timedelta(days=45),
            currency="USD",
            total_amount=Decimal("3000.00"),
            balance_due=Decimal("3000.00"),
            status=InvoiceStatus.ISSUED,
        )
        session.add_all([inv1, inv2, inv3])

        # Seed collection activity
        act = CollectionActivity(
            id=uuid.uuid4(),
            invoice_id=inv_overdue_1_30,
            customer_id=customer_id,
            activity_type=ActivityType.REMINDER_SENT,
            performed_by="SYSTEM_AUTOMATION",
            details={"template": "Standard Notice", "offset_days": 15},
        )
        session.add(act)
        await session.commit()

    # 2. Test GET /api/v1/dashboard/metrics
    metrics_resp = await client.get("/api/v1/dashboard/metrics", headers=auth_headers)
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert Decimal(str(metrics["total_receivables"])) == Decimal("6000.00")
    assert Decimal(str(metrics["total_overdue"])) == Decimal("5000.00")
    assert metrics["dso_days"] > 0.0

    # 3. Test GET /api/v1/dashboard/aging
    aging_resp = await client.get("/api/v1/dashboard/aging", headers=auth_headers)
    assert aging_resp.status_code == 200
    aging_data = aging_resp.json()
    buckets = aging_data["buckets"]
    assert "CURRENT" in buckets
    assert "DAYS_1_30" in buckets
    assert "DAYS_31_60" in buckets
    assert buckets["CURRENT"]["invoice_count"] == 1
    assert Decimal(str(buckets["CURRENT"]["total_balance"])) == Decimal("1000.00")
    assert buckets["DAYS_1_30"]["invoice_count"] == 1
    assert Decimal(str(buckets["DAYS_1_30"]["total_balance"])) == Decimal("2000.00")
    assert buckets["DAYS_31_60"]["invoice_count"] == 1
    assert Decimal(str(buckets["DAYS_31_60"]["total_balance"])) == Decimal("3000.00")

    # 4. Test GET /api/v1/dashboard/recent-activity
    act_resp = await client.get("/api/v1/dashboard/recent-activity?limit=10", headers=auth_headers)
    assert act_resp.status_code == 200
    act_data = act_resp.json()
    assert act_data["total"] >= 1
    assert act_data["items"][0]["activity_type"] == "REMINDER_SENT"

    # 5. Unauthenticated rejection
    unauth = await client.get("/api/v1/dashboard/metrics")
    assert unauth.status_code == 401
