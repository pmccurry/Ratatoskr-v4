"""Custom middleware for the application."""

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies."""

    def __init__(self, app, max_body_size: int = 1_048_576):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": "Request body exceeds maximum size",
                    }
                },
            )
        return await call_next(request)
