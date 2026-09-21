from app.providers.extraction.base import (
    DocumentExtractionProvider,
    ExtractedInvoiceData,
    ExtractedLineItem,
)
from app.providers.extraction.heuristic_matcher import HeuristicMatcher
from app.providers.extraction.pymupdf_parser import PyMuPDFExtractionProvider


def get_extraction_provider() -> DocumentExtractionProvider:
    """Factory returning default DocumentExtractionProvider."""
    return PyMuPDFExtractionProvider()


__all__ = [
    "DocumentExtractionProvider",
    "ExtractedInvoiceData",
    "ExtractedLineItem",
    "HeuristicMatcher",
    "PyMuPDFExtractionProvider",
    "get_extraction_provider",
]
