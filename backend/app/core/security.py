import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import TokenPayload, UserProfile


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for a password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")


def constant_time_compare(val_a: str, val_b: str) -> bool:
    """Constant-time string comparison preventing timing side-channel attacks (Standard 5)."""
    return secrets.compare_digest(val_a.encode("utf-8"), val_b.encode("utf-8"))


def create_access_token(
    subject: str,
    role: str = "OPERATOR",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Mint a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    role: str = "OPERATOR",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Mint a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> TokenPayload:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        token_type = payload.get("type", "access")
        if not constant_time_compare(token_type, expected_type):
            raise UnauthorizedError(f"Invalid token type: expected {expected_type}, got {token_type}")

        sub: Optional[str] = payload.get("sub")
        if not sub:
            raise UnauthorizedError("Token payload missing subject")

        role: str = payload.get("role", "OPERATOR")
        exp: Optional[int] = payload.get("exp")

        return TokenPayload(sub=sub, role=role, exp=exp, type=token_type)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.PyJWTError as e:
        raise UnauthorizedError(f"Invalid authentication token: {str(e)}")


def authenticate_user(username: str, password: str) -> Optional[UserProfile]:
    """
    Authenticate staff user using constant-time comparison against configured credentials.
    In a multi-tenant enterprise system, this connects to user directory / SSO;
    here it securely validates configured operator/admin roles.
    """
    # Check Admin
    is_admin_user = constant_time_compare(username, settings.ADMIN_USERNAME)
    is_admin_pass = constant_time_compare(password, settings.ADMIN_PASSWORD)
    if is_admin_user and is_admin_pass:
        return UserProfile(
            username=settings.ADMIN_USERNAME,
            role="ADMIN",
            is_active=True,
            permissions=["admin", "read", "write", "delete", "export", "cadence"],
        )

    # Check Operator
    is_op_user = constant_time_compare(username, settings.OPERATOR_USERNAME)
    is_op_pass = constant_time_compare(password, settings.OPERATOR_PASSWORD)
    if is_op_user and is_op_pass:
        return UserProfile(
            username=settings.OPERATOR_USERNAME,
            role="OPERATOR",
            is_active=True,
            permissions=["read", "write", "cadence"],
        )

    return None
