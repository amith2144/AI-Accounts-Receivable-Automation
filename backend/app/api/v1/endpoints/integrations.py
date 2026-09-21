from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import PaymentRecord
from app.providers.accounting import get_accounting_exporter
from app.schemas.auth import UserProfile

router = APIRouter(prefix="/integrations", tags=["Integrations & Accounting"])


@router.get("/accounting/export")
async def export_accounting_ledger(
    export_type: str = Query("invoices", description="Type of export: invoices, payments, or reconciliation"),
    format: str = Query("csv", description="Output format: csv or json"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> Response:
    """
    Generate standardized RFC 4180 CSV or JSON export of Accounts Receivable ledger entries
    (invoices, payments, or combined reconciliation) for ingestion into external ERPs/accounting systems.
    """
    exporter = get_accounting_exporter()

    # 1. Fetch Invoices if required
    invoices_data: List[Dict[str, Any]] = []
    if export_type in ["invoices", "reconciliation"]:
        inv_stmt = (
            select(Invoice)
            .options(joinedload(Invoice.customer))
            .where(Invoice.status != InvoiceStatus.VOID)
            .order_by(Invoice.issue_date.desc(), Invoice.invoice_number)
        )
        if start_date:
            inv_stmt = inv_stmt.where(Invoice.issue_date >= start_date)
        if end_date:
            inv_stmt = inv_stmt.where(Invoice.issue_date <= end_date)

        inv_result = await db.execute(inv_stmt)
        invoices = inv_result.scalars().all()

        for inv in invoices:
            invoices_data.append({
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer.name if inv.customer else "",
                "customer_email": inv.customer.email if inv.customer else "",
                "issue_date": inv.issue_date.isoformat(),
                "due_date": inv.due_date.isoformat(),
                "currency": inv.currency,
                "total_amount": float(inv.total_amount),
                "balance_due": float(inv.balance_due),
                "status": inv.status.value,
            })

    # 2. Fetch Payments if required
    payments_data: List[Dict[str, Any]] = []
    if export_type in ["payments", "reconciliation"]:
        pay_stmt = (
            select(PaymentRecord)
            .options(joinedload(PaymentRecord.invoice).joinedload(Invoice.customer))
            .order_by(PaymentRecord.payment_date.desc())
        )
        if start_date:
            pay_stmt = pay_stmt.where(PaymentRecord.payment_date >= start_date)
        if end_date:
            pay_stmt = pay_stmt.where(PaymentRecord.payment_date <= end_date)

        pay_result = await db.execute(pay_stmt)
        payments = pay_result.scalars().all()

        for pay in payments:
            payments_data.append({
                "payment_id": str(pay.id),
                "invoice_number": pay.invoice.invoice_number if pay.invoice else "",
                "customer_name": pay.invoice.customer.name if (pay.invoice and pay.invoice.customer) else "",
                "payment_date": pay.payment_date.isoformat(),
                "payment_method": pay.payment_method.value,
                "reference_number": pay.reference_number or "",
                "amount": float(pay.amount),
                "notes": pay.notes or "",
            })

    # 3. Format as JSON if requested
    if format.lower() == "json":
        if export_type == "invoices":
            payload = {"invoices": invoices_data, "count": len(invoices_data)}
        elif export_type == "payments":
            payload = {"payments": payments_data, "count": len(payments_data)}
        else:
            payload = {
                "invoices": invoices_data,
                "payments": payments_data,
                "total_invoices": len(invoices_data),
                "total_payments": len(payments_data),
            }
        return JSONResponse(content=payload)

    # 4. Format as RFC 4180 CSV
    today_str = date.today().isoformat()
    if export_type == "invoices":
        csv_content = exporter.export_invoices(invoices_data)
        filename = f"accounting_invoices_{today_str}.csv"
    elif export_type == "payments":
        csv_content = exporter.export_payments(payments_data)
        filename = f"accounting_payments_{today_str}.csv"
    else:
        csv_content = exporter.export_reconciliation_ledger(invoices_data, payments_data)
        filename = f"accounting_reconciliation_{today_str}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
