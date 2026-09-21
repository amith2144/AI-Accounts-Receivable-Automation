from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class ExtractedLineItem(BaseModel):
    """Structured line item parsed from invoice document."""
    description: str
    quantity: Decimal = Decimal("1.00")
    unit_price: Decimal
    line_total: Decimal


class ExtractedInvoiceData(BaseModel):
    """Normalized payload produced by DocumentExtractionProvider."""
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[Decimal] = None
    currency: str = "USD"
    line_items: List[ExtractedLineItem] = Field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 to 1.0 confidence score
    raw_text: str = ""
    isolated_text: str = ""
    extraction_method: str = "pymupdf_digital"  # "pymupdf_digital", "tesseract_ocr", "heuristic"


class DocumentExtractionProvider(ABC):
    """
    Abstract Document Extraction Provider Interface.
    Enforces Standard 9 & Rule 02 by isolating document OCR, heuristics, and text parsing
    behind an interface contract with strict delimiter isolation against prompt/command injection.
    """

    DELIMITER_START: str = "[EXTRACTED_DOCUMENT_TEXT]"
    DELIMITER_END: str = "[/EXTRACTED_DOCUMENT_TEXT]"

    @abstractmethod
    def extract_from_bytes(self, file_bytes: bytes, mime_type: str = "application/pdf") -> ExtractedInvoiceData:
        """
        Parses binary invoice document (PDF or image) and extracts structured financial fields.
        """
        pass

    def isolate_text(self, raw_text: str) -> str:
        """
        Standard 9 (Delimiter Isolation):
        Safely isolates untrusted extracted document text inside explicit boundaries
        to prevent command/prompt injection into downstream processing or AI reasoning.
        """
        # Sanitize any accidental closing delimiters inside the text itself
        sanitized = raw_text.replace(self.DELIMITER_END, "\\[/EXTRACTED_DOCUMENT_TEXT\\]")
        return f"{self.DELIMITER_START}\n{sanitized}\n{self.DELIMITER_END}"
