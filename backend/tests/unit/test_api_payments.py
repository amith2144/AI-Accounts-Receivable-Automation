import uuid
from datetime import date
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_async_db, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus


@pytest.fixture
async def payment_test_env():
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
async def test_payment_api_lifecycle(payment_test_env, auth_headers: dict):
    client, session_maker = payment_test_env

    # 1. Seed customer and active invoice
    customer_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    async with session_maker() as session:
        cust = Customer(
            id=customer_id,
            name="Apex Dynamics",
            email="billing@apexdynamics.com",
            payment_terms_days=30,
        )
        session.add(cust)
        inv = Invoice(
            id=invoice_id,
            customer_id=customer_id,
            invoice_number="INV-APEX-001",
            issue_date=date.today(),
            due_date=date.today(),
            currency="USD",
            total_amount=Decimal("1000.00"),
            balance_due=Decimal("1000.00"),
            status=InvoiceStatus.ISSUED,
        )
        session.add(inv)
        await session.commit()

    # 2. Unauthenticated payment attempt -> 401
    unauth = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "100.00", "payment_date": str(date.today()), "payment_method": "ACH"},
    )
    assert unauth.status_code == 401

    # 3. Partial payment ($400.00)
    pay_payload = {
        "amount": "400.00",
        "payment_date": str(date.today()),
        "payment_method": "ACH",
        "reference_number": "ACH-TXN-101",
        "notes": "Partial milestone 1 payment",
    }
    pay_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json=pay_payload,
        headers=auth_headers,
    )
    assert pay_resp.status_code == 201
    res = pay_resp.json()
    assert Decimal(str(res["remaining_balance"])) == Decimal("600.00")
    assert res["invoice_status"] == "PARTIALLY_PAID"
    assert res["payment"]["reference_number"] == "ACH-TXN-101"

    # 4. List payments for invoice
    list_resp = await client.get(f"/api/v1/invoices/{invoice_id}/payments", headers=auth_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert Decimal(str(list_data["items"][0]["amount"])) == Decimal("400.00")

    # 5. Overpayment rejection (attempting to pay $700.00 when balance is $600.00) -> 422
    over_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "700.00", "payment_date": str(date.today()), "payment_method": "WIRE"},
        headers=auth_headers,
    )
    assert over_resp.status_code == 422
    assert "exceeds" in over_resp.json()["error"].lower()

    # 6. Full settlement ($600.00)
    settle_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "600.00", "payment_date": str(date.today()), "payment_method": "CHECK"},
        headers=auth_headers,
    )
    assert settle_resp.status_code == 201
    settle_res = settle_resp.json()
    assert Decimal(str(settle_res["remaining_balance"])) == Decimal("0.00")
    assert settle_res["invoice_status"] == "PAID"

    # 7. Payment on paid invoice -> 422
    post_paid_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "50.00", "payment_date": str(date.today()), "payment_method": "ACH"},
        headers=auth_headers,
    )
    assert post_paid_resp.status_code == 422
    assert "already fully paid" in post_paid_resp.json()["error"].lower()
