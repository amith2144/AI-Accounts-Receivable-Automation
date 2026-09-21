from datetime import timedelta
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import require_role
from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import (
    authenticate_user,
    constant_time_compare,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.main import app
from app.schemas.auth import UserProfile


def test_password_hashing():
    pwd = "supersecretpassword123"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_constant_time_compare():
    assert constant_time_compare("secret_token_123", "secret_token_123") is True
    assert constant_time_compare("secret_token_123", "secret_token_456") is False
    assert constant_time_compare("", "") is True


def test_token_minting_and_decoding():
    access = create_access_token("admin", role="ADMIN", expires_delta=timedelta(minutes=15))
    payload = decode_token(access, expected_type="access")
    assert payload.sub == "admin"
    assert payload.role == "ADMIN"
    assert payload.type == "access"

    refresh = create_refresh_token("admin", role="ADMIN", expires_delta=timedelta(days=7))
    r_payload = decode_token(refresh, expected_type="refresh")
    assert r_payload.sub == "admin"
    assert r_payload.role == "ADMIN"
    assert r_payload.type == "refresh"

    # Attempting to decode refresh token as access token must fail
    with pytest.raises(UnauthorizedError, match="Invalid token type"):
        decode_token(refresh, expected_type="access")

    # Expired token
    expired_token = create_access_token("admin", role="ADMIN", expires_delta=timedelta(seconds=-10))
    with pytest.raises(UnauthorizedError, match="Token has expired"):
        decode_token(expired_token, expected_type="access")


def test_authenticate_user():
    admin = authenticate_user(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    assert admin is not None
    assert admin.username == settings.ADMIN_USERNAME
    assert admin.role == "ADMIN"

    operator = authenticate_user(settings.OPERATOR_USERNAME, settings.OPERATOR_PASSWORD)
    assert operator is not None
    assert operator.username == settings.OPERATOR_USERNAME
    assert operator.role == "OPERATOR"

    invalid = authenticate_user("unknown", "invalidpass")
    assert invalid is None


@pytest.mark.asyncio
async def test_auth_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Invalid login
        bad_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert bad_resp.status_code == 401

        # 2. Valid admin login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # 3. GET /me without token -> 401
        unauth_resp = await client.get("/api/v1/auth/me")
        assert unauth_resp.status_code == 401

        # 4. GET /me with valid token -> 200
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["username"] == settings.ADMIN_USERNAME
        assert me_data["role"] == "ADMIN"

        # 5. POST /refresh with valid refresh token -> 200
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        new_token_data = refresh_resp.json()
        assert "access_token" in new_token_data

        # 6. POST /refresh with invalid refresh token -> 401
        bad_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.jwt.token"},
        )
        assert bad_refresh.status_code == 401


@pytest.mark.asyncio
async def test_rbac_dependency():
    admin_checker = require_role(["ADMIN"])
    operator_user = UserProfile(username="operator", role="OPERATOR", is_active=True, permissions=[])
    admin_user = UserProfile(username="admin", role="ADMIN", is_active=True, permissions=[])

    # Admin passes admin check
    result = await admin_checker(admin_user)
    assert result.username == "admin"

    # Operator fails admin check with ForbiddenError (403)
    with pytest.raises(ForbiddenError, match="Insufficient permissions"):
        await admin_checker(operator_user)
