import pytest
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.base import Base
from app.models.document import DocumentSource, ExtractionStatus
from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentMethod
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.invoice import (
    InvoiceConfirmationRequest,
    InvoiceCreate,
    InvoiceLineItemCreate,
)
from app.schemas.payment import PaymentCreate
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.invoice_verification_service import InvoiceVerificationService
from app.services.payment_service import PaymentService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def milestone_3_env():
    """Sets up an integrated in-memory test database for Milestone 3 domain services."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_milestone_3_core_business_domain_integration(milestone_3_env: AsyncSession):
    """
    Milestone 3 Layer Integration Verification:
    Tests the complete business domain lifecycle across CustomerService, InvoiceService,
    PaymentService, and InvoiceVerificationService with strict transaction integrity.
    """
    session = milestone_3_env

    customer_service = CustomerService(session)
    invoice_service = InvoiceService(session)
    payment_service = PaymentService(session)
    verification_service = InvoiceVerificationService(session, invoice_service, customer_service)

    # 1. Customer Management Workflow
    cust = await customer_service.create_customer(
        CustomerCreate(
            name="Apex Heavy Industries",
            email="billing@apexheavy.com",
            phone="+1-800-555-9000",
            payment_terms_days=45,
            reminder_paused=False,
        )
    )
    assert cust.id is not None
    assert cust.payment_terms_days == 45

    # Directory search
    search_res = await customer_service.list_customers(query="Apex")
    assert search_res.total == 1
    assert search_res.items[0].id == cust.id

    # 2. Document Extraction Verification -> Active Invoice
    staged_doc = DocumentSource(
        id=uuid.uuid4(),
        original_filename="apex_freight_inv.pdf",
        storage_path="memory://invoices/apex_freight_inv.pdf",
        mime_type="application/pdf",
        file_size_bytes=14200,
        extraction_status=ExtractionStatus.SUCCESS,
        details_data={
            "invoice_number": "INV-APEX-001",
            "customer_name": "Apex Heavy Industries",
            "issue_date": "2026-03-01",
            "due_date": "2026-04-15",
            "total_amount": "5000.00",
            "currency": "USD",
            "line_items": [
                {"description": "Turbine Transport", "quantity": 1, "unit_price": 3500.00, "line_total": 3500.00},
                {"description": "Crane Logistics", "quantity": 1, "unit_price": 1500.00, "line_total": 1500.00},
            ],
            "confidence_score": 0.98,
        },
    )
    session.add(staged_doc)
    await session.flush()

    inv_from_doc = await verification_service.verify_and_create_invoice(
        staged_doc.id,
        InvoiceConfirmationRequest(customer_id=cust.id),
    )
    assert inv_from_doc.invoice_number == "INV-APEX-001"
    assert inv_from_doc.total_amount == Decimal("5000.00")
    assert inv_from_doc.balance_due == Decimal("5000.00")
    assert inv_from_doc.status == InvoiceStatus.ISSUED
    assert inv_from_doc.document_source_id == staged_doc.id
    assert len(inv_from_doc.line_items) == 2

    # 3. Direct Invoice Creation with Line Items
    manual_inv = await invoice_service.create_invoice(
        InvoiceCreate(
            customer_id=cust.id,
            invoice_number="INV-APEX-002",
            issue_date=date(2026, 3, 5),
            due_date=date(2026, 4, 19),
            line_items=[
                InvoiceLineItemCreate(description="Maintenance Inspection", quantity=Decimal("4.00"), unit_price=Decimal("250.00")),
                InvoiceLineItemCreate(description="Replacement Bearings", quantity=Decimal("2.00"), unit_price=Decimal("500.00")),
            ],
        )
    )
    assert manual_inv.total_amount == Decimal("2000.00")
    assert manual_inv.balance_due == Decimal("2000.00")

    # Verify Customer Aggregate Balances: Total = $7000.00, Outstanding = $7000.00
    cust_metrics = await customer_service.get_customer(cust.id)
    assert cust_metrics.total_invoiced == Decimal("7000.00")
    assert cust_metrics.outstanding_balance == Decimal("7000.00")

    # 4. Partial Remittance Application ($3000 on $5000 invoice)
    pay_res1 = await payment_service.record_payment(
        PaymentCreate(
            invoice_id=inv_from_doc.id,
            amount=Decimal("3000.00"),
            payment_date=date(2026, 3, 20),
            payment_method=PaymentMethod.WIRE,
            reference_number="FEDWIRE-992211",
            notes="Partial payment for turbine haul",
        )
    )
    assert pay_res1.invoice_status == InvoiceStatus.PARTIALLY_PAID
    assert pay_res1.remaining_balance == Decimal("2000.00")

    # 5. Full Remittance Application (Remaining $2000 settled)
    pay_res2 = await payment_service.record_payment(
        PaymentCreate(
            invoice_id=inv_from_doc.id,
            amount=Decimal("2000.00"),
            payment_date=date(2026, 3, 25),
            payment_method=PaymentMethod.ACH,
            reference_number="ACH-334455",
        )
    )
    assert pay_res2.invoice_status == InvoiceStatus.PAID
    assert pay_res2.remaining_balance == Decimal("0.00")

    # Verify invoice state
    reloaded_inv = await invoice_service.get_invoice(inv_from_doc.id)
    assert reloaded_inv.status == InvoiceStatus.PAID
    assert reloaded_inv.balance_due == Decimal("0.00")

    # 6. Overpayment Guard & Settled Invoice Guard
    with pytest.raises(ValidationError) as exc_overpay:
        await payment_service.record_payment(
            PaymentCreate(
                invoice_id=manual_inv.id,
                amount=Decimal("2500.00"),  # Balance is only 2000.00
                payment_date=date(2026, 3, 26),
                payment_method=PaymentMethod.CHECK,
            )
        )
    assert "exceeds outstanding balance due" in str(exc_overpay.value)

    with pytest.raises(ValidationError) as exc_settled:
        await payment_service.record_payment(
            PaymentCreate(
                invoice_id=inv_from_doc.id,  # Already paid
                amount=Decimal("100.00"),
                payment_date=date(2026, 3, 26),
                payment_method=PaymentMethod.CHECK,
            )
        )
    assert "already fully paid" in str(exc_settled.value)

    # 7. Voiding Safeguards
    # Cannot void a fully paid invoice
    with pytest.raises(ValidationError) as exc_void_paid:
        await invoice_service.void_invoice(inv_from_doc.id)
    assert "Cannot void a fully paid invoice" in str(exc_void_paid.value)

    # Can void uncollected invoice (manual_inv)
    voided_inv = await invoice_service.void_invoice(manual_inv.id, reason="Billing error, rebilling under PO-99")
    assert voided_inv.status == InvoiceStatus.VOID
    assert voided_inv.balance_due == Decimal("0.00")

    # 8. Final Customer Balance Validation: All invoices paid or voided -> Outstanding = $0.00
    final_cust = await customer_service.get_customer(cust.id)
    assert final_cust.outstanding_balance == Decimal("0.00")
