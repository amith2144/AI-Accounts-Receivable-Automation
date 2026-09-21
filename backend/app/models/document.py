import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice


class ExtractionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class DocumentSource(Base, UUIDMixin):
    """Uploaded invoice document metadata and asynchronous extraction status."""
    __tablename__ = "document_sources"

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="extractionstatus"),
        default=ExtractionStatus.QUEUED,
        index=True,
        nullable=False,
    )
    details_data: Mapped[Dict[str, Any]] = mapped_column(
        "extracted_data",
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="document_source",
    )
