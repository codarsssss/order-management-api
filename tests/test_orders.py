import asyncio

import pytest
from sqlalchemy import func, select

from app.models import Order, OrderItem


async def test_total_snapshot_items_and_delete(client, auth, order, catalog, db_factory):
    headers = auth[0]
    path = f"/api/v1/orders/{order['id']}"
    assert order["total"] == "37.05"
    assert order["items"][0]["unit_price"] == "12.35"
    product_id = catalog[1]["id"]
    await client.patch(f"/api/v1/products/{product_id}", headers=headers, json={"price": "20.00"})
    assert (await client.get(path, headers=headers)).json()["total"] == "37.05"
    added = await client.post(
        path + "/items",
        headers=headers,
        json={
            "product_id": product_id,
            "quantity": 2,
        },
    )
    assert added.status_code == 201
    assert added.json()["total"] == "77.05"
    item_path = f"{path}/items/{order['items'][0]['id']}"
    changed = await client.patch(item_path, headers=headers, json={"quantity": 1})
    assert changed.status_code == 200 and changed.json()["total"] == "52.35"
    assert (await client.delete(item_path, headers=headers)).status_code == 204
    assert (await client.get(path, headers=headers)).json()["total"] == "40.00"
    assert (
        await client.delete(f"/api/v1/products/{product_id}", headers=headers)
    ).status_code == 409
    changed = await client.patch(path, headers=headers, json={"comment": "Ready"})
    assert changed.json()["comment"] == "Ready"
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(path, headers=headers)).status_code == 404
    async with db_factory() as session:
        assert await session.scalar(select(func.count()).select_from(OrderItem)) == 0


@pytest.mark.parametrize("problem", ["foreign-product", "inactive", "missing", "foreign-customer"])
async def test_creation_is_atomic(client, auth, catalog, db_factory, problem):
    customer, product = catalog
    invalid_id = 99999
    customer_id = customer["id"]
    if problem in {"foreign-product", "inactive"}:
        response = await client.post(
            "/api/v1/products",
            headers=auth[problem == "foreign-product"],
            json={"name": "Bad", "price": "10", "is_active": False},
        )
        invalid_id = response.json()["id"]
    if problem == "foreign-customer":
        response = await client.post("/api/v1/customers", headers=auth[1], json={"name": "Other"})
        customer_id = response.json()["id"]
        invalid_id = product["id"]
    response = await client.post(
        "/api/v1/orders",
        headers=auth[0],
        json={
            "customer_id": customer_id,
            "items": [
                {"product_id": product["id"], "quantity": 1},
                {"product_id": invalid_id, "quantity": 1},
            ],
        },
    )
    assert response.status_code == (409 if problem == "inactive" else 404), response.text
    async with db_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Order)) == 0
        assert await session.scalar(select(func.count()).select_from(OrderItem)) == 0


async def test_database_failure_rolls_back_inserted_order(
    client, auth, catalog, db_factory, monkeypatch
):
    from app.services import orders

    original_create = orders.create

    async def fail_after_flush(session, owner_id, data):
        created = await original_create(session, owner_id, data)
        # Force a real constraint failure after both order and item have been inserted.
        created.items[0].quantity = 0
        await session.flush()

    monkeypatch.setattr(orders, "create", fail_after_flush)
    response = await client.post(
        "/api/v1/orders",
        headers=auth[0],
        json={
            "customer_id": catalog[0]["id"],
            "items": [{"product_id": catalog[1]["id"], "quantity": 1}],
        },
    )
    assert response.status_code == 409
    async with db_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Order)) == 0
        assert await session.scalar(select(func.count()).select_from(OrderItem)) == 0


async def test_workflow_and_freeze(client, auth, order):
    path = f"/api/v1/orders/{order['id']}"
    headers = auth[0]
    assert (
        await client.patch(path + "/status", headers=headers, json={"status": "completed"})
    ).status_code == 409
    for status in ["confirmed", "processing", "completed"]:
        response = await client.patch(path + "/status", headers=headers, json={"status": status})
        assert response.status_code == 200 and response.json()["status"] == status
    assert (
        await client.patch(path + "/status", headers=headers, json={"status": "cancelled"})
    ).status_code == 409
    assert (await client.patch(path, headers=headers, json={"comment": "No"})).status_code == 409
    assert (await client.delete(path, headers=headers)).status_code == 409
    assert (
        await client.post(
            path + "/items",
            headers=headers,
            json={
                "product_id": order["items"][0]["product_id"],
                "quantity": 1,
            },
        )
    ).status_code == 409
    assert (
        await client.patch(
            f"{path}/items/{order['items'][0]['id']}", headers=headers, json={"quantity": 1}
        )
    ).status_code == 409


