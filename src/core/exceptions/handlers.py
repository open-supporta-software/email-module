import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse

from src.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from src.core.exceptions import (
    ValidationError as AppValidationError,
)
from src.core.settings import settings
from src.core.settings.logger import app_logger


def create_error_response(
    exc: AppError,
    request_id: str,
    *,
    include_traceback: bool = False,
) -> ORJSONResponse:
    """Convert AppError to a standardized ORJSONResponse."""
    error_dict = exc.to_dict()

    # Add request ID if available
    error_dict["request_id"] = request_id

    # Add traceback in debug mode
    if include_traceback and settings.DEBUG:
        error_dict["traceback"] = traceback.format_exc()

    return ORJSONResponse(status_code=exc.status_code, content=error_dict, headers=exc.headers)


def register_error_handlers(app: FastAPI) -> None:  # noqa: C901
    """Register global error handlers for all custom and system exceptions."""

    def _log_exception(level: str, request: Request, exc: Exception, message: str):
        """Helper for structured logging."""
        request_id = request.headers.get(settings.LOGGER.REQUEST_ID_HEADER) or str(uuid.uuid4())
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }

        if settings.DEBUG:
            log_data["traceback"] = traceback.format_exc()

        getattr(app_logger, level)(
            f"{message}: {type(exc).__name__} - {exc!s}",
            extra=log_data,
        )
        return request_id

    #
    # === AppError and its subclasses ===
    #
    @app.exception_handler(AppError)
    def handle_app_error(request: Request, exc: AppError) -> ORJSONResponse:
        request_id = _log_exception("error", request, exc, "Application exception")
        return create_error_response(exc, request_id, include_traceback=True)

    @app.exception_handler(AppValidationError)
    def handle_app_validation_error(request: Request, exc: AppValidationError) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "Validation error")
        return create_error_response(exc, request_id)

    @app.exception_handler(NotFoundError)
    def handle_not_found_error(request: Request, exc: NotFoundError) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "Resource not found")
        return create_error_response(exc, request_id)

    @app.exception_handler(ConflictError)
    def handle_conflict_error(request: Request, exc: ConflictError) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "Conflict error")
        return create_error_response(exc, request_id)

    @app.exception_handler(UnauthorizedError)
    def handle_unauthorized_error(request: Request, exc: UnauthorizedError) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "Unauthorized access")
        return create_error_response(exc, request_id)

    @app.exception_handler(ForbiddenError)
    def handle_forbidden_error(request: Request, exc: ForbiddenError) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "Forbidden access")
        return create_error_response(exc, request_id)

    @app.exception_handler(BadRequestError)
    def handle_bad_request_error(request: Request, exc: BadRequestError) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "Bad request")
        return create_error_response(exc, request_id)

    @app.exception_handler(DatabaseError)
    def handle_database_error(request: Request, exc: DatabaseError) -> ORJSONResponse:
        request_id = _log_exception("error", request, exc, "Database error")
        return create_error_response(exc, request_id, include_traceback=True)

    @app.exception_handler(ExternalServiceError)
    def handle_external_service_error(
        request: Request, exc: ExternalServiceError
    ) -> ORJSONResponse:
        request_id = _log_exception("error", request, exc, "External service error")
        return create_error_response(exc, request_id, include_traceback=True)

    @app.exception_handler(ServiceUnavailableError)
    def handle_service_unavailable_error(
        request: Request, exc: ServiceUnavailableError
    ) -> ORJSONResponse:
        request_id = _log_exception("error", request, exc, "Service unavailable")
        return create_error_response(exc, request_id, include_traceback=True)

    @app.exception_handler(InternalServerError)
    def handle_internal_server_error(request: Request, exc: InternalServerError) -> ORJSONResponse:
        request_id = _log_exception("error", request, exc, "Internal server error")
        return create_error_response(exc, request_id, include_traceback=True)

    #
    # === FastAPI / Pydantic exceptions ===
    #
    @app.exception_handler(HTTPException)
    def handle_http_exception(request: Request, exc: HTTPException) -> ORJSONResponse:
        request_id = _log_exception("warning", request, exc, "HTTP exception")
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": f"HTTP_{exc.status_code}", "message": exc.detail},
                "request_id": request_id,
            },
            headers=getattr(exc, "headers", None),
        )

    #
    # === Fallback for any unhandled exception ===
    #
    @app.exception_handler(Exception)
    def handle_unhandled_exception(request: Request, exc: Exception) -> ORJSONResponse:
        request_id = _log_exception("error", request, exc, "Unhandled exception")
        error_message = "Internal server error"
        details = {}

        if settings.DEBUG:
            error_message = f"{type(exc).__name__}: {exc!s}"
            details = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
            }

        app_error = InternalServerError(message=error_message, details=details)
        return create_error_response(app_error, request_id, include_traceback=True)
