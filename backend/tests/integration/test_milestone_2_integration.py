import fitz
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.base import Base
from app.models.document import DocumentSource, ExtractionStatus
from app.providers.storage import MemoryStorageProvider
from app.workers.celery_app import ping_task
import app.workers.tasks_extraction as tasks_mod


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def milestone_2_env(monkeypatch):
    """Integrated test harness for Milestone 2: Storage & Document Ingestion."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(tasks_mod, "AsyncSessionLocal", session_maker)

    storage = MemoryStorageProvider(bucket_name="ar-ingestion-test")
    monkeypatch.setattr(tasks_mod, "get_storage_provider", lambda: storage)

    yield session_maker, storage

    await engine.dispose()


@pytest.mark.asyncio
async def test_milestone_2_full_pipeline_verification(milestone_2_env):
    """
    Milestone 2 Integrated Layer Verification:
    Tests storage upload -> DB staging -> Celery extraction task execution ->
    multi-tier PyMuPDF parsing with delimiter isolation -> staged review payload.
    """
    session_maker, storage = milestone_2_env

    # Step 1: Verify worker connectivity probe
    assert ping_task() == "pong"

    # Step 2: Create authentic invoice PDF document via PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    invoice_content = (
        "ENTERPRISE INVOICE\n\n"
        "Bill To: Quantum Fleet Management Corp\n"
        "Invoice Number: INV-2026-M2-001\n"
        "Invoice Date: 2026-09-10\n"
        "Payment Due: 2026-10-10\n\n"
        "Description Quantity Unit_Price Line_Total\n"
        "Enterprise Fleet Telematics Subscription 50.00 40.00 2000.00\n"
        "Dedicated Satellite Gateway 1.00 750.00 750.00\n\n"
        "Total Amount Due: $2,750.00\n"
    )
    page.insert_text((50, 72), invoice_content, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()

    # Step 3: Persist document bytes via StorageProvider
    object_key = "invoices/2026/09/INV-2026-M2-001.pdf"
    storage_uri = storage.upload_file(pdf_bytes, object_key, content_type="application/pdf")
    assert storage_uri == f"memory://ar-ingestion-test/{object_key}"

    # Verify storage presigned preview URL generation
    preview_url = storage.get_file_url(object_key, expires_in_seconds=1800)
    assert object_key in preview_url

    # Step 4: Stage initial DocumentSource record in Database
    async with session_maker() as session:
        doc_source = DocumentSource(
            original_filename="INV-2026-M2-001.pdf",
            storage_path=storage_uri,
            mime_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            extraction_status=ExtractionStatus.QUEUED,
        )
        session.add(doc_source)
        await session.commit()
        await session.refresh(doc_source)
        doc_id = doc_source.id

    # Step 5: Execute asynchronous document extraction pipeline
    task_result = await tasks_mod._async_process_invoice_document(str(doc_id))
    assert task_result["status"] == "SUCCESS"
    assert task_result["invoice_number"] == "INV-2026-M2-001"

    # Step 6: Validate staged database payload
    async with session_maker() as session:
        stmt = select(DocumentSource).where(DocumentSource.id == doc_id)
        res = await session.execute(stmt)
        verified_doc = res.scalar_one()

        assert verified_doc.extraction_status == ExtractionStatus.SUCCESS
        payload = verified_doc.details_data
        assert payload["invoice_number"] == "INV-2026-M2-001"
        assert payload["customer_name"] == "Quantum Fleet Management Corp"
        assert payload["issue_date"] == "2026-09-10"
        assert payload["due_date"] == "2026-10-10"
        assert payload["total_amount"] == "2750.00"
        assert payload["currency"] == "USD"
        assert payload["confidence_score"] >= 0.8
        assert len(payload["line_items"]) == 2
        assert payload["line_items"][0]["description"] == "Enterprise Fleet Telematics Subscription"
        assert payload["line_items"][0]["line_total"] == "2000.00"
        assert payload["line_items"][1]["description"] == "Dedicated Satellite Gateway"
        assert payload["line_items"][1]["line_total"] == "750.00"
