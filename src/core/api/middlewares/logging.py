import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.settings import settings
from src.core.settings.logger import app_logger

MAX_BODY_LOG_LENGTH = 500


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log relevant information."""

        request_id = request.headers.get(settings.LOGGER.REQUEST_ID_HEADER, str(uuid.uuid4()))

        start_time = time.time()

        if settings.LOGGER.LOG_REQUESTS:
            await self._log_request(request, request_id)

        try:
            response = await call_next(request)

            process_time = time.time() - start_time

            if settings.LOGGER.LOG_REQUESTS:
                await self._log_response(response, request_id, process_time)

            if (
                settings.LOGGER.LOG_SLOW_REQUESTS
                and process_time > settings.LOGGER.SLOW_REQUEST_THRESHOLD
            ):
                app_logger.warning(
                    (
                        f"Slow request: {request.method} {request.url} took "
                        f"{process_time:.3f}s (threshold: "
                        f"{settings.LOGGER.SLOW_REQUEST_THRESHOLD}s)"
                    ),
                    request_id=request_id,
                    method=request.method,
                    url=str(request.url),
                    process_time=process_time,
                    threshold=settings.LOGGER.SLOW_REQUEST_THRESHOLD,
                )

            response.headers[settings.LOGGER.REQUEST_ID_HEADER] = request_id

            return response

        except Exception as exc:
            process_time = time.time() - start_time

            app_logger.error(
                f"Request failed: {request.method} {request.url} - {exc!s}",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                process_time=process_time,
                exception=str(exc),
            )
            raise

    async def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request details."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
        }

        if settings.LOGGER.LOG_REQUEST_BODY:
            try:
                body = await request.body()
                if body:
                    try:
                        log_data["body"] = body.decode("utf-8")
                    except UnicodeDecodeError:
                        log_data["body"] = str(body)
            except Exception as exc:  # noqa: BLE001
                app_logger.warning(
                    f"Failed to read request body: {type(exc).__name__}: {exc}",
                    request_id=request_id,
                    exception=str(exc),
                )
                log_data["body"] = "<unable to read body>"

        body_info = ""
        if log_data.get("body"):
            safe_body = (
                log_data["body"][:MAX_BODY_LOG_LENGTH].replace("{", "{{").replace("}", "}}")
            )
            body_info = (
                f" with body: {safe_body}"
                f"{'...' if len(log_data['body']) > MAX_BODY_LOG_LENGTH else ''}"
            )

        app_logger.info(
            (
                f"Incoming request: {log_data['method']} {log_data['url']} "
                f"from {log_data['client_ip']}{body_info}"
            ),
            **log_data,
        )

    @staticmethod
    async def _log_response(response: Response, request_id: str, process_time: float) -> None:
        """Log response details."""
        log_data = {
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time,
            "headers": dict(response.headers),
        }

        if settings.LOGGER.LOG_RESPONSE_BODY and not isinstance(response, StreamingResponse):
            if hasattr(response, "body"):
                log_data["body"] = str(response.body)
            else:
                app_logger.warning(
                    "Failed to read response body: response does not have 'body' attribute",
                    request_id=request_id,
                )
                log_data["body"] = "<unable to read body>"

        body_info = ""
        if log_data.get("body"):
            safe_body = (
                log_data["body"][:MAX_BODY_LOG_LENGTH].replace("{", "{{").replace("}", "}}")
            )
            body_info = (
                f" with body: {safe_body}"
                f"{'...' if len(log_data['body']) > MAX_BODY_LOG_LENGTH else ''}"
            )

        app_logger.info(
            (
                f"Request completed: {log_data['status_code']} "
                f"in {log_data['process_time']:.3f}s{body_info}"
            ),
            **log_data,
        )

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        client = request.client
        return client.host if client else "unknown"
