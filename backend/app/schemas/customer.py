import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Legal or trading name of the debtor")
    email: EmailStr = Field(..., description="Primary billing and remittance email contact")
    phone: Optional[str] = Field(None, max_length=50, description="Contact telephone number")
    payment_terms_days: int = Field(30, ge=0, description="Default payment terms in days (e.g., Net 30)")
    reminder_paused: bool = Field(False, description="Master toggle to pause automated reminder outreach")


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    payment_terms_days: Optional[int] = Field(None, ge=0)
    reminder_paused: Optional[bool] = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    total_invoiced: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    offset: int
    limit: int
