import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from app.providers.extraction.base import ExtractedInvoiceData, ExtractedLineItem


class HeuristicMatcher:
    """
    Regex and heuristic rules engine for structured invoice extraction.
    Parses unverified text that has been safely isolated inside delimiter boundaries.
    """

    # Regex patterns for Invoice Number
    INVOICE_NUM_PATTERNS = [
        re.compile(r"\b(?:invoice\s*(?:number|no\.?|#)?|inv\s*#?)\s*[:#]\s*([a-zA-Z0-9\-_/]+)", re.IGNORECASE),
        re.compile(r"\b(INV-[0-9]{3,10}[a-zA-Z0-9\-_]*)\b", re.IGNORECASE),
        re.compile(r"\binvoice\s+(?:number|no\.?)\s+([a-zA-Z0-9\-_/]+)", re.IGNORECASE),
    ]

    # Regex patterns for Customer / Debtor name
    CUSTOMER_PATTERNS = [
        re.compile(r"(?:bill\s*to|billed\s*to|customer|client|invoice\s*to)\s*[:\s]*([^\n\r]{2,80})", re.IGNORECASE),
        re.compile(r"(?:company\s*name)\s*[:\s]*([^\n\r]{2,80})", re.IGNORECASE),
    ]

    # Regex patterns for Total Amount
    TOTAL_PATTERNS = [
        re.compile(r"(?:total\s*(?:amount|due)?|balance\s*due|amount\s*due|grand\s*total|net\s*total)\s*[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))", re.IGNORECASE),
        re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))\s*(?:total|due)", re.IGNORECASE),
    ]

    # Regex patterns for Dates
    ISSUE_DATE_PATTERNS = [
        re.compile(r"(?:invoice\s*date|issue\s*date|date\s*issued|dated)\s*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[a-zA-Z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})", re.IGNORECASE),
        re.compile(r"(?:date)\s*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})", re.IGNORECASE),
    ]

    DUE_DATE_PATTERNS = [
        re.compile(r"(?:due\s*date|payment\s*due(?:\s*by)?|pay\s*by)\s*[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[a-zA-Z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})", re.IGNORECASE),
    ]

    # Pattern for itemized tabular line: (Description) (Quantity) (Unit Price) (Line Total)
    LINE_ITEM_PATTERN = re.compile(
        r"^(.+?)\s+([0-9]+(?:\.[0-9]+)?)\s+\$?([0-9]+(?:\.[0-9]{2}))\s+\$?([0-9]+(?:\.[0-9]{2}))\s*$",
        re.MULTILINE,
    )

    def parse(self, text: str, extraction_method: str = "pymupdf_digital") -> ExtractedInvoiceData:
        """Parses text content and extracts key financial attributes with confidence scoring."""
        invoice_number = self._extract_invoice_number(text)
        customer_name = self._extract_customer_name(text)
        total_amount = self._extract_total_amount(text)
        issue_date = self._extract_date(text, self.ISSUE_DATE_PATTERNS)
        due_date = self._extract_date(text, self.DUE_DATE_PATTERNS)
        line_items = self._extract_line_items(text)

        # Fallback due date to issue date + 30 days if issue date was found
        if issue_date and not due_date:
            from datetime import timedelta
            due_date = issue_date + timedelta(days=30)

        # Confidence calculation
        confidence = self._compute_confidence(
            has_invoice_number=invoice_number is not None,
            has_total_amount=total_amount is not None,
            has_due_date=due_date is not None,
            has_customer_name=customer_name is not None,
            has_line_items=len(line_items) > 0,
        )

        return ExtractedInvoiceData(
            invoice_number=invoice_number,
            customer_name=customer_name,
            issue_date=issue_date,
            due_date=due_date,
            total_amount=total_amount,
            line_items=line_items,
            confidence_score=confidence,
            raw_text=text,
            extraction_method=extraction_method,
        )

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        for pattern in self.INVOICE_NUM_PATTERNS:
            match = pattern.search(text)
            if match:
                inv_num = match.group(1).strip()
                # Basic sanity check
                if len(inv_num) >= 3:
                    return inv_num
        return None

    def _extract_customer_name(self, text: str) -> Optional[str]:
        for pattern in self.CUSTOMER_PATTERNS:
            match = pattern.search(text)
            if match:
                name = match.group(1).strip()
                # Clean trailing punctuation
                name = re.sub(r"[,;:\.]+$", "", name)
                if len(name) >= 2 and not name.lower().startswith("invoice"):
                    return name
        return None

    def _extract_total_amount(self, text: str) -> Optional[Decimal]:
        for pattern in self.TOTAL_PATTERNS:
            match = pattern.search(text)
            if match:
                raw_amt = match.group(1).replace(",", "").strip()
                try:
                    return Decimal(raw_amt)
                except Exception:
                    continue
        return None

    def _extract_date(self, text: str, patterns: List[re.Pattern]) -> Optional[date]:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                raw_date = match.group(1).strip()
                parsed = self._parse_date_string(raw_date)
                if parsed:
                    return parsed
        return None

    def _parse_date_string(self, raw_str: str) -> Optional[date]:
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%Y/%m/%d",
        ]
        # Clean string
        cleaned = re.sub(r"\s+", " ", raw_str).strip()
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        return None

    def _extract_line_items(self, text: str) -> List[ExtractedLineItem]:
        items: List[ExtractedLineItem] = []
        for match in self.LINE_ITEM_PATTERN.finditer(text):
            desc = match.group(1).strip()
            qty_str = match.group(2).strip()
            price_str = match.group(3).strip()
            total_str = match.group(4).strip()
            try:
                qty = Decimal(qty_str)
                price = Decimal(price_str)
                total = Decimal(total_str)
                items.append(
                    ExtractedLineItem(
                        description=desc,
                        quantity=qty,
                        unit_price=price,
                        line_total=total,
                    )
                )
            except Exception:
                continue
        return items

    def _compute_confidence(
        self,
        has_invoice_number: bool,
        has_total_amount: bool,
        has_due_date: bool,
        has_customer_name: bool,
        has_line_items: bool,
    ) -> float:
        score = 0.0
        if has_invoice_number:
            score += 0.30
        if has_total_amount:
            score += 0.30
        if has_due_date:
            score += 0.20
        if has_customer_name:
            score += 0.10
        if has_line_items:
            score += 0.10
        return round(score, 2)
