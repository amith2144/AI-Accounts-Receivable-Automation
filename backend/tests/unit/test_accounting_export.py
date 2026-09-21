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
from app.models.payment import PaymentMethod, PaymentRecord
from app.providers.accounting.csv_exporter import CsvAccountingExporter


def test_csv_accounting_exporter_unit():
    exporter = CsvAccountingExporter()

    # 1. Invoices export
    inv_data = [
        {
            "invoice_number": "INV-001",
            "customer_name": "Oscorp",
            "customer_email": "norman@oscorp.com",
            "issue_date": "2026-09-01",
            "due_date": "2026-10-01",
            "currency": "USD",
            "total_amount": 5000.0,
            "balance_due": 2500.0,
            "status": "PARTIALLY_PAID",
        }
    ]
    csv_inv = exporter.export_invoices(inv_data)
    assert "invoice_number,customer_name" in csv_inv
    assert "INV-001,Oscorp,norman@oscorp.com,2026-09-01,2026-10-01,USD,5000.00,2500.00,PARTIALLY_PAID" in csv_inv

    # 2. Payments export
    pay_data = [
        {
            "payment_id": "pay-123",
            "invoice_number": "INV-001",
            "customer_name": "Oscorp",
            "payment_date": "2026-09-15",
            "payment_method": "ACH",
            "reference_number": "REF-999",
            "amount": 2500.0,
            "notes": "First half payment",
        }
    ]
    csv_pay = exporter.export_payments(pay_data)
    assert "payment_id,invoice_number" in csv_pay
    assert "pay-123,INV-001,Oscorp,2026-09-15,ACH,REF-999,2500.00,First half payment" in csv_pay

    # 3. Reconciliation export
    csv_rec = exporter.export_reconciliation_ledger(inv_data, pay_data)
    assert "record_type,identifier" in csv_rec
    assert "INVOICE,INV-001,Oscorp,2026-09-01,5000.00,2500.00,PARTIALLY_PAID" in csv_rec
    assert "PAYMENT,INV-001,Oscorp,2026-09-15,-2500.00,0.00,ACH,REF-999" in csv_rec


@pytest.fixture
async def export_test_env():
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
async def test_accounting_export_endpoint(export_test_env, auth_headers: dict):
    client, session_maker = export_test_env

    # 1. Seed customer, invoice, and payment
    cust_id = uuid.uuid4()
    inv_id = uuid.uuid4()
    pay_id = uuid.uuid4()

    async with session_maker() as session:
        cust = Customer(id=cust_id, name="Stark Industries", email="tony@stark.com", payment_terms_days=30)
        session.add(cust)
        inv = Invoice(
            id=inv_id,
            customer_id=cust_id,
            invoice_number="INV-STARK-EXP",
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 10, 1),
            currency="USD",
            total_amount=Decimal("10000.00"),
            balance_due=Decimal("6000.00"),
            status=InvoiceStatus.PARTIALLY_PAID,
        )
        session.add(inv)
        pay = PaymentRecord(
            id=pay_id,
            invoice_id=inv_id,
            amount=Decimal("4000.00"),
            payment_date=date(2026, 9, 10),
            payment_method=PaymentMethod.WIRE,
            reference_number="WIRE-777",
            notes="Initial deposit",
        )
        session.add(pay)
        await session.commit()

    # 2. Test Invoices CSV export
    inv_resp = await client.get("/api/v1/integrations/accounting/export?export_type=invoices", headers=auth_headers)
    assert inv_resp.status_code == 200
    assert "text/csv" in inv_resp.headers["Content-Type"]
    assert "INV-STARK-EXP" in inv_resp.text
    assert "Stark Industries" in inv_resp.text

    # 3. Test Payments CSV export
    pay_resp = await client.get("/api/v1/integrations/accounting/export?export_type=payments", headers=auth_headers)
    assert pay_resp.status_code == 200
    assert "WIRE-777" in pay_resp.text
    assert "4000.00" in pay_resp.text

    # 4. Test Reconciliation JSON export
    json_resp = await client.get(
        "/api/v1/integrations/accounting/export?export_type=reconciliation&format=json",
        headers=auth_headers,
    )
    assert json_resp.status_code == 200
    json_data = json_resp.json()
    assert json_data["total_invoices"] == 1
    assert json_data["total_payments"] == 1

    # 5. Unauthenticated request rejected
    unauth = await client.get("/api/v1/integrations/accounting/export")
    assert unauth.status_code == 401
