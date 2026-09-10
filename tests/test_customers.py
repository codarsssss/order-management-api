import pytest


async def test_customer_crud_search_and_pagination(client, auth):
    headers = auth[0]
    response = await client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "name": "Ivan",
            "email": "ivan@example.com",
            "comment": "Call first",
        },
    )
    assert response.status_code == 201
    path = f"/api/v1/customers/{response.json()['id']}"
    assert (await client.get(path, headers=headers)).json()["name"] == "Ivan"
    for search in ["IVAN", "@example.com"]:
        page = (
            await client.get(
                "/api/v1/customers",
                headers=headers,
                params={
                    "search": search,
                    "page_size": 1,
                },
            )
        ).json()
        assert page["total"] == 1
        assert len(page["items"]) == 1
    page = (await client.get("/api/v1/customers?page=2&page_size=1", headers=headers)).json()
    assert page["total"] == 1 and page["items"] == []
    updated = await client.patch(path, headers=headers, json={"name": "Petr", "comment": None})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Petr" and updated.json()["comment"] is None
    assert (await client.patch(path, headers=headers, json={"name": None})).status_code == 422
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(path, headers=headers)).status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
async def test_foreign_customer(client, auth, catalog, method):
    path = f"/api/v1/customers/{catalog[0]['id']}"
    kwargs = {"json": {"name": "Hacked"}} if method == "patch" else {}
    assert (await client.request(method, path, headers=auth[1], **kwargs)).status_code == 404
    assert (await client.get("/api/v1/customers", headers=auth[1])).json()["total"] == 0


async def test_referenced_customer_cannot_be_deleted(client, auth, order):
    response = await client.delete(f"/api/v1/customers/{order['customer_id']}", headers=auth[0])
    assert response.status_code == 409
    assert "SQL" not in response.text
