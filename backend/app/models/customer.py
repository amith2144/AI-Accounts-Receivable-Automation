from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.activity import CollectionActivity


class Customer(Base, UUIDMixin, TimestampMixin):
    """Customer entity representing debtor accounts and communication controls."""
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    reminder_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    collection_activities: Mapped[List["CollectionActivity"]] = relationship(
        "CollectionActivity",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
