import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.settings import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable):
        super().__init__(app)
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)

        self._clean_old_requests(client_ip)

        if len(self.requests[client_ip]) >= settings.SECURITY.RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        self.requests[client_ip].append(time.time())

        return await call_next(request)

    @classmethod
    def _get_client_ip(cls, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, client_ip: str) -> None:
        current_time = time.time()
        window_start = current_time - settings.SECURITY.RATE_LIMIT_WINDOW_SECONDS

        self.requests[client_ip] = [
            timestamp for timestamp in self.requests[client_ip] if timestamp > window_start
        ]
