import pytest
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.base import Base
from app.models.document import DocumentSource, ExtractionStatus
from app.models.invoice import InvoiceStatus
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import InvoiceConfirmationRequest, InvoiceLineItemCreate
from app.services.customer_service import CustomerService
from app.services.invoice_verification_service import InvoiceVerificationService


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
async def sample_staged_document(async_session: AsyncSession):
    doc = DocumentSource(
        id=uuid.uuid4(),
        original_filename="sample_vendor_invoice.pdf",
        storage_path="memory://invoices/sample_vendor_invoice.pdf",
        mime_type="application/pdf",
        file_size_bytes=10240,
        extraction_status=ExtractionStatus.SUCCESS,
        details_data={
            "invoice_number": "INV-EXTRACTED-99",
            "customer_name": "Globex Corp",
            "issue_date": "2026-04-01",
            "due_date": "2026-05-01",
            "total_amount": "2500.00",
            "currency": "USD",
            "line_items": [
                {"description": "Cloud Hosting", "quantity": 1, "unit_price": 1500.00, "line_total": 1500.00},
                {"description": "Database Backup", "quantity": 2, "unit_price": 500.00, "line_total": 1000.00},
            ],
            "confidence_score": 0.95,
        },
    )
    async_session.add(doc)
    await async_session.flush()
    return doc


@pytest.mark.asyncio
async def test_verify_staged_document_with_new_customer(async_session: AsyncSession, sample_staged_document):
    service = InvoiceVerificationService(async_session)

    # Confirm import and provide customer email to auto-provision customer profile
    confirm_request = InvoiceConfirmationRequest(
        customer_email="ap@globex.com",
    )

    invoice = await service.verify_and_create_invoice(sample_staged_document.id, confirm_request)
    assert invoice.id is not None
    assert invoice.invoice_number == "INV-EXTRACTED-99"
    assert invoice.total_amount == Decimal("2500.00")
    assert invoice.balance_due == Decimal("2500.00")
    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.document_source_id == sample_staged_document.id
    assert len(invoice.line_items) == 2


@pytest.mark.asyncio
async def test_verify_with_operator_overrides(async_session: AsyncSession, sample_staged_document):
    cust_service = CustomerService(async_session)
    existing_cust = await cust_service.create_customer(
        CustomerCreate(name="Globex Corp", email="finance@globex.com")
    )

    service = InvoiceVerificationService(async_session)

    # Operator corrects total and updates invoice number
    confirm_request = InvoiceConfirmationRequest(
        customer_id=existing_cust.id,
        invoice_number="INV-CORRECTED-100",
        total_amount=Decimal("1200.00"),
        line_items=[
            InvoiceLineItemCreate(description="Revised Service", quantity=Decimal("1"), unit_price=Decimal("1200.00"))
        ],
    )

    invoice = await service.verify_and_create_invoice(sample_staged_document.id, confirm_request)
    assert invoice.invoice_number == "INV-CORRECTED-100"
    assert invoice.total_amount == Decimal("1200.00")
    assert invoice.customer_id == existing_cust.id
    assert len(invoice.line_items) == 1
    assert invoice.line_items[0].description == "Revised Service"


@pytest.mark.asyncio
async def test_duplicate_confirmation_rejection(async_session: AsyncSession, sample_staged_document):
    service = InvoiceVerificationService(async_session)

    confirm_request = InvoiceConfirmationRequest(
        customer_email="billing@globex.com",
    )
    await service.verify_and_create_invoice(sample_staged_document.id, confirm_request)

    # Second confirmation attempt on the same DocumentSource should be rejected
    with pytest.raises(ConflictError) as exc_info:
        await service.verify_and_create_invoice(sample_staged_document.id, confirm_request)
    assert "already been confirmed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_in_progress_document_rejection(async_session: AsyncSession):
    service = InvoiceVerificationService(async_session)

    processing_doc = DocumentSource(
        id=uuid.uuid4(),
        original_filename="pending.pdf",
        storage_path="memory://invoices/pending.pdf",
        mime_type="application/pdf",
        file_size_bytes=5000,
        extraction_status=ExtractionStatus.PROCESSING,
        details_data={},
    )
    async_session.add(processing_doc)
    await async_session.flush()

    with pytest.raises(ValidationError) as exc_info:
        await service.verify_and_create_invoice(processing_doc.id)
    assert "still in progress" in str(exc_info.value)
