"""
Generate realistic B2B invoice PDFs for local testing and live demo video recordings.
Uses PyMuPDF (fitz) to create structured, professional invoices that match the regex/OCR extraction engine.
"""

import os
from datetime import date, timedelta
import fitz  # PyMuPDF


def create_invoice_pdf(output_path: str, data: dict):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Standard Letter size

    # Background styling: clean modern white with dark slate accents
    # Top banner header
    rect_header = fitz.Rect(36, 36, 576, 110)
    page.draw_rect(rect_header, color=None, fill=(0.08, 0.12, 0.18))  # Dark slate navy

    # Company Branding
    page.insert_text(
        fitz.Point(52, 68),
        data["issuer_name"].upper(),
        fontsize=18,
        fontname="helv",
        color=(1, 1, 1),
    )
    page.insert_text(
        fitz.Point(52, 86),
        data["issuer_tagline"],
        fontsize=9,
        fontname="helv",
        color=(0.6, 0.7, 0.8),
    )

    # Invoice Title & Number in banner
    page.insert_text(
        fitz.Point(400, 68),
        "COMMERCIAL INVOICE",
        fontsize=12,
        fontname="helv",
        color=(0.8, 0.85, 0.95),
    )
    page.insert_text(
        fitz.Point(400, 92),
        f"Invoice #: {data['invoice_number']}",
        fontsize=13,
        fontname="helv",
        color=(1, 1, 1),
    )

    # Billing & Metadata Section
    y = 140
    # Left: Bill To
    page.insert_text(fitz.Point(52, y), "BILL TO:", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(52, y + 16), data["customer_name"], fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(52, y + 32), data["customer_address"], fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(52, y + 46), f"Contact: {data['customer_email']}", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))

    # Right: Dates & Terms
    page.insert_text(fitz.Point(380, y), "INVOICE DETAILS:", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(380, y + 16), f"Invoice Date: {data['issue_date']}", fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(380, y + 32), f"Due Date: {data['due_date']}", fontsize=10, fontname="helv", color=(0.8, 0.1, 0.1) if "overdue" in data.get("note", "").lower() else (0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(380, y + 48), f"Payment Terms: {data['payment_terms']}", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))

    # Divider
    page.draw_line(fitz.Point(36, 215), fitz.Point(576, 215), color=(0.85, 0.88, 0.9), width=1)

    # Line Items Table Header
    y_table = 240
    rect_th = fitz.Rect(36, y_table - 14, 576, y_table + 8)
    page.draw_rect(rect_th, color=None, fill=(0.95, 0.96, 0.98))
    page.insert_text(fitz.Point(52, y_table), "ITEM & SERVICE DESCRIPTION", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.3))
    page.insert_text(fitz.Point(340, y_table), "QTY", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.3))
    page.insert_text(fitz.Point(410, y_table), "UNIT PRICE", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.3))
    page.insert_text(fitz.Point(500, y_table), "TOTAL", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.3))

    # Line Items Rows
    current_y = y_table + 24
    for item in data["line_items"]:
        # Description
        page.insert_text(fitz.Point(52, current_y), item["desc"], fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
        # Qty
        page.insert_text(fitz.Point(340, current_y), str(item["qty"]), fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
        # Unit Price
        page.insert_text(fitz.Point(410, current_y), f"${item['unit_price']:,.2f}", fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
        # Line Total
        page.insert_text(fitz.Point(500, current_y), f"${item['total']:,.2f}", fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
        
        # Row bottom hairline
        page.draw_line(fitz.Point(36, current_y + 8), fitz.Point(576, current_y + 8), color=(0.92, 0.94, 0.95), width=0.5)
        current_y += 24

    # Summary Totals Box
    y_totals = current_y + 20
    rect_tot = fitz.Rect(350, y_totals - 10, 576, y_totals + 70)
    page.draw_rect(rect_tot, color=(0.85, 0.88, 0.9), fill=(0.97, 0.98, 1.0), width=1)

    page.insert_text(fitz.Point(365, y_totals + 10), "Subtotal:", fontsize=10, fontname="helv", color=(0.3, 0.35, 0.4))
    page.insert_text(fitz.Point(490, y_totals + 10), f"${data['total_amount']:,.2f}", fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))

    page.insert_text(fitz.Point(365, y_totals + 32), "Sales Tax (0.0% B2B):", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(510, y_totals + 32), "$0.00", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.5))

    page.draw_line(fitz.Point(365, y_totals + 42), fitz.Point(560, y_totals + 42), color=(0.8, 0.85, 0.9), width=1)

    page.insert_text(fitz.Point(365, y_totals + 60), "Total Due:", fontsize=12, fontname="helv", color=(0.08, 0.12, 0.18))
    page.insert_text(fitz.Point(475, y_totals + 60), f"${data['total_amount']:,.2f}", fontsize=13, fontname="helv", color=(0.08, 0.12, 0.18))

    # Remittance Instructions & Notes at Bottom
    y_footer = 640
    page.draw_line(fitz.Point(36, y_footer), fitz.Point(576, y_footer), color=(0.85, 0.88, 0.9), width=1)
    page.insert_text(fitz.Point(52, y_footer + 20), "REMITTANCE & WIRE INSTRUCTIONS:", fontsize=9, fontname="helv", color=(0.4, 0.45, 0.5))
    page.insert_text(fitz.Point(52, y_footer + 35), "Bank: JPMorgan Chase Bank, N.A. | Routing: 021000021 | Acct: 8849201934", fontsize=8.5, fontname="helv", color=(0.25, 0.25, 0.25))
    page.insert_text(fitz.Point(52, y_footer + 50), "Beneficiary: Enterprise AR Settlement Custody | ACH Remittance: remits@finops-settle.com", fontsize=8.5, fontname="helv", color=(0.25, 0.25, 0.25))
    page.insert_text(fitz.Point(52, y_footer + 70), f"Note: {data.get('note', 'Thank you for your partnership. Prompt settlement on credit terms is appreciated.')}", fontsize=8.5, fontname="helv", color=(0.4, 0.4, 0.4))

    doc.save(output_path)
    doc.close()
    print(f"Generated demo invoice PDF: {output_path}")


def main():
    target_dir = os.path.join("_internal_docs", "demo_invoices")
    os.makedirs(target_dir, exist_ok=True)

    today = date.today()

    demo_invoices = [
        {
            "filename": "INV-2026-0891_Apex_Logistics.pdf",
            "issuer_name": "TransNational Freight & Supply Co.",
            "issuer_tagline": "Intermodal Logistics, Dedicated Fleet & Cold Chain Services",
            "invoice_number": "INV-2026-0891",
            "customer_name": "Apex Freight Logistics LLC",
            "customer_address": "8400 Logistics Blvd, Suite 400, Dallas, TX 75261",
            "customer_email": "billing@apexlogistics.com",
            "issue_date": (today - timedelta(days=75)).strftime("%Y-%m-%d"),
            "due_date": (today - timedelta(days=45)).strftime("%Y-%m-%d"),
            "payment_terms": "Net 30 Days",
            "note": "Status: 45 Days Overdue. Please remit balance immediately to avoid carrier dispatch suspension.",
            "total_amount": 18450.00,
            "line_items": [
                {"desc": "Intermodal Freight Transit Lane CHI-DFW (5 Reefers)", "qty": 5, "unit_price": 2500.00, "total": 12500.00},
                {"desc": "Fuel Surcharge Assessment & Linehaul Levies", "qty": 1, "unit_price": 3950.00, "total": 3950.00},
                {"desc": "Detention & Terminal Yard Handling Fees (48h)", "qty": 2, "unit_price": 1000.00, "total": 2000.00},
            ],
        },
        {
            "filename": "INV-2026-0742_Precision_CNC.pdf",
            "issuer_name": "Apex Industrial Tooling Solutions",
            "issuer_tagline": "High-Tolerance Aerospace & Automotive Machining Services",
            "invoice_number": "INV-2026-0742",
            "customer_name": "Precision Machining & Tooling Inc.",
            "customer_address": "1200 Industrial Parkway, Cleveland, OH 44135",
            "customer_email": "ap@precisiontooling.com",
            "issue_date": (today - timedelta(days=105)).strftime("%Y-%m-%d"),
            "due_date": (today - timedelta(days=75)).strftime("%Y-%m-%d"),
            "payment_terms": "Net 30 Days",
            "note": "Status: 75 Days Overdue. Critical collection notice — production tooling on credit hold.",
            "total_amount": 42800.00,
            "line_items": [
                {"desc": "5-Axis CNC Titanium Turbine Stator Blades (Lot #84)", "qty": 20, "unit_price": 1500.00, "total": 30000.00},
                {"desc": "Anodized Surface Passivation & Heat Hardening", "qty": 1, "unit_price": 6800.00, "total": 6800.00},
                {"desc": "CMM Laser Dimensional Inspection & Certification", "qty": 1, "unit_price": 6000.00, "total": 6000.00},
            ],
        },
        {
            "filename": "INV-2026-1044_BioHealth_Diagnostics.pdf",
            "issuer_name": "Nexus Bioscience Supplies & Reagents",
            "issuer_tagline": "Clinical Diagnostics, High-Purity Reagents & Laboratory Consumables",
            "invoice_number": "INV-2026-1044",
            "customer_name": "BioHealth Clinical Diagnostics",
            "customer_address": "500 Kendall Square, Cambridge, MA 02142",
            "customer_email": "accounting@biohealthdiagnostics.com",
            "issue_date": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
            "due_date": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
            "payment_terms": "Net 30 Days",
            "note": "Status: Current / Open. Scheduled for automated processing.",
            "total_amount": 15600.00,
            "line_items": [
                {"desc": "Automated PCR Assay Reagent Kits (Batch #410)", "qty": 8, "unit_price": 1400.00, "total": 11200.00},
                {"desc": "Sterile Micropipette Barrier Filter Tips (50 racks)", "qty": 10, "unit_price": 240.00, "total": 2400.00},
                {"desc": "Cryogenic Vials & Specimen Transport Containers", "qty": 1, "unit_price": 2000.00, "total": 2000.00},
            ],
        },
    ]

    for inv in demo_invoices:
        out_file = os.path.join(target_dir, inv["filename"])
        create_invoice_pdf(out_file, inv)

    print("\nAll 3 photorealistic demo invoices successfully created in _internal_docs/demo_invoices/")


if __name__ == "__main__":
    main()
