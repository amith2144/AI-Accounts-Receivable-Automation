from datetime import date
from decimal import Decimal
import fitz
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.base import Base
from app.models.document import DocumentSource, ExtractionStatus
from app.providers.storage import MemoryStorageProvider
import app.workers.tasks_extraction as tasks_mod


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def setup_test_db(monkeypatch):
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(tasks_mod, "AsyncSessionLocal", test_session_maker)

    # Setup MemoryStorageProvider
    mem_storage = MemoryStorageProvider()
    monkeypatch.setattr(tasks_mod, "get_storage_provider", lambda: mem_storage)

    yield test_session_maker, mem_storage

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_process_invoice_document_task_success(setup_test_db):
    session_maker, storage = setup_test_db

    # 1. Create synthetic PDF
    doc_pdf = fitz.open()
    page = doc_pdf.new_page()
    text = (
        "INVOICE\n"
        "Bill To: Nexus Prime Logistics\n"
        "Invoice Number: INV-9901\n"
        "Date: 2026-09-01\n"
        "Due Date: 2026-10-01\n"
        "Warehousing Services 2.00 1700.00 3400.00\n"
        "Total Amount: $3,400.00\n"
    )
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc_pdf.tobytes()
    doc_pdf.close()

    # 2. Upload to storage
    storage_key = "invoices/test_inv_9901.pdf"
    storage_uri = storage.upload_file(pdf_bytes, storage_key, content_type="application/pdf")

    # 3. Create DocumentSource record in DB
    async with session_maker() as session:
        doc_record = DocumentSource(
            original_filename="test_inv_9901.pdf",
            storage_path=storage_uri,
            mime_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            extraction_status=ExtractionStatus.QUEUED,
        )
        session.add(doc_record)
        await session.commit()
        await session.refresh(doc_record)
        doc_id = doc_record.id

    # 4. Execute extraction task
    result = await tasks_mod._async_process_invoice_document(str(doc_id))
    assert result["status"] == "SUCCESS"
    assert result["invoice_number"] == "INV-9901"

    # 5. Verify database updates
    async with session_maker() as session:
        stmt = select(DocumentSource).where(DocumentSource.id == doc_id)
        res = await session.execute(stmt)
        updated_doc = res.scalar_one()

        assert updated_doc.extraction_status == ExtractionStatus.SUCCESS
        assert updated_doc.details_data["invoice_number"] == "INV-9901"
        assert updated_doc.details_data["customer_name"] == "Nexus Prime Logistics"
        assert updated_doc.details_data["total_amount"] == "3400.00"
        assert len(updated_doc.details_data["line_items"]) == 1
        assert updated_doc.details_data["confidence_score"] >= 0.7


@pytest.mark.asyncio
async def test_process_invoice_document_corrupted_file(setup_test_db):
    session_maker, storage = setup_test_db

    # Upload corrupt bytes
    storage_key = "invoices/corrupted.pdf"
    storage_uri = storage.upload_file(b"NOT_A_VALID_PDF_BYTES", storage_key, content_type="application/pdf")

    async with session_maker() as session:
        doc_record = DocumentSource(
            original_filename="corrupted.pdf",
            storage_path=storage_uri,
            mime_type="application/pdf",
            file_size_bytes=len(b"NOT_A_VALID_PDF_BYTES"),
            extraction_status=ExtractionStatus.QUEUED,
        )
        session.add(doc_record)
        await session.commit()
        await session.refresh(doc_record)
        doc_id = doc_record.id

    # Execute task
    result = await tasks_mod._async_process_invoice_document(str(doc_id))
    assert result["status"] == "FAILED"

    # Verify DB status
    async with session_maker() as session:
        stmt = select(DocumentSource).where(DocumentSource.id == doc_id)
        res = await session.execute(stmt)
        updated_doc = res.scalar_one()
        assert updated_doc.extraction_status == ExtractionStatus.FAILED
        assert updated_doc.error_message is not None
