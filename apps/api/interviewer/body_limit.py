"""Bound actual API request bytes before JSON or multipart parsing."""
import asyncio

from starlette.responses import JSONResponse


REQUEST_LIMIT = 11 * 1024 * 1024
RECEIVE_TIMEOUT = 30


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api") or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        # Authentication/Host/CSRF middleware wraps this middleware and rejects
        # unauthorized requests before this bounded allocation. Pre-reading
        # prevents a parser from committing an action before overflow is known.
        body = bytearray()
        try:
            async with asyncio.timeout(RECEIVE_TIMEOUT):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > REQUEST_LIMIT:
                        await JSONResponse({"detail": "Request exceeds upload limit"}, status_code=413)(scope, receive, send)
                        return
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"detail": "Request body timed out. Retry the upload or paste text."}, status_code=408)(scope, receive, send)
            return

        pending = True
        async def bounded_receive():
            nonlocal pending
            if pending:
                pending = False
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(scope, bounded_receive, send)
