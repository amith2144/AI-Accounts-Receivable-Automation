import abc
from typing import Any, Dict, List


class AccountingSyncProvider(abc.ABC):
    """
    Abstract provider interface for exporting financial ledger data
    to external accounting systems (QuickBooks, Xero, ERPs, CSV).
    Enforces Rule 02 by isolating external accounting integration contracts.
    """

    @abc.abstractmethod
    def export_invoices(self, invoices: List[Dict[str, Any]]) -> str:
        """Export invoice ledger entries into formatted string/stream."""
        pass

    @abc.abstractmethod
    def export_payments(self, payments: List[Dict[str, Any]]) -> str:
        """Export remittance payment records into formatted string/stream."""
        pass

    @abc.abstractmethod
    def export_reconciliation_ledger(
        self,
        invoices: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
    ) -> str:
        """Export combined AR reconciliation report."""
        pass
