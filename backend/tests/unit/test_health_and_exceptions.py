import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database.session import get_async_db
from app.core.exceptions import AppException, NotFoundError


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_test_client():
    # Setup in-memory SQLite engine for testing healthcheck dependency
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_async_db():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_endpoint(async_test_client: AsyncClient):
    response = await async_test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_handled_app_exception(async_test_client: AsyncClient):
    # Temporarily add a test route raising NotFoundError
    @app.get("/test/not-found-route")
    async def not_found_route():
        raise NotFoundError("Invoice INV-1001 not found", details={"invoice_id": "123"})

    response = await async_test_client.get("/test/not-found-route")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "Invoice INV-1001 not found"
    assert data["code"] == "NOT_FOUND"
    assert data["details"] == {"invoice_id": "123"}
    assert "request_id" in data


@pytest.mark.asyncio
async def test_unhandled_exception_sanitization(async_test_client: AsyncClient):
    # Temporarily add a test route raising unexpected RuntimeError
    @app.get("/test/crash-route")
    async def crash_route():
        raise RuntimeError("Internal database password leaked here!")

    response = await async_test_client.get("/test/crash-route")
    assert response.status_code == 500
    data = response.json()
    # Ensure sensitive error message is sanitized per Standard 8
    assert data["error"] == "An internal server error occurred. Please contact support."
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert "password" not in response.text
    assert "request_id" in data
