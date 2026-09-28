from fastapi.testclient import TestClient

from app.main import app


def test_request_id_is_preserved() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"X-Request-ID": "test-request-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_request_id_is_generated_for_invalid_value() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"X-Request-ID": "invalid request id"},
        )

    request_id = response.headers["X-Request-ID"]
    assert request_id != "invalid request id"
    assert len(request_id) == 32


def test_not_found_uses_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get(
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
