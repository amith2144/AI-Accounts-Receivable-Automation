from typing import AsyncGenerator, List, Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.database.session import AsyncSessionLocal, get_async_db
from app.schemas.auth import UserProfile
from app.services.activity_service import CollectionActivityService
from app.services.aging_service import AgingService
from app.services.cadence_service import CadenceService
from app.services.customer_service import CustomerService
from app.services.invoice_service import InvoiceService
from app.services.invoice_verification_service import InvoiceVerificationService
from app.services.payment_service import PaymentService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

get_db = get_async_db


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserProfile:
    """Validate bearer access token and return the current user profile."""
    if not token:
        raise UnauthorizedError("Authentication token is required")

    payload = decode_token(token, expected_type="access")
    return UserProfile(
        username=payload.sub,
        role=payload.role,
        is_active=True,
        permissions=["admin", "read", "write"] if payload.role == "ADMIN" else ["read", "write"],
    )


def require_role(allowed_roles: List[str]):
    """Role-based access control (RBAC) dependency factory."""

    async def role_checker(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(f"Insufficient permissions. Required role: {', '.join(allowed_roles)}")
        return current_user

    return role_checker


# --- Service Layer Dependency Factories ---


async def get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    return CustomerService(session=db)


async def get_invoice_service(db: AsyncSession = Depends(get_db)) -> InvoiceService:
    return InvoiceService(session=db)


async def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(session=db)


async def get_aging_service(db: AsyncSession = Depends(get_db)) -> AgingService:
    return AgingService(session=db)


async def get_cadence_service(db: AsyncSession = Depends(get_db)) -> CadenceService:
    return CadenceService(session=db)


async def get_activity_service(db: AsyncSession = Depends(get_db)) -> CollectionActivityService:
    return CollectionActivityService(session=db)


async def get_invoice_verification_service(db: AsyncSession = Depends(get_db)) -> InvoiceVerificationService:
    return InvoiceVerificationService(session=db)
