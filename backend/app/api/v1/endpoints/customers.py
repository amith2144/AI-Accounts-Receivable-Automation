import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_customer_service
from app.schemas.auth import UserProfile
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    query: Optional[str] = Query(None, description="Search debtors by name or email"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CustomerListResponse:
    """List and search debtor customer profiles with balance rollups."""
    return await customer_service.list_customers(query=query, offset=offset, limit=limit)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CustomerResponse:
    """Register a new customer debtor account with default payment terms."""
    return await customer_service.create_customer(data)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CustomerResponse:
    """Retrieve detailed debtor profile and aggregate receivable balances."""
    return await customer_service.get_customer(customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: UserProfile = Depends(get_current_user),
) -> CustomerResponse:
    """Update debtor contact details, terms, or automated reminder pause status."""
    return await customer_service.update_customer(customer_id, data)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: UserProfile = Depends(get_current_user),
) -> None:
    """Delete debtor customer account if no active invoices exist."""
    await customer_service.delete_customer(customer_id)