@pytest.mark.parametrize("steps", [[], ["confirmed"], ["confirmed", "processing"]])
async def test_cancellation(client, auth, order, steps):
    path = f"/api/v1/orders/{order['id']}/status"
    for status in [*steps, "cancelled"]:
        assert (
            await client.patch(path, headers=auth[0], json={"status": status})
        ).status_code == 200
    for status in ["new", "confirmed", "cancelled"]:
        assert (
            await client.patch(path, headers=auth[0], json={"status": status})
        ).status_code == 409


async def test_concurrent_status_changes_are_serialized(client, auth, order):
    path = f"/api/v1/orders/{order['id']}/status"
    responses = await asyncio.gather(
        *[client.patch(path, headers=auth[0], json={"status": "confirmed"}) for _ in range(2)]
    )
    assert sorted(response.status_code for response in responses) == [200, 409]


@pytest.mark.parametrize(
    "method,suffix,data",
    [
        ("get", "", None),
        ("patch", "", {"comment": "No"}),
        ("delete", "", None),
        ("get", "/total", None),
        ("patch", "/status", {"status": "confirmed"}),
        ("post", "/items", {"product_id": 1, "quantity": 1}),
        ("patch", "/items/1", {"quantity": 2}),
        ("delete", "/items/1", None),
    ],
)
async def test_foreign_order(client, auth, order, method, suffix, data):
    kwargs = {"json": data} if data is not None else {}
    response = await client.request(
        method, f"/api/v1/orders/{order['id']}{suffix}", headers=auth[1], **kwargs
    )
    assert response.status_code == 404
    assert (await client.get("/api/v1/orders", headers=auth[1])).json()["total"] == 0


async def test_item_belongs_to_specific_order(client, auth, order, catalog):
    second = await client.post(
        "/api/v1/orders",
        headers=auth[0],
        json={
            "customer_id": catalog[0]["id"],
            "items": [],
        },
    )
    path = f"/api/v1/orders/{second.json()['id']}/items/{order['items'][0]['id']}"
    assert (await client.patch(path, headers=auth[0], json={"quantity": 2})).status_code == 404
    assert (await client.delete(path, headers=auth[0])).status_code == 404


async def test_filters_sort_dates_and_empty_order(client, auth, order, catalog):
    headers = auth[0]
    empty = await client.post(
        "/api/v1/orders", headers=headers, json={"customer_id": catalog[0]["id"]}
    )
    assert empty.status_code == 201 and empty.json()["total"] == "0.00"
    assert (
        await client.patch(
            f"/api/v1/orders/{empty.json()['id']}/status",
            headers=headers,
            json={"status": "confirmed"},
        )
    ).status_code == 409
    for sort, expected in [("total", "0.00"), ("-total", "37.05")]:
        page = (
            await client.get(
                "/api/v1/orders",
                headers=headers,
                params={
                    "sort": sort,
                    "page_size": 1,
                    "customer_id": catalog[0]["id"],
                    "status": "new",
                },
            )
        ).json()
        assert page["total"] == 2 and page["items"][0]["total"] == expected
    page = (
        await client.get(
            "/api/v1/orders",
            headers=headers,
            params={
                "date_from": "2000-01-01T00:00:00Z",
                "date_to": "2001-01-01T00:00:00Z",
            },
        )
    ).json()
    assert page["total"] == 0
    for params in [
        {"sort": "id;DROP TABLE orders"},
        {"page_size": 101},
        {"date_from": "2026-01-01T00:00:00"},
        {"date_from": "2026-01-01T00:00:00Z", "date_to": "2025-01-01T00:00:00Z"},
    ]:
        assert (
            await client.get("/api/v1/orders", headers=headers, params=params)
        ).status_code == 422


@pytest.mark.parametrize("quantity", [0, -1, 1.5, 1_000_001])
async def test_invalid_quantity(client, auth, catalog, quantity):
    response = await client.post(
        "/api/v1/orders",
        headers=auth[0],
        json={
            "customer_id": catalog[0]["id"],
            "items": [{"product_id": catalog[1]["id"], "quantity": quantity}],
        },
    )
    assert response.status_code == 422
