import pytest


@pytest.mark.parametrize("price", ["-0.01", "10000000000.00", "1.001", "NaN", "Infinity"])
async def test_invalid_price(client, auth, price):
    response = await client.post(
        "/api/v1/products",
        headers=auth[0],
        json={
            "name": "Product",
            "price": price,
        },
    )
    assert response.status_code == 422


async def test_products_crud_and_filters(client, auth):
    headers = auth[0]
    for name, price, active in [("Free", "0", True), ("Work", "99.99", True), ("Old", "50", False)]:
        response = await client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "name": name,
                "price": price,
                "is_active": active,
            },
        )
        assert response.status_code == 201
    for params, expected in [
        ({"min_price": "90", "max_price": "100", "is_active": True}, "Work"),
        ({"is_active": False}, "Old"),
        ({"search": "free"}, "Free"),
    ]:
        page = (await client.get("/api/v1/products", headers=headers, params=params)).json()
        assert page["total"] == 1
        assert page["items"][0]["name"] == expected
    path = f"/api/v1/products/{response.json()['id']}"
    patched = await client.patch(path, headers=headers, json={"price": "20.00"})
    assert patched.json()["price"] == "20.00"
    assert (await client.get(path, headers=headers)).status_code == 200
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (
        await client.get("/api/v1/products?min_price=100&max_price=1", headers=headers)
    ).status_code == 422


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
async def test_foreign_product(client, auth, catalog, method):
    path = f"/api/v1/products/{catalog[1]['id']}"
    kwargs = {"json": {"price": "1"}} if method == "patch" else {}
    assert (await client.request(method, path, headers=auth[1], **kwargs)).status_code == 404
    assert (await client.get("/api/v1/products", headers=auth[1])).json()["total"] == 0
