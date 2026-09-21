import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository handling Customer persistence, search, directory querying, and balance aggregation."""

    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session)

    async def get_by_email(self, email: str) -> Optional[Customer]:
        """Lookup customer by unique billing email address."""
        stmt = select(Customer).where(func.lower(Customer.email) == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(
        self,
        query: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Customer]:
        """Search customer directory by name, email, or phone with pagination."""
        stmt = select(Customer)
        if query and query.strip():
            term = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Customer.name).like(term),
                    func.lower(Customer.email).like(term),
                    Customer.phone.like(term),
                )
            )
        stmt = stmt.order_by(Customer.name.asc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_search(self, query: Optional[str] = None) -> int:
        """Count total matching customers for search pagination."""
        stmt = select(func.count()).select_from(Customer)
        if query and query.strip():
            term = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Customer.name).like(term),
                    func.lower(Customer.email).like(term),
                    Customer.phone.like(term),
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_with_invoices(self, customer_id: uuid.UUID) -> Optional[Customer]:
        """Retrieve customer with eagerly loaded invoices."""
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.invoices))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_customer_balances(self, customer_id: uuid.UUID) -> Dict[str, Decimal]:
        """Compute aggregated total invoiced amount and remaining outstanding balance for a customer."""
        stmt = select(
            func.coalesce(func.sum(Invoice.total_amount), 0),
            func.coalesce(func.sum(Invoice.balance_due), 0),
        ).where(
            Invoice.customer_id == customer_id,
            Invoice.status != InvoiceStatus.VOID,
        )
        result = await self.session.execute(stmt)
        row = result.first()
        total_invoiced = Decimal(str(row[0])) if row else Decimal("0.00")
        outstanding_balance = Decimal(str(row[1])) if row else Decimal("0.00")
        return {
            "total_invoiced": total_invoiced,
            "outstanding_balance": outstanding_balance,
        }

    async def count_active_invoices(self, customer_id: uuid.UUID) -> int:
        """Count non-void invoices with remaining balance to guard against invalid deletion."""
        stmt = select(func.count()).select_from(Invoice).where(
            Invoice.customer_id == customer_id,
            Invoice.status != InvoiceStatus.VOID,
            Invoice.balance_due > 0,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
