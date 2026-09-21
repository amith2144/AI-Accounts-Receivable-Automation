"""
Seed script to populate the local PostgreSQL database with realistic B2B enterprise data.
Enables instant local visual testing and provides a full, populated environment for recording demo videos.

Usage:
    # Run locally (if PostgreSQL is on localhost:5432):
    backend\\.venv\\Scripts\\python scripts/seed_demo_data.py

    # Or run inside Docker container:
    docker compose exec backend-api python scripts/seed_demo_data.py
"""

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, delete, text

from app.core.config import settings
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import InvoiceLineItem, PaymentRecord, PaymentMethod
from app.models.aging import AgingSchedule, AgingBucket
from app.models.cadence import ReminderCadence, ReminderTone
from app.models.activity import CollectionActivity, ActivityType


async def seed(db_url: str = None):
    target_url = db_url or os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    print(f"Connecting to database: {target_url}")
    engine = create_async_engine(target_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # Verify schema
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        print("Cleaning up any existing demo records...")
        # Order matters for foreign keys
        await session.execute(delete(CollectionActivity))
        await session.execute(delete(PaymentRecord))
        await session.execute(delete(AgingSchedule))
        await session.execute(delete(InvoiceLineItem))
        await session.execute(delete(Invoice))
        await session.execute(delete(Customer))
        await session.execute(delete(ReminderCadence))
        await session.commit()

        print("1. Seeding Reminder Cadences (Autonomous Escalation Ladder)...")
        cadences = [
            ReminderCadence(
                id=uuid.uuid4(),
                name="T-3 Days Friendly Pre-Due Notice",
                trigger_offset_days=-3,
                reminder_tone=ReminderTone.FRIENDLY,
                email_subject_template="Courtesy Reminder: Upcoming Payment for Invoice {{ invoice_number }}",
                email_body_template=(
                    "Dear {{ customer_name }},\n\n"
                    "This is a friendly reminder that invoice {{ invoice_number }} for ${{ balance_due }} "
                    "will be due in 3 business days on {{ due_date }}.\n\n"
                    "Please review the attached invoice copy. If payment is already in transit via ACH or Wire, "
                    "kindly disregard this note.\n\n"
                    "Best regards,\nAccounts Receivable Team"
                ),
                is_active=True,
            ),
            ReminderCadence(
                id=uuid.uuid4(),
                name="T-0 Days Due Date Arrival Notice",
                trigger_offset_days=0,
                reminder_tone=ReminderTone.STANDARD,
                email_subject_template="Payment Due Today: Invoice {{ invoice_number }}",
                email_body_template=(
                    "Hello {{ customer_name }},\n\n"
                    "Invoice {{ invoice_number }} for ${{ balance_due }} is due today ({{ due_date }}).\n\n"
                    "Please execute payment using the banking remittance instructions on the invoice. "
                    "If you have any questions or require an updated statement, please let us know immediately.\n\n"
                    "Thank you,\nCredit & Treasury Operations"
                ),
                is_active=True,
            ),
            ReminderCadence(
                id=uuid.uuid4(),
                name="T+7 Days Past-Due Reminder",
                trigger_offset_days=7,
                reminder_tone=ReminderTone.STANDARD,
                email_subject_template="Past Due Reminder: Invoice {{ invoice_number }}",
                email_body_template=(
                    "Attention {{ customer_name }} Accounts Payable,\n\n"
                    "According to our records, invoice {{ invoice_number }} with an outstanding balance of ${{ balance_due }} "
                    "is now 7 days past due (Due Date: {{ due_date }}).\n\n"
                    "Please confirm the scheduled disbursement date for this invoice or provide the remittance confirmation number.\n\n"
                    "Sincerely,\nAccounts Receivable Department"
                ),
                is_active=True,
            ),
            ReminderCadence(
                id=uuid.uuid4(),
                name="T+15 Days Overdue Escalation",
                trigger_offset_days=15,
                reminder_tone=ReminderTone.FIRM,
                email_subject_template="URGENT: Overdue Account Notice — Invoice {{ invoice_number }}",
                email_body_template=(
                    "Dear {{ customer_name }},\n\n"
                    "Your account is currently 15 days overdue. Outstanding balance due: ${{ balance_due }} "
                    "for invoice {{ invoice_number }}.\n\n"
                    "To maintain uninterrupted delivery of goods and active credit terms, please remit payment immediately. "
                    "If there is an active billing discrepancy, contact our treasury manager directly.\n\n"
                    "Accounts Receivable Escalation Team"
                ),
                is_active=True,
            ),
            ReminderCadence(
                id=uuid.uuid4(),
                name="T+30 Days Credit Hold & Demand Notice",
                trigger_offset_days=30,
                reminder_tone=ReminderTone.URGENT,
                email_subject_template="CRITICAL NOTICE: Credit Suspension Warning — Invoice {{ invoice_number }}",
                email_body_template=(
                    "FINAL REMINDER: {{ customer_name }},\n\n"
                    "Invoice {{ invoice_number }} (Balance: ${{ balance_due }}) is now 30+ days overdue.\n\n"
                    "Continued non-payment will result in immediate placement on Credit Hold, withholding of all pending orders, "
                    "and referral to third-party recovery counsel.\n\n"
                    "Please settle this balance within 48 hours to avoid credit suspension.\n\n"
                    "Finance Operations & Risk Management"
                ),
                is_active=True,
            ),
        ]
        session.add_all(cadences)
        await session.flush()

        print("2. Seeding Enterprise B2B Customers...")
        customers = [
            Customer(
                id=uuid.uuid4(),
                name="Apex Freight Logistics LLC",
                email="billing@apexlogistics.com",
                phone="+1-312-555-0192",
                payment_terms_days=30,
                reminder_paused=False,
            ),
            Customer(
                id=uuid.uuid4(),
                name="Precision Machining & Tooling Inc.",
                email="ap@precisiontooling.com",
                phone="+1-216-555-0144",
                payment_terms_days=30,
                reminder_paused=False,
            ),
            Customer(
                id=uuid.uuid4(),
                name="BluePeak Digital Performance Media",
                email="finance@bluepeakagency.com",
                phone="+1-415-555-0188",
                payment_terms_days=15,
                reminder_paused=False,
            ),
            Customer(
                id=uuid.uuid4(),
                name="BioHealth Clinical Diagnostics",
                email="accounting@biohealthdiagnostics.com",
                phone="+1-617-555-0177",
                payment_terms_days=30,
                reminder_paused=False,
            ),
            Customer(
                id=uuid.uuid4(),
                name="Titan Commercial Mechanical Services",
                email="invoicing@titanhvac.com",
                phone="+1-713-555-0163",
                payment_terms_days=30,
                reminder_paused=True,  # Demonstrates dispute pause control!
            ),
        ]
        session.add_all(customers)
        await session.flush()

        today = date.today()
        now = datetime.now(timezone.utc)

        print("3. Seeding Realistic Invoices across all 5 Aging Tiers...")
        # 1. BioHealth - Current (Not overdue, due in 20 days)
        inv_current = Invoice(
            id=uuid.uuid4(),
            customer_id=customers[3].id,
            invoice_number="INV-2026-1044",
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=20),
            currency="USD",
            total_amount=Decimal("15600.00"),
            balance_due=Decimal("15600.00"),
            status=InvoiceStatus.ISSUED,
        )
        inv_current_items = [
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_current.id,
                description="Automated PCR Assay Reagent Kits (Batch #410)",
                quantity=Decimal("8.00"),
                unit_price=Decimal("1400.00"),
                line_total=Decimal("11200.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_current.id,
                description="Sterile Micropipette Barrier Filter Tips (50 Racks)",
                quantity=Decimal("10.00"),
                unit_price=Decimal("240.00"),
                line_total=Decimal("2400.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_current.id,
                description="Cryogenic Vials & Specimen Transport Cold Boxes",
                quantity=Decimal("1.00"),
                unit_price=Decimal("2000.00"),
                line_total=Decimal("2000.00"),
            ),
        ]
        inv_current_aging = AgingSchedule(
            id=uuid.uuid4(),
            invoice_id=inv_current.id,
            days_overdue=0,
            bucket=AgingBucket.CURRENT,
        )

        # 2. BluePeak - 1 to 30 Days Overdue (12 days overdue)
        inv_1_30 = Invoice(
            id=uuid.uuid4(),
            customer_id=customers[2].id,
            invoice_number="INV-2026-0982",
            issue_date=today - timedelta(days=27),
            due_date=today - timedelta(days=12),
            currency="USD",
            total_amount=Decimal("9200.00"),
            balance_due=Decimal("9200.00"),
            status=InvoiceStatus.OVERDUE,
        )
        inv_1_30_items = [
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_1_30.id,
                description="Omni-channel Programmatic Ad Campaign Management (Q3)",
                quantity=Decimal("1.00"),
                unit_price=Decimal("6500.00"),
                line_total=Decimal("6500.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_1_30.id,
                description="Creative Asset Production & Dynamic Video Localization",
                quantity=Decimal("1.00"),
                unit_price=Decimal("2700.00"),
                line_total=Decimal("2700.00"),
            ),
        ]
        inv_1_30_aging = AgingSchedule(
            id=uuid.uuid4(),
            invoice_id=inv_1_30.id,
            days_overdue=12,
            bucket=AgingBucket.DAYS_1_30,
        )

        # 3. Apex Logistics - 31 to 60 Days Overdue (45 days overdue, partially paid)
        inv_31_60 = Invoice(
            id=uuid.uuid4(),
            customer_id=customers[0].id,
            invoice_number="INV-2026-0891",
            issue_date=today - timedelta(days=75),
            due_date=today - timedelta(days=45),
            currency="USD",
            total_amount=Decimal("18450.00"),
            balance_due=Decimal("13450.00"),  # $5,000 partial payment already applied
            status=InvoiceStatus.PARTIALLY_PAID,
        )
        inv_31_60_items = [
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_31_60.id,
                description="Intermodal Freight Transit Lane CHI-DFW (5 Reefers)",
                quantity=Decimal("5.00"),
                unit_price=Decimal("2500.00"),
                line_total=Decimal("12500.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_31_60.id,
                description="Fuel Surcharge Assessment & Linehaul Levies",
                quantity=Decimal("1.00"),
                unit_price=Decimal("3950.00"),
                line_total=Decimal("3950.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_31_60.id,
                description="Detention & Terminal Yard Handling Fees (48h)",
                quantity=Decimal("2.00"),
                unit_price=Decimal("1000.00"),
                line_total=Decimal("2000.00"),
            ),
        ]
        inv_31_60_aging = AgingSchedule(
            id=uuid.uuid4(),
            invoice_id=inv_31_60.id,
            days_overdue=45,
            bucket=AgingBucket.DAYS_31_60,
        )
        inv_31_60_payment = PaymentRecord(
            id=uuid.uuid4(),
            invoice_id=inv_31_60.id,
            amount=Decimal("5000.00"),
            payment_date=today - timedelta(days=20),
            payment_method=PaymentMethod.ACH,
            reference_number="ACH-TX-883910",
            notes="Partial settlement authorized by dispatch finance.",
        )

        # 4. Precision Tooling - 61 to 90 Days Overdue (75 days overdue)
        inv_61_90 = Invoice(
            id=uuid.uuid4(),
            customer_id=customers[1].id,
            invoice_number="INV-2026-0742",
            issue_date=today - timedelta(days=105),
            due_date=today - timedelta(days=75),
            currency="USD",
            total_amount=Decimal("42800.00"),
            balance_due=Decimal("42800.00"),
            status=InvoiceStatus.OVERDUE,
        )
        inv_61_90_items = [
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_61_90.id,
                description="5-Axis CNC Titanium Turbine Stator Blades (Lot #84)",
                quantity=Decimal("20.00"),
                unit_price=Decimal("1500.00"),
                line_total=Decimal("30000.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_61_90.id,
                description="Anodized Surface Passivation & Heat Hardening",
                quantity=Decimal("1.00"),
                unit_price=Decimal("6800.00"),
                line_total=Decimal("6800.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_61_90.id,
                description="CMM Laser Dimensional Inspection & Certification",
                quantity=Decimal("1.00"),
                unit_price=Decimal("6000.00"),
                line_total=Decimal("6000.00"),
            ),
        ]
        inv_61_90_aging = AgingSchedule(
            id=uuid.uuid4(),
            invoice_id=inv_61_90.id,
            days_overdue=75,
            bucket=AgingBucket.DAYS_61_90,
        )

        # 5. Titan Mechanical - 90+ Days Overdue (110 days overdue, paused due to active claim)
        inv_90_plus = Invoice(
            id=uuid.uuid4(),
            customer_id=customers[4].id,
            invoice_number="INV-2026-0518",
            issue_date=today - timedelta(days=140),
            due_date=today - timedelta(days=110),
            currency="USD",
            total_amount=Decimal("64350.00"),
            balance_due=Decimal("64350.00"),
            status=InvoiceStatus.OVERDUE,
        )
        inv_90_plus_items = [
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_90_plus.id,
                description="Commercial Chiller Retrofit & Variable Refrigerant Flow Units",
                quantity=Decimal("3.00"),
                unit_price=Decimal("18000.00"),
                line_total=Decimal("54000.00"),
            ),
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_90_plus.id,
                description="Emergency Sunday Crane Rigging & Rooftop Deployment",
                quantity=Decimal("1.00"),
                unit_price=Decimal("10350.00"),
                line_total=Decimal("10350.00"),
            ),
        ]
        inv_90_plus_aging = AgingSchedule(
            id=uuid.uuid4(),
            invoice_id=inv_90_plus.id,
            days_overdue=110,
            bucket=AgingBucket.DAYS_90_PLUS,
        )

        # 6. Apex Logistics - Fully Paid historical invoice (demonstrates completed cash flow velocity)
        inv_paid = Invoice(
            id=uuid.uuid4(),
            customer_id=customers[0].id,
            invoice_number="INV-2026-0320",
            issue_date=today - timedelta(days=120),
            due_date=today - timedelta(days=90),
            currency="USD",
            total_amount=Decimal("12500.00"),
            balance_due=Decimal("0.00"),
            status=InvoiceStatus.PAID,
        )
        inv_paid_items = [
            InvoiceLineItem(
                id=uuid.uuid4(),
                invoice_id=inv_paid.id,
                description="Cross-Docking Storage & Transloading Services (100 Pallets)",
                quantity=Decimal("100.00"),
                unit_price=Decimal("125.00"),
                line_total=Decimal("12500.00"),
            )
        ]
        inv_paid_aging = AgingSchedule(
            id=uuid.uuid4(),
            invoice_id=inv_paid.id,
            days_overdue=0,
            bucket=AgingBucket.CURRENT,
        )
        inv_paid_payment = PaymentRecord(
            id=uuid.uuid4(),
            invoice_id=inv_paid.id,
            amount=Decimal("12500.00"),
            payment_date=today - timedelta(days=88),
            payment_method=PaymentMethod.WIRE,
            reference_number="WIRE-FED-992140",
            notes="Settled in full via Fedwire.",
        )

        all_invoices = [inv_current, inv_1_30, inv_31_60, inv_61_90, inv_90_plus, inv_paid]
        session.add_all(all_invoices)
        await session.flush()

        all_items = (
            inv_current_items
            + inv_1_30_items
            + inv_31_60_items
            + inv_61_90_items
            + inv_90_plus_items
            + inv_paid_items
        )
        session.add_all(all_items)

        all_aging = [
            inv_current_aging,
            inv_1_30_aging,
            inv_31_60_aging,
            inv_61_90_aging,
            inv_90_plus_aging,
            inv_paid_aging,
        ]
        session.add_all(all_aging)

        all_payments = [inv_31_60_payment, inv_paid_payment]
        session.add_all(all_payments)
        await session.flush()

        print("4. Seeding Collection Activity Audit Logs...")
        activities = [
            CollectionActivity(
                id=uuid.uuid4(),
                invoice_id=inv_current.id,
                customer_id=customers[3].id,
                activity_type=ActivityType.STATUS_CHANGE,
                performed_by="BILLING_ADMIN",
                details={
                    "old_status": "DRAFT",
                    "new_status": "ISSUED",
                    "reason": "Invoice verified and committed to active ledger",
                },
                created_at=now - timedelta(days=10),
            ),
            CollectionActivity(
                id=uuid.uuid4(),
                invoice_id=inv_1_30.id,
                customer_id=customers[2].id,
                activity_type=ActivityType.REMINDER_SENT,
                performed_by="SYSTEM_AUTOMATION",
                details={
                    "cadence_name": "T+7 Days Past-Due Reminder",
                    "recipient": "finance@bluepeakagency.com",
                    "tone": "STANDARD",
                    "offset_days": 7,
                },
                created_at=now - timedelta(days=5),
            ),
            CollectionActivity(
                id=uuid.uuid4(),
                invoice_id=inv_31_60.id,
                customer_id=customers[0].id,
                activity_type=ActivityType.PAYMENT_APPLIED,
                performed_by="AR_OPERATOR",
                details={
                    "amount": 5000.00,
                    "payment_method": "ACH",
                    "remaining_balance": 13450.00,
                    "reference": "ACH-TX-883910",
                },
                created_at=now - timedelta(days=20),
            ),
            CollectionActivity(
                id=uuid.uuid4(),
                invoice_id=inv_31_60.id,
                customer_id=customers[0].id,
                activity_type=ActivityType.REMINDER_SENT,
                performed_by="SYSTEM_AUTOMATION",
                details={
                    "cadence_name": "T+15 Days Overdue Escalation",
                    "recipient": "billing@apexlogistics.com",
                    "tone": "FIRM",
                    "offset_days": 15,
                },
                created_at=now - timedelta(days=30),
            ),
            CollectionActivity(
                id=uuid.uuid4(),
                invoice_id=inv_61_90.id,
                customer_id=customers[1].id,
                activity_type=ActivityType.REMINDER_SENT,
                performed_by="SYSTEM_AUTOMATION",
                details={
                    "cadence_name": "T+30 Days Credit Hold & Demand Notice",
                    "recipient": "ap@precisiontooling.com",
                    "tone": "URGENT",
                    "offset_days": 30,
                },
                created_at=now - timedelta(days=45),
            ),
            CollectionActivity(
                id=uuid.uuid4(),
                invoice_id=inv_90_plus.id,
                customer_id=customers[4].id,
                activity_type=ActivityType.MANUAL_NOTE,
                performed_by="VP_FINANCE",
                details={
                    "note": "Outreach temporarily paused by VP Finance. Customer claims warranty inspection required on chiller compressor.",
                },
                created_at=now - timedelta(days=15),
            ),
        ]
        session.add_all(activities)
        await session.commit()

        print("\n=======================================================")
        print(" DEMO DATABASE SEED COMPLETED SUCCESSFULLY!")
        print("=======================================================")
        print(f" - Customers Seeded: {len(customers)}")
        print(f" - Active Invoices: {len(all_invoices)}")
        print(f" - Aging Distribution:")
        print(f"     * CURRENT (Not Overdue):     $15,600.00  (BioHealth Diagnostics)")
        print(f"     * 1–30 Days Overdue:          $9,200.00  (BluePeak Media)")
        print(f"     * 31–60 Days Overdue:        $13,450.00  (Apex Logistics, partially paid)")
        print(f"     * 61–90 Days Overdue:        $42,800.00  (Precision Tooling)")
        print(f"     * 90+ Days Overdue:          $64,350.00  (Titan HVAC, paused)")
        print(f"     * PAID (Historical):         $12,500.00  (Apex Logistics)")
        print(f" - Total Receivables Portfolio:  $157,900.00")
        print(f" - Total Past-Due Receivables:   $129,800.00")
        print(f" - Cadence Rules Active:         5 rules configured")
        print("=======================================================\n")

    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed AR Platform Demo Database")
    parser.add_argument("--db-url", type=str, default=None, help="Custom PostgreSQL asyncpg connection URL")
    args = parser.parse_args()
    asyncio.run(seed(db_url=args.db_url))
