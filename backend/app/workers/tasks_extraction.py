import asyncio
import logging
import uuid
from typing import Any, Dict
from celery import Task
from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.document import DocumentSource, ExtractionStatus
from app.providers.extraction import ExtractedInvoiceData, get_extraction_provider
from app.providers.storage import get_storage_provider
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.workers.extraction")


async def _async_process_invoice_document(document_source_id_str: str) -> Dict[str, Any]:
    """
    Asynchronous core routine for fetching document from storage, executing
    PyMuPDF/OCR text extraction, heuristic field matching, and updating DocumentSource.
    """
    doc_id = uuid.UUID(document_source_id_str)
    storage_provider = get_storage_provider()
    extraction_provider = get_extraction_provider()

    async with AsyncSessionLocal() as session:
        # 1. Fetch DocumentSource record
        stmt = select(DocumentSource).where(DocumentSource.id == doc_id)
        result = await session.execute(stmt)
        doc: DocumentSource | None = result.scalar_one_or_none()

        if not doc:
            logger.error(f"DocumentSource {doc_id} not found in database.")
            return {"status": "FAILED", "error": "DocumentSource record not found"}

        # 2. Update status to PROCESSING
        doc.extraction_status = ExtractionStatus.PROCESSING
        await session.commit()
        await session.refresh(doc)

        try:
            # 3. Download raw bytes from storage
            # Strip storage scheme prefix (e.g., s3://bucket/key or memory://bucket/key)
            storage_key = doc.storage_path
            if "://" in storage_key:
                # Format: scheme://bucket/key -> extract key
                parts = storage_key.split("://", 1)[1].split("/", 1)
                storage_key = parts[1] if len(parts) > 1 else parts[0]

            logger.info(f"Downloading document bytes for {doc.id} from key: {storage_key}")
            file_bytes = storage_provider.download_file(storage_key)

            # 4. Execute Multi-Tier Document Extraction with Delimiter Isolation
            extracted: ExtractedInvoiceData = extraction_provider.extract_from_bytes(
                file_bytes=file_bytes,
                mime_type=doc.mime_type,
            )

            # 5. Evaluate extraction quality (Section 7 Failure Modes)
            has_essentials = extracted.invoice_number is not None and extracted.total_amount is not None

            if has_essentials and extracted.confidence_score >= 0.6:
                doc.extraction_status = ExtractionStatus.SUCCESS
                doc.error_message = None
            elif extracted.raw_text.strip():
                # Text found but key fields missing; requires operator review
                doc.extraction_status = ExtractionStatus.PARTIAL_SUCCESS
                doc.error_message = "Partial extraction: some invoice fields could not be verified automatically."
            else:
                doc.extraction_status = ExtractionStatus.FAILED
                doc.error_message = "Failed to extract legible text from document."

            # Stage extracted fields as JSON payload
            doc.details_data = {
                "invoice_number": extracted.invoice_number,
                "customer_name": extracted.customer_name,
                "issue_date": extracted.issue_date.isoformat() if extracted.issue_date else None,
                "due_date": extracted.due_date.isoformat() if extracted.due_date else None,
                "total_amount": str(extracted.total_amount) if extracted.total_amount is not None else None,
                "currency": extracted.currency,
                "line_items": [item.model_dump(mode="json") for item in extracted.line_items],
                "confidence_score": extracted.confidence_score,
                "extraction_method": extracted.extraction_method,
            }

            await session.commit()
            logger.info(f"Successfully processed DocumentSource {doc.id} -> {doc.extraction_status}")

            return {
                "document_id": str(doc.id),
                "status": doc.extraction_status.value,
                "confidence_score": extracted.confidence_score,
                "invoice_number": extracted.invoice_number,
            }

        except Exception as exc:
            logger.exception(f"Unhandled failure during document extraction for {doc.id}: {str(exc)}")
            doc.extraction_status = ExtractionStatus.FAILED
            doc.error_message = f"Document processing failed: {str(exc)}"
            await session.commit()
            return {"document_id": str(doc.id), "status": "FAILED", "error": str(exc)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="app.workers.tasks_extraction.process_invoice_document",
)
def process_invoice_document(self: Task, document_source_id: str) -> Dict[str, Any]:
    """
    Celery background worker entrypoint for invoice extraction.
    Executes asynchronous pipeline inside event loop with exponential retry handling.
    """
    try:
        return asyncio.run(_async_process_invoice_document(document_source_id))
    except Exception as exc:
        logger.error(f"Task retry triggered for {document_source_id}: {str(exc)}")
        raise self.retry(exc=exc)
