"""Initial schema baseline

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Customers Table
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("reminder_paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=False)
    op.create_index(op.f("ix_customers_name"), "customers", ["name"], unique=False)

    # 2. Document Sources Table
    op.create_table(
        "document_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "extraction_status",
            sa.Enum("QUEUED", "PROCESSING", "SUCCESS", "PARTIAL_SUCCESS", "FAILED", name="extractionstatus"),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column(
            "extracted_data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_sources_extraction_status"), "document_sources", ["extraction_status"], unique=False)

    # 3. Reminder Cadences Table
    op.create_table(
        "reminder_cadences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("trigger_offset_days", sa.Integer(), nullable=False),
        sa.Column(
            "reminder_tone",
            sa.Enum("FRIENDLY", "STANDARD", "FIRM", "URGENT", name="remindertone"),
            server_default="STANDARD",
            nullable=False,
        ),
        sa.Column("email_subject_template", sa.String(length=255), nullable=False),
        sa.Column("email_body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Invoices Table
    op.create_table(
        "invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("balance_due", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PENDING_REVIEW", "ISSUED", "PARTIALLY_PAID", "PAID", "OVERDUE", "VOID", name="invoicestatus"),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("document_source_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_source_id"], ["document_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "invoice_number", name="uq_customer_invoice_number"),
    )
    op.create_index(op.f("ix_invoices_customer_id"), "invoices", ["customer_id"], unique=False)
    op.create_index(op.f("ix_invoices_due_date"), "invoices", ["due_date"], unique=False)
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=False)
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"], unique=False)

    # 5. Invoice Line Items Table
    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), server_default="1.00", nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_line_items_invoice_id"), "invoice_line_items", ["invoice_id"], unique=False)

    # 6. Payment Records Table
    op.create_table(
        "payment_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("ACH", "WIRE", "CHECK", "CREDIT_CARD", "OTHER", name="paymentmethod"),
            nullable=False,
        ),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_records_invoice_id"), "payment_records", ["invoice_id"], unique=False)

    # 7. Aging Schedules Table
    op.create_table(
        "aging_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("days_overdue", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "bucket",
            sa.Enum("CURRENT", "DAYS_1_30", "DAYS_31_60", "DAYS_61_90", "DAYS_90_PLUS", name="agingbucket"),
            server_default="CURRENT",
            nullable=False,
        ),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id"),
    )
    op.create_index(op.f("ix_aging_schedules_bucket"), "aging_schedules", ["bucket"], unique=False)
    op.create_index(op.f("ix_aging_schedules_invoice_id"), "aging_schedules", ["invoice_id"], unique=True)

    # 8. Collection Activities Table
    op.create_table(
        "collection_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column(
            "activity_type",
            sa.Enum("REMINDER_SENT", "MANUAL_NOTE", "CALL_LOGGED", "STATUS_CHANGE", "PAYMENT_APPLIED", name="activitytype"),
            nullable=False,
        ),
        sa.Column("performed_by", sa.String(length=255), server_default="SYSTEM_AUTOMATION", nullable=False),
        sa.Column(
            "details",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_activities_customer_id"), "collection_activities", ["customer_id"], unique=False)
    op.create_index(op.f("ix_collection_activities_invoice_id"), "collection_activities", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_collection_activities_invoice_id"), table_name="collection_activities")
    op.drop_index(op.f("ix_collection_activities_customer_id"), table_name="collection_activities")
    op.drop_table("collection_activities")

    op.drop_index(op.f("ix_aging_schedules_invoice_id"), table_name="aging_schedules")
    op.drop_index(op.f("ix_aging_schedules_bucket"), table_name="aging_schedules")
    op.drop_table("aging_schedules")

    op.drop_index(op.f("ix_payment_records_invoice_id"), table_name="payment_records")
    op.drop_table("payment_records")

    op.drop_index(op.f("ix_invoice_line_items_invoice_id"), table_name="invoice_line_items")
    op.drop_table("invoice_line_items")

    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_number"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_due_date"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_customer_id"), table_name="invoices")
    op.drop_table("invoices")

    op.drop_table("reminder_cadences")

    op.drop_index(op.f("ix_document_sources_extraction_status"), table_name="document_sources")
    op.drop_table("document_sources")

    op.drop_index(op.f("ix_customers_name"), table_name="customers")
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_table("customers")

    # Drop enums for PostgreSQL if applicable
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="activitytype").drop(bind, checkfirst=True)
        sa.Enum(name="agingbucket").drop(bind, checkfirst=True)
        sa.Enum(name="paymentmethod").drop(bind, checkfirst=True)
        sa.Enum(name="invoicestatus").drop(bind, checkfirst=True)
        sa.Enum(name="remindertone").drop(bind, checkfirst=True)
        sa.Enum(name="extractionstatus").drop(bind, checkfirst=True)
