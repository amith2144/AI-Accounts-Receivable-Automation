from app.providers.accounting.base import AccountingSyncProvider
from app.providers.accounting.csv_exporter import CsvAccountingExporter


def get_accounting_exporter() -> AccountingSyncProvider:
    """Factory returning default accounting export provider."""
    return CsvAccountingExporter()


__all__ = [
    "AccountingSyncProvider",
    "CsvAccountingExporter",
    "get_accounting_exporter",
]
