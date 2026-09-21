import enum
from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class ReminderTone(str, enum.Enum):
    FRIENDLY = "FRIENDLY"
    STANDARD = "STANDARD"
    FIRM = "FIRM"
    URGENT = "URGENT"


class ReminderCadence(Base, UUIDMixin, TimestampMixin):
    """Configurable reminder schedule and messaging templates for overdue outreach."""
    __tablename__ = "reminder_cadences"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_offset_days: Mapped[int] = mapped_column(Integer, nullable=False)
    reminder_tone: Mapped[ReminderTone] = mapped_column(
        Enum(ReminderTone, name="remindertone"),
        default=ReminderTone.STANDARD,
        nullable=False,
    )
    email_subject_template: Mapped[str] = mapped_column(String(255), nullable=False)
    email_body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
