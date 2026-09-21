import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentMethod


class PaymentBase(BaseModel):
    invoice_id: uuid.UUID = Field(..., description="Target invoice ID being settled")
    amount: Decimal = Field(..., gt=0, description="Remittance amount received (must be positive)")
    payment_date: date = Field(..., description="Date payment received")
    payment_method: PaymentMethod = Field(..., description="Remittance channel (ACH, WIRE, CHECK, CREDIT_CARD, OTHER)")
    reference_number: Optional[str] = Field(None, max_length=100, description="External transaction or check number")
    notes: Optional[str] = Field(None, max_length=1000, description="Remittance memo or notes")


class PaymentCreate(PaymentBase):
    pass


class PaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Remittance amount received (must be positive)")
    payment_date: date = Field(..., description="Date payment received")
    payment_method: PaymentMethod = Field(..., description="Remittance channel (ACH, WIRE, CHECK, CREDIT_CARD, OTHER)")
    reference_number: Optional[str] = Field(None, max_length=100, description="External transaction or check number")
    notes: Optional[str] = Field(None, max_length=1000, description="Remittance memo or notes")


class PaymentResponse(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class PaymentResult(BaseModel):
    payment: PaymentResponse
    invoice_id: uuid.UUID
    invoice_status: InvoiceStatus
    remaining_balance: Decimal


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    total: int
