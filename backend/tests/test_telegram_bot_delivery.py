import json

import pytest
from httpx import AsyncClient, MockTransport, ReadTimeout, Response

from app.telegram.bot import send_message


@pytest.mark.parametrize(
    ("status_code", "response", "expected"),
    [
        (200, {"ok": True}, "sent"),
        (403, {"ok": False}, "failed"),
        (502, {"ok": False}, "uncertain"),
        (200, [], "uncertain"),
    ],
)
async def test_send_message_classifies_telegram_response(status_code, response, expected):
    def respond(request):
        assert request.method == "POST"
        assert request.url.host == "api.telegram.org"
        assert json.loads(request.content) == {"chat_id": 601, "text": "Сервер доступен."}
        return Response(status_code, json=response)

    async with AsyncClient(transport=MockTransport(respond)) as client:
        assert await send_message(client, "123456:test", 601, "Сервер доступен.") == expected


async def test_send_message_treats_timeout_as_uncertain():
    def fail(request):
        raise ReadTimeout("Нет подтверждения доставки", request=request)

    async with AsyncClient(transport=MockTransport(fail)) as client:
        assert await send_message(client, "123456:test", 601, "Сервер доступен.") == "uncertain"
