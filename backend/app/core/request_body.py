from fastapi.routing import APIRoute
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import Message, Receive, Scope, Send

MAX_JSON_BODY_BYTES = 128 * 1024
MAX_CALLBACK_BODY_BYTES = 1024 * 1024


class LimitedJSONRoute(APIRoute):
    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.body_field is None or scope["method"] not in self.methods:
            await super().handle(scope, receive, send)
            return

        limit = (self.openapi_extra or {}).get("x-max-body-bytes", MAX_JSON_BODY_BYTES)
        too_large = HTTPException(413, "Размер тела запроса превышает допустимый предел")
        try:
            declared = int(Headers(scope=scope).get("content-length", "0"))
        except ValueError:
            raise HTTPException(400, "Недопустимый заголовок Content-Length") from None
        if declared > limit:
            raise too_large

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise too_large
            return message

        # FastAPI получает только допустимые фрагменты до сборки тела и разбора JSON.
        await super().handle(scope, limited_receive, send)
