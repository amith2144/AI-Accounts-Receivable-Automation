import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    get_invoice_service,
    get_invoice_verification_service,
)
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.document import DocumentSource, ExtractionStatus
from app.models.invoice import InvoiceStatus
from app.providers.storage import get_storage_provider
from app.schemas.auth import UserProfile
from app.schemas.invoice import (
    DocumentImportStatusResponse,
    DocumentUploadResponse,
    InvoiceConfirmationRequest,
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    InvoiceVoidRequest,
)
from app.services.invoice_service import InvoiceService
from app.services.invoice_verification_service import InvoiceVerificationService
from app.workers.tasks_extraction import process_invoice_document

logger = logging.getLogger("app.api.invoices")

router = APIRouter(prefix="/invoices", tags=["Invoices"])

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    customer_id: Optional[uuid.UUID] = Query(None, description="Filter by debtor customer ID"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    search: Optional[str] = Query(None, description="Search by invoice number"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: UserProfile = Depends(get_current_user),
) -> InvoiceListResponse:
    """List and paginate invoices with optional customer, status, or search filters."""
    return await invoice_service.list_invoices(
        customer_id=customer_id,
        status=status,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: UserProfile = Depends(get_current_user),
) -> InvoiceResponse:
    """Manually create an invoice with line items and verified customer linkage."""
    return await invoice_service.create_invoice(data)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: UserProfile = Depends(get_current_user),
) -> InvoiceResponse:
    """Retrieve detailed invoice record with line items and balance breakdown."""
    return await invoice_service.get_invoice(invoice_id)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: UserProfile = Depends(get_current_user),
) -> InvoiceResponse:
    """Update invoice attributes prior to terminal settlement."""
    return await invoice_service.update_invoice(invoice_id, data)


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    invoice_id: uuid.UUID,
    data: InvoiceVoidRequest,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    current_user: UserProfile = Depends(get_current_user),
) -> InvoiceResponse:
    """Void an uncollected invoice, zeroing balance and logging audit trail."""
    return await invoice_service.void_invoice(invoice_id, reason=data.reason)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> DocumentUploadResponse:
    """
    Multipart file upload endpoint.
    Validates file format and size, persists binary payload to object storage,
    creates a DocumentSource staging record, and enqueues background OCR/extraction task.
    """
    # 1. Validate MIME type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported file format '{content_type}'. Allowed types: PDF, PNG, JPEG.",
            details={"allowed_types": list(ALLOWED_MIME_TYPES.keys())},
        )

    # 2. Read file bytes and validate size limit (Standard 4 & 9)
    file_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValidationError(
            f"File size ({len(file_bytes)} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB.",
            details={"max_size_mb": settings.MAX_UPLOAD_SIZE_MB},
        )

    if len(file_bytes) == 0:
        raise ValidationError("Uploaded file is empty.")

    # 3. Persist to storage provider
    storage_provider = get_storage_provider()
    doc_id = uuid.uuid4()
    ext = ALLOWED_MIME_TYPES.get(content_type, ".bin")
    storage_key = f"invoices/{doc_id}{ext}"
    storage_path = storage_provider.upload_file(storage_key, file_bytes, content_type)

    # 4. Create DocumentSource record
    doc_source = DocumentSource(
        id=doc_id,
        original_filename=file.filename or f"invoice_{doc_id}{ext}",
        storage_path=storage_path,
        mime_type=content_type,
        file_size_bytes=len(file_bytes),
        extraction_status=ExtractionStatus.QUEUED,
        details_data={},
    )
    db.add(doc_source)
    await db.commit()
    await db.refresh(doc_source)

    # 5. Enqueue Celery background extraction task
    task_id = None
    try:
        celery_task = process_invoice_document.delay(str(doc_id))
        task_id = celery_task.id
    except Exception as exc:
        logger.warning(f"Could not enqueue Celery task (worker/redis offline): {str(exc)}")

    return DocumentUploadResponse(
        document_id=doc_source.id,
        original_filename=doc_source.original_filename,
        file_size_bytes=doc_source.file_size_bytes,
        mime_type=doc_source.mime_type,
        extraction_status=doc_source.extraction_status.value,
        task_id=task_id,
    )


@router.get("/import-status/{document_id}", response_model=DocumentImportStatusResponse)
async def get_import_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> DocumentImportStatusResponse:
    """Retrieve asynchronous document extraction progress and staged financial fields."""
    stmt = select(DocumentSource).where(DocumentSource.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise NotFoundError(
            f"DocumentSource with ID {document_id} not found.",
            details={"document_id": str(document_id)},
        )

    return DocumentImportStatusResponse(
        document_id=doc.id,
        original_filename=doc.original_filename,
        extraction_status=doc.extraction_status.value,
        extracted_data=doc.details_data or {},
        error_message=doc.error_message,
    )


@router.post("/confirm-import/{document_id}", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def confirm_imported_invoice(
    document_id: uuid.UUID,
    confirmation: InvoiceConfirmationRequest,
    verification_service: InvoiceVerificationService = Depends(get_invoice_verification_service),
    current_user: UserProfile = Depends(get_current_user),
) -> InvoiceResponse:
    """
    Commit operator-reviewed and adjusted document extraction data into active ledger invoice.
    Auto-provisions customer profile if needed.
    """
    return await verification_service.verify_and_create_invoice(
        document_source_id=document_id,
        data=confirmation,
    )
