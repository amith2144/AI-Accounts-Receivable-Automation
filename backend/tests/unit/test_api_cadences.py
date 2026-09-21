import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_async_db, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.activity import ActivityType, CollectionActivity
from app.models.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus


@pytest.fixture
async def cadence_test_env():
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
        yield client, test_session_maker

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
def auth_headers():
    token = create_access_token("operator", role="OPERATOR")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_cadence_and_activity_api(cadence_test_env, auth_headers: dict):
    client, session_maker = cadence_test_env

    # 1. Create cadence rule
    rule_payload = {
        "name": "Overdue 15 Day Notice",
        "trigger_offset_days": 15,
        "reminder_tone": "FIRM",
        "email_subject_template": "Overdue Notice: Invoice {{ invoice_number }}",
        "email_body_template": "Hello {{ customer_name }}, your balance of ${{ balance_due }} is overdue.",
        "is_active": True,
    }
    create_resp = await client.post("/api/v1/cadences", json=rule_payload, headers=auth_headers)
    assert create_resp.status_code == 201
    cadence_data = create_resp.json()
    assert cadence_data["name"] == "Overdue 15 Day Notice"
    assert cadence_data["trigger_offset_days"] == 15
    cadence_id = cadence_data["id"]

    # 2. List cadences
    list_resp = await client.get("/api/v1/cadences", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Get cadence by ID
    get_resp = await client.get(f"/api/v1/cadences/{cadence_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == cadence_id

    # 4. Update cadence
    up_resp = await client.put(
        f"/api/v1/cadences/{cadence_id}",
        json={"name": "Updated 15 Day Notice", "reminder_tone": "URGENT"},
        headers=auth_headers,
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["name"] == "Updated 15 Day Notice"
    assert up_resp.json()["reminder_tone"] == "URGENT"

    # 5. Trigger cadence run (dry run)
    trigger_resp = await client.post("/api/v1/cadences/trigger-run?dry_run=true", headers=auth_headers)
    assert trigger_resp.status_code == 200
    summary = trigger_resp.json()
    assert summary["evaluated_cadences"] >= 1
    assert "dispatched_count" in summary

    # 6. Seed and test /api/v1/activities
    cust_id = uuid.uuid4()
    inv_id = uuid.uuid4()
    async with session_maker() as session:
        cust = Customer(id=cust_id, name="LexCorp", email="lex@lexcorp.com", payment_terms_days=30)
        session.add(cust)
        act = CollectionActivity(
            id=uuid.uuid4(),
            invoice_id=inv_id,
            customer_id=cust_id,
            activity_type=ActivityType.CALL_LOGGED,
            performed_by="OPERATOR",
            details={"notes": "Called client accounts department"},
        )
        session.add(act)
        await session.commit()

    act_resp = await client.get("/api/v1/activities", headers=auth_headers)
    assert act_resp.status_code == 200
    act_data = act_resp.json()
    assert act_data["total"] >= 1

    act_filtered = await client.get(f"/api/v1/activities?customer_id={cust_id}", headers=auth_headers)
    assert act_filtered.status_code == 200
    assert act_filtered.json()["total"] == 1

    # 7. Delete cadence
    del_resp = await client.delete(f"/api/v1/cadences/{cadence_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # 8. Unauthenticated request rejected
    unauth = await client.get("/api/v1/cadences")
    assert unauth.status_code == 401
