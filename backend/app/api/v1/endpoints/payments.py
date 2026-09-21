import uuid
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_payment_service
from app.schemas.auth import UserProfile
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentRequest,
    PaymentResult,
)
from app.services.payment_service import PaymentService

router = APIRouter(tags=["Payments"])


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentResult,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment_for_invoice(
    invoice_id: uuid.UUID,
    request: PaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: UserProfile = Depends(get_current_user),
) -> PaymentResult:
    """
    Record remittance received against an invoice with row-level locking (SELECT FOR UPDATE).
    Enforces overpayment prevention (422) and automatically transitions invoice status
    (PARTIALLY_PAID or PAID).
    """
    data = PaymentCreate(
        invoice_id=invoice_id,
        amount=request.amount,
        payment_date=request.payment_date,
        payment_method=request.payment_method,
        reference_number=request.reference_number,
        notes=request.notes,
    )
    return await payment_service.record_payment(data)


@router.get(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentListResponse,
)
async def list_payments_for_invoice(
    invoice_id: uuid.UUID,
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: UserProfile = Depends(get_current_user),
) -> PaymentListResponse:
    """Retrieve itemized payment history and receipts for a specific invoice."""
    return await payment_service.list_payments_for_invoice(invoice_id)


@router.post(
    "/payments",
    response_model=PaymentResult,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment_direct(
    data: PaymentCreate,
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: UserProfile = Depends(get_current_user),
) -> PaymentResult:
    """Record remittance directly using complete PaymentCreate schema."""
    return await payment_service.record_payment(data)
