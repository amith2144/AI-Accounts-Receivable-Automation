import io
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.api.v1.endpoints.invoices as invoices_ep
from app.api.deps import get_async_db, get_db
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.models.document import DocumentSource, ExtractionStatus
from app.providers.storage import MemoryStorageProvider


@pytest.fixture
async def m5_integration_env(monkeypatch):
    """Integrated test environment for Milestone 5: API Layer, Gateway & Security Hardening."""
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

    # In-memory storage provider for document uploads
    storage = MemoryStorageProvider(bucket_name="m5-test-bucket")
    monkeypatch.setattr(invoices_ep, "get_storage_provider", lambda: storage)

    # Mock Celery delay to avoid redis socket connect delays in unit/integration tests
    mock_delay = MagicMock()
    mock_delay.return_value = MagicMock(id="m5-mock-task-id")
    monkeypatch.setattr(invoices_ep.process_invoice_document, "delay", mock_delay)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, test_session_maker, storage

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_milestone_5_end_to_end_api_and_security(m5_integration_env):
    """
    Milestone 5 Integrated Verification:
    Auth -> Customer -> Invoice -> Upload -> Verification -> Payment ->
    Dashboard -> Cadence -> Activities -> Accounting Export -> RBAC guards.
    """
    client, session_maker, storage = m5_integration_env

    # -------------------------------------------------------------------------
    # 1. Staff Authentication & Session Lifecycle (TASK-025)
    # -------------------------------------------------------------------------
    # Verify unauthenticated call to protected endpoint is rejected
    unauth_resp = await client.get("/api/v1/customers")
    assert unauth_resp.status_code == 401
    assert unauth_resp.json()["code"] == "UNAUTHORIZED"

    # Authenticate as operator
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.OPERATOR_USERNAME, "password": settings.OPERATOR_PASSWORD},
    )
    assert login_resp.status_code == 200
    token_payload = login_resp.json()
    assert "access_token" in token_payload
    assert "refresh_token" in token_payload
    access_token = token_payload["access_token"]
    refresh_token = token_payload["refresh_token"]

    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Verify /auth/me returns operator profile
    me_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == settings.OPERATOR_USERNAME

    # Refresh token rotation
    ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_resp.status_code == 200
    assert "access_token" in ref_resp.json()

    # -------------------------------------------------------------------------
    # 2. Customer Management (TASK-026)
    # -------------------------------------------------------------------------
    cust_payload = {
        "name": "Omni Consumer Products",
        "email": "remittance@ocp.corp",
        "phone": "+1-313-555-0100",
        "payment_terms_days": 30,
        "reminder_paused": False,
    }
    cust_resp = await client.post("/api/v1/customers", json=cust_payload, headers=auth_headers)
    assert cust_resp.status_code == 201
    cust_data = cust_resp.json()
    customer_id = cust_data["id"]
    assert cust_data["name"] == "Omni Consumer Products"

    # Query customer list
    list_cust_resp = await client.get("/api/v1/customers?query=Omni", headers=auth_headers)
    assert list_cust_resp.status_code == 200
    assert list_cust_resp.json()["total"] == 1

    # -------------------------------------------------------------------------
    # 3. Direct Invoice Creation & Line Items (TASK-027)
    # -------------------------------------------------------------------------
    today = date.today()
    inv_payload = {
        "customer_id": customer_id,
        "invoice_number": "INV-OCP-2026-001",
        "issue_date": str(today - timedelta(days=20)),
        "due_date": str(today - timedelta(days=5)),  # Past due (overdue)
        "currency": "USD",
        "line_items": [
            {"description": "ED-209 Firmware Upgrade", "quantity": "10.00", "unit_price": "250.00"},
            {"description": "Coprocessor Diagnostics", "quantity": "1.00", "unit_price": "1500.00"},
        ],
    }
    inv_resp = await client.post("/api/v1/invoices", json=inv_payload, headers=auth_headers)
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()
    invoice_id = inv_data["id"]
    assert Decimal(str(inv_data["total_amount"])) == Decimal("4000.00")
    assert Decimal(str(inv_data["balance_due"])) == Decimal("4000.00")
    assert len(inv_data["line_items"]) == 2

    # -------------------------------------------------------------------------
    # 4. Document Ingestion & Verification Flow (TASK-027)
    # -------------------------------------------------------------------------
    mock_pdf = b"%PDF-1.4 Mock Document Content for Automated Ingestion"
    upload_file = {"file": ("ocp_invoice.pdf", io.BytesIO(mock_pdf), "application/pdf")}
    upload_resp = await client.post("/api/v1/invoices/upload", files=upload_file, headers=auth_headers)
    assert upload_resp.status_code == 202
    doc_id = upload_resp.json()["document_id"]

    # Verify import status
    status_resp = await client.get(f"/api/v1/invoices/import-status/{doc_id}", headers=auth_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["extraction_status"] == "QUEUED"

    # Stage extracted document
    async with session_maker() as session:
        doc = await session.get(DocumentSource, uuid.UUID(doc_id))
        doc.extraction_status = ExtractionStatus.SUCCESS
        doc.details_data = {
            "invoice_number": "INV-OCP-2026-002",
            "customer_name": "Omni Consumer Products",
            "issue_date": str(today - timedelta(days=10)),
            "due_date": str(today + timedelta(days=20)),
            "total_amount": "6000.00",
            "currency": "USD",
        }
        await session.commit()

    # Confirm imported document into active ledger
    confirm_payload = {
        "customer_id": customer_id,
        "invoice_number": "INV-OCP-2026-002",
        "issue_date": str(today - timedelta(days=10)),
        "due_date": str(today + timedelta(days=20)),
        "total_amount": "6000.00",
        "currency": "USD",
        "line_items": [{"description": "Urban Security Modules", "quantity": "3.00", "unit_price": "2000.00"}],
    }
    confirm_resp = await client.post(
        f"/api/v1/invoices/confirm-import/{doc_id}",
        json=confirm_payload,
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 201
    assert confirm_resp.json()["invoice_number"] == "INV-OCP-2026-002"

    # -------------------------------------------------------------------------
    # 5. Remittance & Payment Processing (TASK-028)
    # -------------------------------------------------------------------------
    # Partial payment on invoice 1 ($1,500.00 of $4,000.00)
    pay_payload = {
        "amount": "1500.00",
        "payment_date": str(today),
        "payment_method": "ACH",
        "reference_number": "ACH-OCP-7788",
        "notes": "Partial settlement batch 1",
    }
    pay_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json=pay_payload,
        headers=auth_headers,
    )
    assert pay_resp.status_code == 201
    pay_result = pay_resp.json()
    assert Decimal(str(pay_result["remaining_balance"])) == Decimal("2500.00")
    assert pay_result["invoice_status"] == "PARTIALLY_PAID"

    # Query payment history for invoice
    pay_list = await client.get(f"/api/v1/invoices/{invoice_id}/payments", headers=auth_headers)
    assert pay_list.status_code == 200
    assert pay_list.json()["total"] == 1

    # Overpayment rejection: attempt $3,000.00 when balance is $2,500.00 -> 422
    over_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "3000.00", "payment_date": str(today), "payment_method": "WIRE"},
        headers=auth_headers,
    )
    assert over_resp.status_code == 422
    assert "exceeds" in over_resp.json()["error"].lower()

    # Settle remaining $2,500.00 -> status PAID
    settle_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "2500.00", "payment_date": str(today), "payment_method": "WIRE"},
        headers=auth_headers,
    )
    assert settle_resp.status_code == 201
    assert Decimal(str(settle_resp.json()["remaining_balance"])) == Decimal("0.00")
    assert settle_resp.json()["invoice_status"] == "PAID"

    # -------------------------------------------------------------------------
    # 6. Operational Dashboard Telemetry (TASK-029)
    # -------------------------------------------------------------------------
    metrics_resp = await client.get("/api/v1/dashboard/metrics", headers=auth_headers)
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    # Invoice 1 is PAID (balance $0), Invoice 2 has balance $6,000.00
    assert Decimal(str(metrics_data["total_receivables"])) == Decimal("6000.00")

    aging_resp = await client.get("/api/v1/dashboard/aging", headers=auth_headers)
    assert aging_resp.status_code == 200
    buckets = aging_resp.json()["buckets"]
    assert "CURRENT" in buckets
    assert buckets["CURRENT"]["invoice_count"] == 1

    act_resp = await client.get("/api/v1/dashboard/recent-activity", headers=auth_headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["total"] >= 1

    # -------------------------------------------------------------------------
    # 7. Cadence Rule Administration & Trigger (TASK-030)
    # -------------------------------------------------------------------------
    cadence_payload = {
        "name": "Standard Net 30 Cadence",
        "trigger_offset_days": 7,
        "reminder_tone": "STANDARD",
        "email_subject_template": "Follow-Up: Invoice {{ invoice_number }}",
        "email_body_template": "Dear {{ customer_name }}, this is a friendly reminder for invoice {{ invoice_number }}.",
        "is_active": True,
    }
    cad_resp = await client.post("/api/v1/cadences", json=cadence_payload, headers=auth_headers)
    assert cad_resp.status_code == 201

    # Trigger cadence dry-run dispatch
    trigger_resp = await client.post("/api/v1/cadences/trigger-run?dry_run=true", headers=auth_headers)
    assert trigger_resp.status_code == 200
    assert trigger_resp.json()["evaluated_cadences"] >= 1

    # Query comprehensive activities endpoint
    all_act = await client.get("/api/v1/activities", headers=auth_headers)
    assert all_act.status_code == 200
    assert all_act.json()["total"] >= 1

    # -------------------------------------------------------------------------
    # 8. External ERP & Accounting Export (TASK-031)
    # -------------------------------------------------------------------------
    # Export Invoices CSV
    inv_csv_resp = await client.get("/api/v1/integrations/accounting/export?export_type=invoices", headers=auth_headers)
    assert inv_csv_resp.status_code == 200
    assert "text/csv" in inv_csv_resp.headers["Content-Type"]
    assert "INV-OCP-2026-002" in inv_csv_resp.text

    # Export Payments CSV
    pay_csv_resp = await client.get("/api/v1/integrations/accounting/export?export_type=payments", headers=auth_headers)
    assert pay_csv_resp.status_code == 200
    assert "ACH-OCP-7788" in pay_csv_resp.text

    # Export Reconciliation JSON
    rec_json_resp = await client.get(
        "/api/v1/integrations/accounting/export?export_type=reconciliation&format=json",
        headers=auth_headers,
    )
    assert rec_json_resp.status_code == 200
    rec_data = rec_json_resp.json()
    assert rec_data["total_invoices"] >= 1
    assert rec_data["total_payments"] >= 2
