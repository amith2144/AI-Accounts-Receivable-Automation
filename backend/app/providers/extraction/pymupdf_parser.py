import io
import logging
from typing import Optional
import fitz  # PyMuPDF
from PIL import Image

from app.core.config import settings
from app.providers.extraction.base import DocumentExtractionProvider, ExtractedInvoiceData
from app.providers.extraction.heuristic_matcher import HeuristicMatcher

logger = logging.getLogger("app.providers.extraction.pymupdf")


class PyMuPDFExtractionProvider(DocumentExtractionProvider):
    """
    Multi-tier document parser combining high-performance PyMuPDF digital extraction
    with Tesseract OCR fallback for scanned images, protected by delimiter isolation (Standard 9).
    """

    def __init__(self, matcher: Optional[HeuristicMatcher] = None):
        self.matcher = matcher or HeuristicMatcher()
        if settings.TESSERACT_CMD:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def extract_from_bytes(
        self,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
    ) -> ExtractedInvoiceData:
        """
        Parses document binary data using digital text extraction with OCR fallback.
        """
        raw_text = ""
        extraction_method = "pymupdf_digital"

        if mime_type == "application/pdf" or file_bytes.startswith(b"%PDF"):
            raw_text, extraction_method = self._extract_from_pdf(file_bytes)
        elif mime_type.startswith("image/") or file_bytes[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1"):
            raw_text, extraction_method = self._extract_from_image(file_bytes)
        else:
            # Fallback text attempt
            try:
                raw_text, extraction_method = self._extract_from_pdf(file_bytes)
            except Exception:
                raw_text = ""

        # Standard 9: Enforce Delimiter Isolation around raw extracted document text
        isolated_text = self.isolate_text(raw_text)

        # Parse isolated text through heuristic pattern matcher
        extracted_data = self.matcher.parse(isolated_text, extraction_method=extraction_method)
        extracted_data.raw_text = raw_text
        extracted_data.isolated_text = isolated_text
        return extracted_data

    def _extract_from_pdf(self, file_bytes: bytes) -> tuple[str, str]:
        """Extracts text from PDF pages using PyMuPDF with OCR fallback for scanned pages."""
        text_parts = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(page_text)

        full_digital_text = "\n".join(text_parts).strip()

        # If digital text is rich enough, return immediately (fastest path)
        if len(full_digital_text) >= 50:
            doc.close()
            return full_digital_text, "pymupdf_digital"

        # Fallback to OCR if digital text is empty/sparse (scanned PDF)
        if settings.OCR_ENABLED:
            logger.info("Digital text sparse (< 50 chars); initiating Tesseract OCR fallback for PDF...")
            ocr_parts = []
            for page_index in range(len(doc)):
                page = doc[page_index]
                try:
                    # Render page to pixmap image for optical recognition
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    import pytesseract
                    page_ocr = pytesseract.image_to_string(img)
                    if page_ocr.strip():
                        ocr_parts.append(page_ocr)
                except Exception as ocr_err:
                    logger.warning(f"OCR failed for PDF page {page_index}: {str(ocr_err)}")

            doc.close()
            ocr_text = "\n".join(ocr_parts).strip()
            if ocr_text:
                return ocr_text, "tesseract_ocr"

        doc.close()
        return full_digital_text, "pymupdf_digital"

    def _extract_from_image(self, file_bytes: bytes) -> tuple[str, str]:
        """Extracts text from raw image bytes using Tesseract OCR."""
        if not settings.OCR_ENABLED:
            logger.warning("OCR is disabled; cannot extract text from image.")
            return "", "ocr_disabled"

        try:
            img = Image.open(io.BytesIO(file_bytes))
            import pytesseract
            text = pytesseract.image_to_string(img)
            return text.strip(), "tesseract_ocr"
        except Exception as exc:
            logger.warning(f"Image OCR extraction error: {str(exc)}")
            return "", "tesseract_ocr_error"
