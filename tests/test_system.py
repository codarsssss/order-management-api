async def test_health_and_openapi(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert (await client.get("/docs")).status_code == 200
    schema = (await client.get("/openapi.json")).json()
    assert len(schema["paths"]) == 14
    assert (
        schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"][
            "tokenUrl"
        ]
        == "/api/v1/auth/login"
    )
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            assert operation["summary"]
            if "/auth/" not in path and path != "/health":
                assert operation["security"]
