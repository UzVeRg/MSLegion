from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.core.database import get_session
from app.main import app


async def two_chunks(body: bytes) -> AsyncIterator[bytes]:
    yield body[:-1]
    yield body[-1:]


@pytest.mark.parametrize("streamed", [False, True], ids=["content-length", "chunked"])
@pytest.mark.parametrize(
    ("method", "path", "limit"),
    [
        ("POST", "/api/v1/auth/telegram", 131_072),
        ("PUT", "/api/v1/auth/me/telegram-notifications", 131_072),
        ("POST", "/api/v1/users", 131_072),
        ("POST", "/api/v1/communities", 131_072),
        ("POST", "/api/v1/callbacks/server-status", 131_072),
        ("POST", "/api/v1/callbacks/events", 1_048_576),
    ],
)
async def test_oversize_json_rejected_before_decoding(
    client, monkeypatch, method, path, limit, streamed
):
    def unexpected_session():
        pytest.fail("При превышении лимита тело должно быть отклонено до зависимостей API")

    monkeypatch.setitem(app.dependency_overrides, get_session, unexpected_session)
    decode = AsyncMock()
    monkeypatch.setattr(Request, "json", decode)
    body = b"{}".ljust(limit + 1)
    response = await client.request(
        method,
        path,
        headers={"Content-Type": "application/json", "X-Request-ID": "body-limit-test"},
        content=two_chunks(body) if streamed else body,
    )

    assert response.status_code == 413
    assert response.headers["X-Request-ID"] == "body-limit-test"
    error = response.json()["error"]
    assert error["request_id"] == "body-limit-test"
    assert error["code"] == "request_body_too_large"
    decode.assert_not_awaited()


@pytest.mark.parametrize("streamed", [False, True], ids=["content-length", "chunked"])
async def test_login_json_at_limit_reaches_schema_validation(client, streamed):
    # Пустому объекту не хватает обязательного поля init_data.
    body = b"{}".ljust(131_072)
    response = await client.post(
        "/api/v1/auth/telegram",
        headers={"Content-Type": "application/json"},
        content=two_chunks(body) if streamed else body,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_documents_limits_for_all_json_bodies():
    paths = app.openapi()["paths"]
    callback = paths["/api/v1/callbacks/events"]["post"]
    assert callback["x-max-body-bytes"] == 1_048_576
    for path, operations in paths.items():
        for method, operation in operations.items():
            if "application/json" in operation.get("requestBody", {}).get("content", {}):
                responses = operation["responses"]
                assert "413" in responses, (method, path)
                schema = responses["413"]["content"]["application/json"]["schema"]
                assert schema["$ref"] == "#/components/schemas/ErrorEnvelope", (method, path)
