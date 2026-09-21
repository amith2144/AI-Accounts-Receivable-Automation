import datetime
import logging
import uuid
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.document import DocumentSource, ExtractionStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.customer_repo import CustomerRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.schemas.customer import CustomerCreate
from app.schemas.invoice import (
    InvoiceConfirmationRequest,
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceResponse,
)
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService

logger = logging.getLogger("app.services.verification")


class InvoiceVerificationService:
    """
    Domain service for human-in-the-loop invoice document verification.
    Transforms staged DocumentSource extracted data into active ledger Invoices.
    Enforces Rule 02 and Rule 03.
    """

    def __init__(
        self,
        session: AsyncSession,
        invoice_service: Optional[InvoiceService] = None,
        customer_service: Optional[CustomerService] = None,
        customer_repo: Optional[CustomerRepository] = None,
        invoice_repo: Optional[InvoiceRepository] = None,
    ):
        self.session = session
        self.customer_repo = customer_repo or CustomerRepository(session)
        self.invoice_repo = invoice_repo or InvoiceRepository(session)
        self.customer_service = customer_service or CustomerService(session, self.customer_repo)
        self.invoice_service = invoice_service or InvoiceService(session, self.invoice_repo, self.customer_repo)

    async def verify_and_create_invoice(
        self,
        document_source_id: uuid.UUID,
        data: Optional[InvoiceConfirmationRequest] = None,
    ) -> InvoiceResponse:
        """
        Convert approved or operator-corrected DocumentSource data into an active Invoice.
        Validates extraction state, resolves debtor customer, checks for duplicates,
        and links source document provenance.
        """
        # 1. Fetch DocumentSource
        stmt = select(DocumentSource).where(DocumentSource.id == document_source_id)
        result = await self.session.execute(stmt)
        doc = result.scalars().first()
        if not doc:
            raise NotFoundError(
                f"DocumentSource with ID {document_source_id} not found.",
                details={"document_source_id": str(document_source_id)},
            )

        # 2. Check extraction readiness
        if doc.extraction_status in [ExtractionStatus.QUEUED, ExtractionStatus.PROCESSING]:
            raise ValidationError(
                "Document extraction is still in progress. Please wait for completion before confirming.",
                details={"status": doc.extraction_status.value},
            )

        if doc.extraction_status == ExtractionStatus.FAILED and (
            not data or not data.invoice_number or not (data.total_amount or data.line_items)
        ):
            raise ValidationError(
                "Cannot confirm invoice from failed extraction without providing required manual fields (invoice_number, total_amount).",
                details={"status": doc.extraction_status.value},
            )

        # 3. Guard against duplicate invoice conversion
        check_stmt = select(Invoice).where(Invoice.document_source_id == document_source_id)
        check_res = await self.session.execute(check_stmt)
        existing_invoice = check_res.scalars().first()
        if existing_invoice:
            raise ConflictError(
                f"An invoice ({existing_invoice.invoice_number}) has already been confirmed for this document.",
                details={"existing_invoice_id": str(existing_invoice.id)},
            )

        # 4. Resolve debtor customer
        customer_id: uuid.UUID
        customer_terms_days = 30

        if data and data.customer_id:
            customer = await self.customer_repo.get(data.customer_id)
            if not customer:
                raise NotFoundError(f"Customer with ID {data.customer_id} not found.")
            customer_id = customer.id
            customer_terms_days = customer.payment_terms_days
        else:
            cust_name = (data.customer_name if data and data.customer_name else None) or doc.details_data.get("customer_name")
            cust_email = (data.customer_email if data and data.customer_email else None)

            if cust_email:
                existing_cust = await self.customer_repo.get_by_email(cust_email)
                if existing_cust:
                    customer_id = existing_cust.id
                    customer_terms_days = existing_cust.payment_terms_days
                else:
                    new_cust = await self.customer_service.create_customer(
                        CustomerCreate(
                            name=cust_name.strip() if cust_name else "Unknown Customer",
                            email=cust_email,
                            payment_terms_days=30,
                        )
                    )
                    customer_id = new_cust.id
            elif cust_name and cust_name.strip():
                # Search by customer name
                matches = await self.customer_repo.search(query=cust_name.strip(), limit=1)
                if matches and matches[0].name.lower() == cust_name.strip().lower():
                    customer_id = matches[0].id
                    customer_terms_days = matches[0].payment_terms_days
                else:
                    raise ValidationError(
                        f"Could not automatically match customer '{cust_name}'. Please select or create customer manually.",
                        details={"customer_name": cust_name},
                    )
            else:
                raise ValidationError(
                    "No customer identified. Please assign a customer_id or provide customer details to confirm import."
                )

        # 5. Resolve invoice number
        invoice_num = (data.invoice_number if data and data.invoice_number else None) or doc.details_data.get("invoice_number")
        if not invoice_num or not invoice_num.strip():
            raise ValidationError("Invoice number could not be determined. Please supply invoice_number.")
        invoice_num = invoice_num.strip()

        # 6. Resolve dates
        issue_date: datetime.date
        if data and data.issue_date:
            issue_date = data.issue_date
        elif doc.details_data.get("issue_date"):
            try:
                issue_date = datetime.date.fromisoformat(doc.details_data["issue_date"])
            except ValueError:
                issue_date = datetime.date.today()
        else:
            issue_date = datetime.date.today()

        due_date: datetime.date
        if data and data.due_date:
            due_date = data.due_date
        elif doc.details_data.get("due_date"):
            try:
                due_date = datetime.date.fromisoformat(doc.details_data["due_date"])
            except ValueError:
                due_date = issue_date + datetime.timedelta(days=customer_terms_days)
        else:
            due_date = issue_date + datetime.timedelta(days=customer_terms_days)

        if due_date < issue_date:
            due_date = issue_date + datetime.timedelta(days=customer_terms_days)

        # 7. Resolve currency
        currency = (data.currency if data and data.currency else None) or doc.details_data.get("currency") or "USD"

        # 8. Resolve line items and total
        line_items: List[InvoiceLineItemCreate] = []
        if data and data.line_items is not None:
            line_items = data.line_items
        elif doc.details_data.get("line_items"):
            for item_dict in doc.details_data["line_items"]:
                qty = Decimal(str(item_dict.get("quantity", "1.00")))
                price = Decimal(str(item_dict.get("unit_price", "0.00")))
                line_items.append(
                    InvoiceLineItemCreate(
                        description=item_dict.get("description", "Item charge"),
                        quantity=qty,
                        unit_price=price,
                    )
                )

        total_amount: Optional[Decimal] = None
        if data and data.total_amount is not None:
            total_amount = data.total_amount
        elif doc.details_data.get("total_amount"):
            try:
                total_amount = Decimal(str(doc.details_data["total_amount"]))
            except Exception:
                total_amount = None

        # 9. Create active invoice record via InvoiceService
        create_payload = InvoiceCreate(
            customer_id=customer_id,
            invoice_number=invoice_num,
            issue_date=issue_date,
            due_date=due_date,
            currency=currency,
            total_amount=total_amount,
            line_items=line_items,
            status=InvoiceStatus.ISSUED,
            document_source_id=document_source_id,
        )

        invoice_response = await self.invoice_service.create_invoice(create_payload)
        logger.info(
            f"Successfully confirmed and created active invoice {invoice_response.invoice_number} "
            f"from DocumentSource {document_source_id}"
        )

        return invoice_response
