import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.customer import Customer
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)

logger = logging.getLogger("app.services.customer")


class CustomerService:
    """
    Domain service for debtor management, directory search, terms configuration,
    and reminder suspension controls. Enforces Rule 02 by isolating business rules.
    """

    def __init__(self, session: AsyncSession, customer_repo: Optional[CustomerRepository] = None):
        self.session = session
        self.customer_repo = customer_repo or CustomerRepository(session)

    async def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        """Create a new debtor account with unique email enforcement and valid terms."""
        normalized_email = data.email.lower().strip()
        existing = await self.customer_repo.get_by_email(normalized_email)
        if existing:
            raise ConflictError(
                f"A customer with email '{normalized_email}' already exists.",
                details={"email": normalized_email, "customer_id": str(existing.id)},
            )

        if data.payment_terms_days < 0:
            raise ValidationError(
                "Payment terms days cannot be negative.",
                details={"payment_terms_days": data.payment_terms_days},
            )

        customer = await self.customer_repo.create(
            Customer(
                name=data.name.strip(),
                email=normalized_email,
                phone=data.phone.strip() if data.phone else None,
                payment_terms_days=data.payment_terms_days,
                reminder_paused=data.reminder_paused,
            )
        )
        logger.info(f"Created customer '{customer.name}' with ID {customer.id}")

        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            payment_terms_days=customer.payment_terms_days,
            reminder_paused=customer.reminder_paused,
            total_invoiced=0,
            outstanding_balance=0,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )

    async def get_customer(self, customer_id: uuid.UUID) -> CustomerResponse:
        """Retrieve customer details with aggregate invoiced and outstanding balances."""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise NotFoundError(
                f"Customer with ID {customer_id} not found.",
                details={"customer_id": str(customer_id)},
            )

        balances = await self.customer_repo.get_customer_balances(customer_id)

        return CustomerResponse(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            payment_terms_days=customer.payment_terms_days,
            reminder_paused=customer.reminder_paused,
            total_invoiced=balances["total_invoiced"],
            outstanding_balance=balances["outstanding_balance"],
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )

    async def list_customers(
        self,
        query: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CustomerListResponse:
        """Search and paginate customer directory with balance rollups."""
        customers = await self.customer_repo.search(query=query, offset=offset, limit=limit)
        total = await self.customer_repo.count_search(query=query)

        items = []
        for c in customers:
            balances = await self.customer_repo.get_customer_balances(c.id)
            items.append(
                CustomerResponse(
                    id=c.id,
                    name=c.name,
                    email=c.email,
                    phone=c.phone,
                    payment_terms_days=c.payment_terms_days,
                    reminder_paused=c.reminder_paused,
                    total_invoiced=balances["total_invoiced"],
                    outstanding_balance=balances["outstanding_balance"],
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )

        return CustomerListResponse(items=items, total=total, offset=offset, limit=limit)

    async def update_customer(self, customer_id: uuid.UUID, data: CustomerUpdate) -> CustomerResponse:
        """Update customer details, verifying uniqueness when email changes."""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise NotFoundError(
                f"Customer with ID {customer_id} not found.",
                details={"customer_id": str(customer_id)},
            )

        update_dict = data.model_dump(exclude_unset=True)

        if "email" in update_dict and update_dict["email"] is not None:
            new_email = update_dict["email"].lower().strip()
            if new_email != customer.email.lower():
                existing = await self.customer_repo.get_by_email(new_email)
                if existing and existing.id != customer_id:
                    raise ConflictError(
                        f"Email '{new_email}' is already in use by another customer.",
                        details={"email": new_email},
                    )
            update_dict["email"] = new_email

        if "payment_terms_days" in update_dict and update_dict["payment_terms_days"] is not None:
            if update_dict["payment_terms_days"] < 0:
                raise ValidationError("Payment terms days cannot be negative.")

        updated_customer = await self.customer_repo.update(customer, update_dict)
        balances = await self.customer_repo.get_customer_balances(customer_id)

        return CustomerResponse(
            id=updated_customer.id,
            name=updated_customer.name,
            email=updated_customer.email,
            phone=updated_customer.phone,
            payment_terms_days=updated_customer.payment_terms_days,
            reminder_paused=updated_customer.reminder_paused,
            total_invoiced=balances["total_invoiced"],
            outstanding_balance=balances["outstanding_balance"],
            created_at=updated_customer.created_at,
            updated_at=updated_customer.updated_at,
        )

    async def toggle_reminder_pause(self, customer_id: uuid.UUID, pause: bool) -> CustomerResponse:
        """Suspend or resume automated collection reminder outreach for a debtor."""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise NotFoundError(
                f"Customer with ID {customer_id} not found.",
                details={"customer_id": str(customer_id)},
            )

        updated_customer = await self.customer_repo.update(customer, {"reminder_paused": pause})
        logger.info(f"Toggled reminder_paused={pause} for customer {customer_id}")
        balances = await self.customer_repo.get_customer_balances(customer_id)

        return CustomerResponse(
            id=updated_customer.id,
            name=updated_customer.name,
            email=updated_customer.email,
            phone=updated_customer.phone,
            payment_terms_days=updated_customer.payment_terms_days,
            reminder_paused=updated_customer.reminder_paused,
            total_invoiced=balances["total_invoiced"],
            outstanding_balance=balances["outstanding_balance"],
            created_at=updated_customer.created_at,
            updated_at=updated_customer.updated_at,
        )

    async def delete_customer(self, customer_id: uuid.UUID) -> bool:
        """Soft/hard delete customer account, blocked if active invoices exist."""
        customer = await self.customer_repo.get(customer_id)
        if not customer:
            raise NotFoundError(
                f"Customer with ID {customer_id} not found.",
                details={"customer_id": str(customer_id)},
            )

        active_count = await self.customer_repo.count_active_invoices(customer_id)
        if active_count > 0:
            raise ConflictError(
                f"Cannot delete customer {customer_id} because they have {active_count} active invoice(s).",
                details={"customer_id": str(customer_id), "active_invoices": active_count},
            )

        deleted = await self.customer_repo.delete(customer_id)
        logger.info(f"Deleted customer {customer_id}")
        return deleted
