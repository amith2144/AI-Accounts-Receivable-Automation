import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.invoice import Invoice


class ActivityType(str, enum.Enum):
    REMINDER_SENT = "REMINDER_SENT"
    MANUAL_NOTE = "MANUAL_NOTE"
    CALL_LOGGED = "CALL_LOGGED"
    STATUS_CHANGE = "STATUS_CHANGE"
    PAYMENT_APPLIED = "PAYMENT_APPLIED"


class CollectionActivity(Base, UUIDMixin):
    """Immutable audit trail entry documenting collection communications and lifecycle changes."""
    __tablename__ = "collection_activities"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activitytype"),
        nullable=False,
    )
    performed_by: Mapped[str] = mapped_column(
        String(255),
        default="SYSTEM_AUTOMATION",
        nullable=False,
    )
    # JSON with JSONB fallback on PostgreSQL for fast queries
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="collection_activities")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="collection_activities")
