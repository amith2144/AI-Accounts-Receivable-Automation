from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.auth import LoginRequest, RefreshRequest, Token, UserProfile

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest) -> Token:
    """
    Authenticate staff operator or administrator credentials using constant-time comparison
    and issue signed JWT access and refresh tokens.
    """
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise UnauthorizedError("Incorrect username or password")

    access_token = create_access_token(subject=user.username, role=user.role)
    refresh_token = create_refresh_token(subject=user.username, role=user.role)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshRequest) -> Token:
    """
    Exchange a valid refresh token for a newly minted access token.
    """
    payload = decode_token(request.refresh_token, expected_type="refresh")

    new_access_token = create_access_token(subject=payload.sub, role=payload.role)
    # Re-issue refresh token or keep same refresh token
    new_refresh_token = create_refresh_token(subject=payload.sub, role=payload.role)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """
    Retrieve current authenticated operator/admin profile and assigned permissions.
    """
    return current_user
