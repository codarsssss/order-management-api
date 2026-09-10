import os

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("POSTGRES_DB", "orders_test")
os.environ.setdefault("POSTGRES_USER", "orders_test")
os.environ.setdefault("POSTGRES_PASSWORD", "isolated-test-only")
os.environ.setdefault("POSTGRES_PORT", "55439")
os.environ.setdefault("JWT_SECRET", "isolated-tests-secret-at-least-32-characters")

from app.core.config import get_settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def db_factory():
    settings = get_settings()
    if not settings.postgres_db.endswith("_test"):
        pytest.fail("Tests require a dedicated database whose name ends with _test")
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE order_items, orders, products, customers, users RESTART IDENTITY CASCADE"
            )
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(db_factory):
    async def override_session():
        async with db_factory() as session, session.begin():
            yield session

    app.dependency_overrides[get_session] = override_session
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def auth(client):
    async def create(email):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "a-secure-test-password",
            },
        )
        assert response.status_code == 201, response.text
        login = await client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
                "password": "a-secure-test-password",
            },
        )
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return await create("owner@example.com"), await create("other@example.com")


@pytest.fixture
async def catalog(client, auth):
    customer = await client.post("/api/v1/customers", headers=auth[0], json={"name": "Acme"})
    product = await client.post(
        "/api/v1/products",
        headers=auth[0],
        json={
            "name": "Consulting",
            "price": "12.35",
        },
    )
    assert customer.status_code == product.status_code == 201
    return customer.json(), product.json()


@pytest.fixture
async def order(client, auth, catalog):
    customer, product = catalog
    response = await client.post(
        "/api/v1/orders",
        headers=auth[0],
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 3}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
