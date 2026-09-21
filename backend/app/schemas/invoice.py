import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.invoice import InvoiceStatus


class InvoiceLineItemBase(BaseModel):
    description: str = Field(..., min_length=1, description="Description of the goods or services rendered")
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0, description="Quantity billed")
    unit_price: Decimal = Field(..., ge=0, description="Per-unit rate or price")
    line_total: Optional[Decimal] = Field(None, ge=0, description="Calculated line item total")


class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass


class InvoiceLineItemResponse(InvoiceLineItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    line_total: Decimal
    created_at: datetime


class InvoiceBase(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Debtor customer ID")
    invoice_number: str = Field(..., min_length=1, max_length=100, description="Customer-facing invoice number")
    issue_date: date = Field(..., description="Issuance date of invoice")
    due_date: date = Field(..., description="Payment due date")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO-4217 currency code")
    status: InvoiceStatus = Field(default=InvoiceStatus.ISSUED, description="Current lifecycle state")


class InvoiceCreate(InvoiceBase):
    total_amount: Optional[Decimal] = Field(None, ge=0, description="Total billed amount. Computed from line items if omitted.")
    line_items: List[InvoiceLineItemCreate] = Field(default_factory=list, description="Itemized billing lines")
    document_source_id: Optional[uuid.UUID] = Field(None, description="Linked uploaded document ID if staged")


class InvoiceConfirmationRequest(BaseModel):
    customer_id: Optional[uuid.UUID] = Field(None, description="Assign to existing customer")
    customer_name: Optional[str] = Field(None, max_length=255, description="Customer name if creating or matching")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email if creating new profile")
    invoice_number: Optional[str] = Field(None, max_length=100, description="Confirmed or corrected invoice number")
    issue_date: Optional[date] = Field(None, description="Confirmed invoice date")
    due_date: Optional[date] = Field(None, description="Confirmed due date")
    currency: Optional[str] = Field("USD", min_length=3, max_length=3)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    line_items: Optional[List[InvoiceLineItemCreate]] = None


class InvoiceUpdate(BaseModel):
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    line_items: Optional[List[InvoiceLineItemCreate]] = None


class InvoiceVoidRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Audited business justification for voiding")


class InvoiceResponse(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    total_amount: Decimal
    balance_due: Decimal
    document_source_id: Optional[uuid.UUID]
    line_items: List[InvoiceLineItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    offset: int
    limit: int


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    extraction_status: str
    task_id: Optional[str] = None


class DocumentImportStatusResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    extraction_status: str
    extracted_data: dict = Field(default_factory=dict)
    error_message: Optional[str] = None
