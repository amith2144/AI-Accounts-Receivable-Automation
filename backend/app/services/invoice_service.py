import logging
import uuid
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.activity import ActivityType, CollectionActivity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import InvoiceLineItem
from app.repositories.customer_repo import CustomerRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItemResponse,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)

logger = logging.getLogger("app.services.invoice")


class InvoiceService:
    """
    Domain service for invoice lifecycle management, line item validation,
    status transitions, and voiding safeguards. Enforces Rule 02 and Rule 03.
    """

    def __init__(
        self,
        session: AsyncSession,
        invoice_repo: Optional[InvoiceRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
    ):
        self.session = session
        self.invoice_repo = invoice_repo or InvoiceRepository(session)
        self.customer_repo = customer_repo or CustomerRepository(session)

    async def create_invoice(self, data: InvoiceCreate) -> InvoiceResponse:
        """Create a new invoice with customer validation, line item sum verification, and initial balance."""
        # 1. Customer verification
        customer = await self.customer_repo.get(data.customer_id)
        if not customer:
            raise NotFoundError(
                f"Customer with ID {data.customer_id} does not exist.",
                details={"customer_id": str(data.customer_id)},
            )

        # 2. Duplicate invoice number check per debtor
        existing = await self.invoice_repo.get_by_customer_and_number(
            data.customer_id, data.invoice_number
        )
        if existing:
            raise ConflictError(
                f"Invoice number '{data.invoice_number}' already exists for this customer.",
                details={"customer_id": str(data.customer_id), "invoice_number": data.invoice_number},
            )

        # 3. Date sequence validation
        if data.due_date < data.issue_date:
            raise ValidationError(
                "Invoice due date cannot be earlier than issue date.",
                details={"issue_date": str(data.issue_date), "due_date": str(data.due_date)},
            )

        # 4. Monetary calculations and line item consistency
        if data.line_items:
            computed_total = Decimal("0.00")
            for item in data.line_items:
                qty = Decimal(str(item.quantity))
                price = Decimal(str(item.unit_price))
                computed_total += (qty * price).quantize(Decimal("0.01"))

            if data.total_amount is not None:
                provided_total = Decimal(str(data.total_amount)).quantize(Decimal("0.01"))
                if abs(provided_total - computed_total) > Decimal("0.01"):
                    raise ValidationError(
                        f"Provided total amount ({provided_total}) does not match sum of line items ({computed_total}).",
                        details={"provided": str(provided_total), "computed": str(computed_total)},
                    )
            final_total = computed_total
        else:
            if data.total_amount is None or Decimal(str(data.total_amount)) < 0:
                raise ValidationError("Total amount must be specified and non-negative when line items are omitted.")
            final_total = Decimal(str(data.total_amount)).quantize(Decimal("0.01"))

        # 5. Persist invoice record
        invoice = Invoice(
            id=uuid.uuid4(),
            customer_id=data.customer_id,
            invoice_number=data.invoice_number.strip(),
            issue_date=data.issue_date,
            due_date=data.due_date,
            currency=data.currency.upper(),
            total_amount=final_total,
            balance_due=final_total,
            status=data.status or InvoiceStatus.ISSUED,
            document_source_id=data.document_source_id,
        )
        self.session.add(invoice)
        await self.session.flush()

        # 6. Persist line items if provided
        if data.line_items:
            await self.invoice_repo.add_line_items(
                invoice.id,
                [item.model_dump() for item in data.line_items],
            )

        # 7. Reload with all relationships
        reloaded = await self.invoice_repo.get_with_details(invoice.id)
        logger.info(f"Created invoice '{invoice.invoice_number}' (ID: {invoice.id}) for customer {data.customer_id}")
        return self._to_response(reloaded)

    async def get_invoice(self, invoice_id: uuid.UUID) -> InvoiceResponse:
        """Retrieve an invoice by ID with line items and relations."""
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(
                f"Invoice with ID {invoice_id} not found.",
                details={"invoice_id": str(invoice_id)},
            )
        return self._to_response(invoice)

    async def list_invoices(
        self,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> InvoiceListResponse:
        """List and paginate invoices with optional filtering."""
        invoices = await self.invoice_repo.list_invoices(
            customer_id=customer_id,
            status=status,
            search=search,
            offset=offset,
            limit=limit,
        )
        total = await self.invoice_repo.count_invoices(
            customer_id=customer_id,
            status=status,
            search=search,
        )
        items = [self._to_response(inv) for inv in invoices]
        return InvoiceListResponse(items=items, total=total, offset=offset, limit=limit)

    async def update_invoice(self, invoice_id: uuid.UUID, data: InvoiceUpdate) -> InvoiceResponse:
        """Update invoice attributes prior to terminal settlement."""
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(
                f"Invoice with ID {invoice_id} not found.",
                details={"invoice_id": str(invoice_id)},
            )

        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.VOID]:
            raise ValidationError(
                f"Cannot update invoice in terminal status '{invoice.status.value}'.",
                details={"invoice_id": str(invoice_id), "status": invoice.status.value},
            )

        new_issue_date = data.issue_date or invoice.issue_date
        new_due_date = data.due_date or invoice.due_date
        if new_due_date < new_issue_date:
            raise ValidationError("Invoice due date cannot be earlier than issue date.")

        invoice.issue_date = new_issue_date
        invoice.due_date = new_due_date
        if data.currency:
            invoice.currency = data.currency.upper()

        # Update line items if provided
        if data.line_items is not None:
            if len(invoice.payments) > 0:
                raise ValidationError(
                    "Cannot modify line items or total amounts on an invoice with recorded payments.",
                    details={"payment_count": len(invoice.payments)},
                )

            # Delete existing line items
            for old_item in list(invoice.line_items):
                await self.session.delete(old_item)
            await self.session.flush()

            # Add new line items and recalculate
            computed_total = Decimal("0.00")
            for item in data.line_items:
                qty = Decimal(str(item.quantity))
                price = Decimal(str(item.unit_price))
                computed_total += (qty * price).quantize(Decimal("0.01"))

            invoice.total_amount = computed_total
            invoice.balance_due = computed_total

            await self.invoice_repo.add_line_items(
                invoice.id,
                [item.model_dump() for item in data.line_items],
            )

        await self.session.flush()
        reloaded = await self.invoice_repo.get_with_details(invoice_id)
        return self._to_response(reloaded)

    async def void_invoice(self, invoice_id: uuid.UUID, reason: Optional[str] = None) -> InvoiceResponse:
        """Void an uncollected invoice, setting balance to 0 and logging audit activity."""
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(
                f"Invoice with ID {invoice_id} not found.",
                details={"invoice_id": str(invoice_id)},
            )

        if invoice.status == InvoiceStatus.VOID:
            raise ValidationError("Invoice is already voided.")

        if invoice.status == InvoiceStatus.PAID:
            raise ValidationError("Cannot void a fully paid invoice; process a refund or credit memo first.")

        if len(invoice.payments) > 0:
            raise ValidationError(
                "Cannot void an invoice with applied payments; reverse payments prior to voiding.",
                details={"applied_payments": len(invoice.payments)},
            )

        old_status = invoice.status
        invoice.status = InvoiceStatus.VOID
        invoice.balance_due = Decimal("0.00")

        # Record audit activity
        audit = CollectionActivity(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            activity_type=ActivityType.STATUS_CHANGE,
            performed_by="OPERATOR",
            details={
                "previous_status": old_status.value,
                "new_status": InvoiceStatus.VOID.value,
                "reason": reason or "Voided by operator",
            },
        )
        self.session.add(audit)
        await self.session.flush()

        logger.info(f"Voided invoice {invoice.invoice_number} (ID: {invoice.id})")
        reloaded = await self.invoice_repo.get_with_details(invoice_id)
        return self._to_response(reloaded)

    async def transition_status(self, invoice_id: uuid.UUID, new_status: InvoiceStatus) -> InvoiceResponse:
        """Enforce state machine transitions for invoice lifecycle."""
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice with ID {invoice_id} not found.")

        if invoice.status == InvoiceStatus.VOID:
            raise ValidationError("Cannot change status of a voided invoice.")

        if invoice.status == InvoiceStatus.PAID and new_status != InvoiceStatus.PAID:
            raise ValidationError("Cannot transition a paid invoice without payment reversal.")

        if new_status == InvoiceStatus.PAID and invoice.balance_due > Decimal("0.00"):
            raise ValidationError(
                f"Cannot mark invoice as PAID while balance due is {invoice.balance_due}.",
                details={"balance_due": str(invoice.balance_due)},
            )

        if new_status == InvoiceStatus.VOID:
            return await self.void_invoice(invoice_id)

        old_status = invoice.status
        invoice.status = new_status

        audit = CollectionActivity(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            activity_type=ActivityType.STATUS_CHANGE,
            performed_by="SYSTEM",
            details={"previous_status": old_status.value, "new_status": new_status.value},
        )
        self.session.add(audit)
        await self.session.flush()

        reloaded = await self.invoice_repo.get_with_details(invoice_id)
        return self._to_response(reloaded)

    def _to_response(self, invoice: Invoice) -> InvoiceResponse:
        line_items_resp = [
            InvoiceLineItemResponse(
                id=item.id,
                invoice_id=item.invoice_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                created_at=item.created_at,
            )
            for item in (invoice.line_items or [])
        ]
        return InvoiceResponse(
            id=invoice.id,
            customer_id=invoice.customer_id,
            invoice_number=invoice.invoice_number,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            currency=invoice.currency,
            total_amount=invoice.total_amount,
            balance_due=invoice.balance_due,
            status=invoice.status,
            document_source_id=invoice.document_source_id,
            line_items=line_items_resp,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
        )
