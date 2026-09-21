import csv
import io
from typing import Any, Dict, List

from app.providers.accounting.base import AccountingSyncProvider


class CsvAccountingExporter(AccountingSyncProvider):
    """
    Standard RFC 4180 CSV exporter for accounting ledger synchronization.
    Formats numbers with 2 decimal places and ISO dates for universal ERP compatibility.
    """

    def export_invoices(self, invoices: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        fieldnames = [
            "invoice_number",
            "customer_name",
            "customer_email",
            "issue_date",
            "due_date",
            "currency",
            "total_amount",
            "balance_due",
            "status",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for inv in invoices:
            writer.writerow({
                "invoice_number": inv.get("invoice_number", ""),
                "customer_name": inv.get("customer_name", ""),
                "customer_email": inv.get("customer_email", ""),
                "issue_date": str(inv.get("issue_date", "")),
                "due_date": str(inv.get("due_date", "")),
                "currency": inv.get("currency", "USD"),
                "total_amount": f"{float(inv.get('total_amount', 0)):.2f}",
                "balance_due": f"{float(inv.get('balance_due', 0)):.2f}",
                "status": inv.get("status", ""),
            })

        return output.getvalue()

    def export_payments(self, payments: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        fieldnames = [
            "payment_id",
            "invoice_number",
            "customer_name",
            "payment_date",
            "payment_method",
            "reference_number",
            "amount",
            "notes",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for pay in payments:
            writer.writerow({
                "payment_id": str(pay.get("payment_id", "")),
                "invoice_number": pay.get("invoice_number", ""),
                "customer_name": pay.get("customer_name", ""),
                "payment_date": str(pay.get("payment_date", "")),
                "payment_method": pay.get("payment_method", ""),
                "reference_number": pay.get("reference_number", "") or "",
                "amount": f"{float(pay.get('amount', 0)):.2f}",
                "notes": pay.get("notes", "") or "",
            })

        return output.getvalue()

    def export_reconciliation_ledger(
        self,
        invoices: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
    ) -> str:
        output = io.StringIO()
        fieldnames = [
            "record_type",
            "identifier",
            "customer_name",
            "transaction_date",
            "amount",
            "balance_due",
            "status_or_method",
            "reference_notes",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for inv in invoices:
            writer.writerow({
                "record_type": "INVOICE",
                "identifier": inv.get("invoice_number", ""),
                "customer_name": inv.get("customer_name", ""),
                "transaction_date": str(inv.get("issue_date", "")),
                "amount": f"{float(inv.get('total_amount', 0)):.2f}",
                "balance_due": f"{float(inv.get('balance_due', 0)):.2f}",
                "status_or_method": inv.get("status", ""),
                "reference_notes": f"Due: {inv.get('due_date', '')}",
            })

        for pay in payments:
            writer.writerow({
                "record_type": "PAYMENT",
                "identifier": pay.get("invoice_number", ""),
                "customer_name": pay.get("customer_name", ""),
                "transaction_date": str(pay.get("payment_date", "")),
                "amount": f"-{float(pay.get('amount', 0)):.2f}",
                "balance_due": "0.00",
                "status_or_method": pay.get("payment_method", ""),
                "reference_notes": pay.get("reference_number", "") or pay.get("notes", "") or "",
            })

        return output.getvalue()
