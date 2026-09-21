import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.payment import InvoiceLineItem, PaymentRecord
    from app.models.aging import AgingSchedule
    from app.models.activity import CollectionActivity
    from app.models.document import DocumentSource


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    VOID = "VOID"


class Invoice(Base, UUIDMixin, TimestampMixin):
    """Invoice entity representing receivables, balances, and collection state."""
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("customer_id", "invoice_number", name="uq_customer_invoice_number"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    invoice_number: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoicestatus"),
        default=InvoiceStatus.DRAFT,
        index=True,
        nullable=False,
    )
    document_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
    line_items: Mapped[List["InvoiceLineItem"]] = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["PaymentRecord"]] = relationship(
        "PaymentRecord",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    aging_schedule: Mapped[Optional["AgingSchedule"]] = relationship(
        "AgingSchedule",
        back_populates="invoice",
        uselist=False,
        cascade="all, delete-orphan",
    )
    collection_activities: Mapped[List["CollectionActivity"]] = relationship(
        "CollectionActivity",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    document_source: Mapped[Optional["DocumentSource"]] = relationship(
        "DocumentSource",
        back_populates="invoices",
    )
