from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import User


async def test_registration_login_me(client, db_factory):
    data = {"email": "Owner@example.com", "password": "  secure password  "}
    response = await client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201
    assert response.json()["email"] == "owner@example.com"
    assert "hashed_password" not in response.json()
    assert response.json()["created_at"].endswith("Z")
    async with db_factory() as session:
        user = await session.scalar(select(User))
        assert user.hashed_password.startswith("$argon2id$")
        assert user.hashed_password != data["password"]
    assert (await client.post("/api/v1/auth/register", json=data)).status_code == 409
    login = await client.post(
        "/api/v1/auth/login",
        data={
            "username": data["email"],
            "password": data["password"],
        },
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    me = await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {login.json()['access_token']}",
        },
    )
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"


@pytest.mark.parametrize("path", ["auth/me", "customers", "products", "orders"])
async def test_missing_token(client, path):
    response = await client.get(f"/api/v1/{path}")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_wrong_credentials_and_inactive_user(client, auth, db_factory):
    for email in ["owner@example.com", "missing@example.com"]:
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401
    async with db_factory() as session, session.begin():
        user = await session.scalar(select(User).where(User.email == "owner@example.com"))
        user.is_active = False
    assert (await client.get("/api/v1/auth/me", headers=auth[0])).status_code == 403
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "owner@example.com",
            "password": "a-secure-test-password",
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize("kind", ["garbage", "expired", "missing-exp", "bad-sub", "unknown-user"])
async def test_invalid_tokens(client, kind):
    claims = {"sub": "1", "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(hours=1)}
    if kind == "expired":
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
    elif kind == "missing-exp":
        claims.pop("exp")
    elif kind == "bad-sub":
        claims["sub"] = "x"
    token = (
        "garbage"
        if kind == "garbage"
        else jwt.encode(claims, get_settings().jwt_secret.get_secret_value(), algorithm="HS256")
    )
    assert (
        await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401
