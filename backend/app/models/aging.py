import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice


class AgingBucket(str, enum.Enum):
    CURRENT = "CURRENT"
    DAYS_1_30 = "DAYS_1_30"
    DAYS_31_60 = "DAYS_31_60"
    DAYS_61_90 = "DAYS_61_90"
    DAYS_90_PLUS = "DAYS_90_PLUS"


class AgingSchedule(Base, UUIDMixin):
    """Calculated aging snapshot tracking overdue duration and bucket category."""
    __tablename__ = "aging_schedules"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    days_overdue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bucket: Mapped[AgingBucket] = mapped_column(
        Enum(AgingBucket, name="agingbucket"),
        default=AgingBucket.CURRENT,
        index=True,
        nullable=False,
    )
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="aging_schedule")
