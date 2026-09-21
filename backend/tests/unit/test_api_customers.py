import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_async_db, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base


@pytest.fixture
async def async_client_with_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_db():
        async with test_session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_async_db] = override_db
    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
def auth_headers():
    token = create_access_token("operator", role="OPERATOR")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_customer_api_crud_lifecycle(async_client_with_db: AsyncClient, auth_headers: dict):
    client = async_client_with_db

    # 1. Unauthenticated request must be rejected with 401
    unauth_resp = await client.get("/api/v1/customers")
    assert unauth_resp.status_code == 401

    # 2. Create customer 1
    create_payload = {
        "name": "Acme Corp",
        "email": "billing@acme.com",
        "phone": "+1-555-0199",
        "payment_terms_days": 30,
        "reminder_paused": False,
    }
    create_resp = await client.post("/api/v1/customers", json=create_payload, headers=auth_headers)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["name"] == "Acme Corp"
    assert created_data["email"] == "billing@acme.com"
    customer_id = created_data["id"]

    # 3. Duplicate email returns 409 Conflict
    dup_resp = await client.post("/api/v1/customers", json=create_payload, headers=auth_headers)
    assert dup_resp.status_code == 409
    assert dup_resp.json()["code"] == "CONFLICT"

    # 4. Create customer 2
    create_resp2 = await client.post(
        "/api/v1/customers",
        json={"name": "Beta LLC", "email": "finance@beta.com", "payment_terms_days": 15},
        headers=auth_headers,
    )
    assert create_resp2.status_code == 201

    # 5. List customers
    list_resp = await client.get("/api/v1/customers", headers=auth_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 2
    assert len(list_data["items"]) == 2

    # 6. Search query
    search_resp = await client.get("/api/v1/customers?query=Beta", headers=auth_headers)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["name"] == "Beta LLC"

    # 7. Get single customer by ID
    get_resp = await client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Acme Corp"

    # 8. Get non-existent customer -> 404
    fake_id = str(uuid.uuid4())
    nf_resp = await client.get(f"/api/v1/customers/{fake_id}", headers=auth_headers)
    assert nf_resp.status_code == 404
    assert nf_resp.json()["code"] == "NOT_FOUND"

    # 9. Update customer
    update_resp = await client.put(
        f"/api/v1/customers/{customer_id}",
        json={"reminder_paused": True, "payment_terms_days": 45},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["reminder_paused"] is True
    assert updated_data["payment_terms_days"] == 45

    # 10. Delete customer
    del_resp = await client.delete(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # 11. Verify deleted customer is gone -> 404
    gone_resp = await client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert gone_resp.status_code == 404
