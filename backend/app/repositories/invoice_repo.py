import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import InvoiceLineItem
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository managing Invoice persistence, eager relations, filtering, and balance aggregations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Invoice, session)

    async def get_by_customer_and_number(
        self,
        customer_id: uuid.UUID,
        invoice_number: str,
    ) -> Optional[Invoice]:
        """Lookup an invoice by tenant customer ID and invoice number (unique per debtor)."""
        stmt = select(Invoice).where(
            Invoice.customer_id == customer_id,
            func.lower(Invoice.invoice_number) == invoice_number.strip().lower(),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_details(
        self,
        invoice_id: uuid.UUID,
        for_update: bool = False,
    ) -> Optional[Invoice]:
        """Retrieve an invoice with eagerly loaded line items, payments, and document source."""
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                selectinload(Invoice.line_items),
                selectinload(Invoice.payments),
                selectinload(Invoice.customer),
                selectinload(Invoice.document_source),
                selectinload(Invoice.aging_schedule),
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_invoices(
        self,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Invoice]:
        """Filter and paginate invoices with line items loaded."""
        stmt = select(Invoice).options(selectinload(Invoice.line_items))

        if customer_id:
            stmt = stmt.where(Invoice.customer_id == customer_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(Invoice.invoice_number).like(term))

        stmt = stmt.order_by(Invoice.due_date.asc(), Invoice.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_invoices(
        self,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count invoices matching given filter criteria."""
        stmt = select(func.count()).select_from(Invoice)

        if customer_id:
            stmt = stmt.where(Invoice.customer_id == customer_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(Invoice.invoice_number).like(term))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_overdue_invoices(self, as_of_date: date) -> Sequence[Invoice]:
        """Retrieve all active unpaid invoices whose due date is past the target date."""
        stmt = (
            select(Invoice)
            .where(
                Invoice.due_date < as_of_date,
                Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.VOID]),
                Invoice.balance_due > 0,
            )
            .options(selectinload(Invoice.customer))
            .order_by(Invoice.due_date.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_line_items(
        self,
        invoice_id: uuid.UUID,
        line_items: List[Dict[str, Any]],
    ) -> List[InvoiceLineItem]:
        """Persist line items linked to an invoice."""
        created_items = []
        for item_data in line_items:
            qty = Decimal(str(item_data["quantity"]))
            price = Decimal(str(item_data["unit_price"]))
            total = qty * price
            line_item = InvoiceLineItem(
                invoice_id=invoice_id,
                description=item_data["description"].strip(),
                quantity=qty,
                unit_price=price,
                line_total=total,
            )
            self.session.add(line_item)
            created_items.append(line_item)
        await self.session.flush()
        return created_items
