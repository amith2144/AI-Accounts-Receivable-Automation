import io
import uuid
from datetime import date
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.api.v1.endpoints.invoices as invoices_ep
from app.api.deps import get_async_db, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base
from app.models.customer import Customer
from app.models.document import DocumentSource, ExtractionStatus
from app.providers.storage import MemoryStorageProvider


@pytest.fixture
async def invoice_test_env(monkeypatch):
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

    storage = MemoryStorageProvider(bucket_name="test-invoices")
    monkeypatch.setattr(invoices_ep, "get_storage_provider", lambda: storage)

    from unittest.mock import MagicMock
    mock_delay = MagicMock()
    mock_delay.return_value = MagicMock(id="mock-task-id-123")
    monkeypatch.setattr(invoices_ep.process_invoice_document, "delay", mock_delay)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, test_session_maker, storage

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
def auth_headers():
    token = create_access_token("operator", role="OPERATOR")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_invoice_api_crud_and_lifecycle(invoice_test_env, auth_headers: dict):
    client, session_maker, _ = invoice_test_env

    # 1. Seed customer
    customer_id = uuid.uuid4()
    async with session_maker() as session:
        cust = Customer(
            id=customer_id,
            name="Stark Industries",
            email="payments@stark.com",
            payment_terms_days=30,
        )
        session.add(cust)
        await session.commit()

    # 2. Create invoice with line items
    create_payload = {
        "customer_id": str(customer_id),
        "invoice_number": "INV-STARK-001",
        "issue_date": str(date.today()),
        "due_date": str(date.today()),
        "currency": "USD",
        "line_items": [
            {"description": "Arc Reactor Maintenance", "quantity": "2", "unit_price": "5000.00"},
            {"description": "Repulsor Calibration", "quantity": "1", "unit_price": "2500.00"},
        ],
    }
    create_resp = await client.post("/api/v1/invoices", json=create_payload, headers=auth_headers)
    assert create_resp.status_code == 201
    inv_data = create_resp.json()
    assert inv_data["invoice_number"] == "INV-STARK-001"
    assert Decimal(str(inv_data["total_amount"])) == Decimal("12500.00")
    assert Decimal(str(inv_data["balance_due"])) == Decimal("12500.00")
    assert len(inv_data["line_items"]) == 2
    invoice_id = inv_data["id"]

    # 3. Duplicate invoice number returns 409 Conflict
    dup_resp = await client.post("/api/v1/invoices", json=create_payload, headers=auth_headers)
    assert dup_resp.status_code == 409

    # 4. Get invoice by ID
    get_resp = await client.get(f"/api/v1/invoices/{invoice_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == invoice_id

    # 5. List invoices
    list_resp = await client.get(f"/api/v1/invoices?customer_id={customer_id}", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # 6. Update invoice currency
    up_resp = await client.put(
        f"/api/v1/invoices/{invoice_id}",
        json={"currency": "EUR"},
        headers=auth_headers,
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["currency"] == "EUR"

    # 7. Void invoice
    void_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/void",
        json={"reason": "Billing dispute resolved with cancellation"},
        headers=auth_headers,
    )
    assert void_resp.status_code == 200
    void_data = void_resp.json()
    assert void_data["status"] == "VOID"
    assert Decimal(str(void_data["balance_due"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_invoice_upload_and_confirmation_flow(invoice_test_env, auth_headers: dict):
    client, session_maker, storage = invoice_test_env

    # 1. Upload mock PDF file
    mock_pdf_bytes = b"%PDF-1.4 Mock Invoice Header Content"
    files = {"file": ("invoice_sample.pdf", io.BytesIO(mock_pdf_bytes), "application/pdf")}
    upload_resp = await client.post("/api/v1/invoices/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 202
    upload_data = upload_resp.json()
    doc_id = upload_data["document_id"]
    assert upload_data["original_filename"] == "invoice_sample.pdf"
    assert upload_data["mime_type"] == "application/pdf"

    # 2. Check import status
    status_resp = await client.get(f"/api/v1/invoices/import-status/{doc_id}", headers=auth_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["document_id"] == doc_id
    assert status_data["extraction_status"] == "QUEUED"

    # 3. Simulate successful extraction staging
    async with session_maker() as session:
        doc = await session.get(DocumentSource, uuid.UUID(doc_id))
        doc.extraction_status = ExtractionStatus.SUCCESS
        doc.details_data = {
            "invoice_number": "INV-M5-EXTRACT-01",
            "customer_name": "Wayne Enterprises",
            "customer_email": "accounts@waynecorp.com",
            "issue_date": "2026-09-01",
            "due_date": "2026-10-01",
            "total_amount": "8000.00",
            "currency": "USD",
            "line_items": [
                {"description": "Tactical Hardware", "quantity": 2.0, "unit_price": 4000.0, "line_total": 8000.0}
            ],
        }
        await session.commit()

    # 4. Confirm import into active invoice
    confirm_payload = {
        "customer_name": "Wayne Enterprises",
        "customer_email": "accounts@waynecorp.com",
        "invoice_number": "INV-M5-EXTRACT-01",
        "issue_date": "2026-09-01",
        "due_date": "2026-10-01",
        "total_amount": "8000.00",
        "line_items": [
            {"description": "Tactical Hardware", "quantity": "2.00", "unit_price": "4000.00"}
        ],
    }
    confirm_resp = await client.post(
        f"/api/v1/invoices/confirm-import/{doc_id}",
        json=confirm_payload,
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 201
    confirmed_inv = confirm_resp.json()
    assert confirmed_inv["invoice_number"] == "INV-M5-EXTRACT-01"
    assert Decimal(str(confirmed_inv["total_amount"])) == Decimal("8000.00")
    assert confirmed_inv["status"] == "ISSUED"
    assert confirmed_inv["document_source_id"] == doc_id
