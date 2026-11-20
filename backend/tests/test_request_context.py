import pytest


@pytest.mark.parametrize(
    ("path", "method", "codes"),
    [
        ("/ready", "get", (503,)),
        ("/api/v1/users", "post", (401, 409, 422)),
        ("/api/v1/users", "get", (401, 422)),
        ("/api/v1/users/{user_id}", "get", (401, 404, 422)),
        ("/api/v1/callbacks/events", "post", (401, 409, 422)),
        ("/api/v1/admin/callbacks", "get", (401, 422)),
        ("/api/v1/admin/status", "get", (401,)),
    ],
)
async def test_openapi_describes_error_envelope(client, path, method, codes):
    spec = (await client.get("/openapi.json")).json()
    responses = spec["paths"][path][method]["responses"]
    for code in codes:
        schema = responses[str(code)]["content"]["application/json"]["schema"]
        name = schema["$ref"].rsplit("/", 1)[1]
        assert "error" in spec["components"]["schemas"][name]["required"]


async def test_request_id_is_preserved(client) -> None:
    response = await client.get(
        "/health",
        headers={"X-Request-ID": "test-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


async def test_request_id_is_generated_for_invalid_value(client) -> None:
    response = await client.get(
        "/health",
        headers={"X-Request-ID": "invalid request id"},
    )

    request_id = response.headers["X-Request-ID"]
    assert request_id != "invalid request id"
    assert len(request_id) == 32


async def test_not_found_uses_error_envelope(client) -> None:
    response = await client.get(
        "/missing-endpoint",
        headers={"X-Request-ID": "missing-endpoint-test"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Not Found",
            "request_id": "missing-endpoint-test",
        }
    }
