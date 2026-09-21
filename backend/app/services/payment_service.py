import logging
import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.activity import ActivityType, CollectionActivity
from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentRecord
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentResult,
)

logger = logging.getLogger("app.services.payment")


class PaymentService:
    """
    Domain service for remittance processing, balance reconciliation,
    and row-level locked transaction safety. Enforces Rule 02 and Rule 03.
    """

    def __init__(
        self,
        session: AsyncSession,
        payment_repo: Optional[PaymentRepository] = None,
        invoice_repo: Optional[InvoiceRepository] = None,
    ):
        self.session = session
        self.payment_repo = payment_repo or PaymentRepository(session)
        self.invoice_repo = invoice_repo or InvoiceRepository(session)

    async def record_payment(self, data: PaymentCreate) -> PaymentResult:
        """
        Record a payment against an invoice with row-level locking (SELECT FOR UPDATE),
        strict overpayment rejection (422), balance recalculation, and status transition.
        """
        if data.amount <= Decimal("0.00"):
            raise ValidationError(
                "Payment amount must be greater than zero.",
                details={"amount": str(data.amount)},
            )

        # 1. Acquire row-level lock on the target invoice to prevent concurrent remittance race conditions
        invoice = await self.invoice_repo.get(data.invoice_id, for_update=True)
        if not invoice:
            raise NotFoundError(
                f"Invoice with ID {data.invoice_id} not found.",
                details={"invoice_id": str(data.invoice_id)},
            )

        # 2. Check invoice lifecycle constraints
        if invoice.status == InvoiceStatus.VOID:
            raise ValidationError(
                f"Cannot apply payment to voided invoice '{invoice.invoice_number}'.",
                details={"invoice_id": str(invoice.id), "status": invoice.status.value},
            )

        if invoice.status == InvoiceStatus.PAID or invoice.balance_due <= Decimal("0.00"):
            raise ValidationError(
                f"Invoice '{invoice.invoice_number}' is already fully paid. Balance due is zero.",
                details={"invoice_id": str(invoice.id), "balance_due": str(invoice.balance_due)},
            )

        # 3. Prevent overpayment (HTTP 422 Unprocessable Content)
        payment_amount = Decimal(str(data.amount)).quantize(Decimal("0.01"))
        if payment_amount > invoice.balance_due:
            raise ValidationError(
                f"Payment amount (${payment_amount}) exceeds outstanding balance due (${invoice.balance_due}).",
                details={
                    "payment_amount": str(payment_amount),
                    "balance_due": str(invoice.balance_due),
                    "invoice_id": str(invoice.id),
                },
            )

        # 4. Calculate updated balance and determine resulting status
        new_balance = (invoice.balance_due - payment_amount).quantize(Decimal("0.01"))
        invoice.balance_due = new_balance

        if new_balance == Decimal("0.00"):
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        # 5. Persist immutable PaymentRecord
        payment = PaymentRecord(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            amount=payment_amount,
            payment_date=data.payment_date,
            payment_method=data.payment_method,
            reference_number=data.reference_number.strip() if data.reference_number else None,
            notes=data.notes.strip() if data.notes else None,
        )
        self.session.add(payment)

        # 6. Record audit activity
        audit = CollectionActivity(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            activity_type=ActivityType.PAYMENT_APPLIED,
            performed_by="REMITTANCE_CLERK",
            details={
                "payment_id": str(payment.id),
                "amount": str(payment_amount),
                "remaining_balance": str(new_balance),
                "method": data.payment_method.value,
                "reference": data.reference_number,
                "new_status": invoice.status.value,
            },
        )
        self.session.add(audit)

        await self.session.flush()
        await self.session.refresh(payment)

        logger.info(
            f"Applied payment ${payment_amount} to invoice {invoice.invoice_number}. "
            f"Remaining balance: ${new_balance}, Status: {invoice.status.value}"
        )

        return PaymentResult(
            payment=PaymentResponse(
                id=payment.id,
                invoice_id=payment.invoice_id,
                amount=payment.amount,
                payment_date=payment.payment_date,
                payment_method=payment.payment_method,
                reference_number=payment.reference_number,
                notes=payment.notes,
                created_at=payment.created_at,
            ),
            invoice_id=invoice.id,
            invoice_status=invoice.status,
            remaining_balance=new_balance,
        )

    async def list_payments_for_invoice(self, invoice_id: uuid.UUID) -> PaymentListResponse:
        """Retrieve all payment records for an invoice."""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise NotFoundError(
                f"Invoice with ID {invoice_id} not found.",
                details={"invoice_id": str(invoice_id)},
            )

        records = await self.payment_repo.get_by_invoice(invoice_id)
        items = [
            PaymentResponse(
                id=rec.id,
                invoice_id=rec.invoice_id,
                amount=rec.amount,
                payment_date=rec.payment_date,
                payment_method=rec.payment_method,
                reference_number=rec.reference_number,
                notes=rec.notes,
                created_at=rec.created_at,
            )
            for rec in records
        ]
        return PaymentListResponse(items=items, total=len(items))
