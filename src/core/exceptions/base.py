"""Base exception classes for the application."""

from typing import Any


class AppError(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.headers = headers or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": {"code": self.error_code, "message": self.message, "details": self.details},
        }


class ValidationError(AppError):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=422, details=details, **kwargs)


class NotFoundError(AppError):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource: str | None = None,
        resource_id: Any | None = None,
        **kwargs,
    ):
        details = {}
        if resource:
            details["resource"] = resource
        if resource_id is not None:
            details["resource_id"] = resource_id

        super().__init__(message=message, status_code=404, details=details, **kwargs)


class ConflictError(AppError):
    """Exception raised for conflicts (e.g., duplicate resources)."""

    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None, **kwargs):
        super().__init__(message=message, status_code=409, details=details, **kwargs)


class UnauthorizedError(AppError):
    """Exception raised for authentication/authorization errors."""

    def __init__(
        self,
        message: str = "Unauthorized",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=401, details=details, **kwargs)


class ForbiddenError(AppError):
    """Exception raised for forbidden access."""

    def __init__(
        self,
        message: str = "Forbidden",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=403, details=details, **kwargs)


class BadRequestError(AppError):
    """Exception raised for bad requests."""

    def __init__(
        self,
        message: str = "Bad request",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=400, details=details, **kwargs)


class InternalServerError(AppError):
    """Exception raised for internal server errors."""

    def __init__(
        self,
        message: str = "Internal server error",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=500, details=details, **kwargs)


class ServiceUnavailableError(AppError):
    """Exception raised when a service is unavailable."""

    def __init__(
        self,
        message: str = "Service unavailable",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=503, details=details, **kwargs)


class DatabaseError(AppError):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str = "Database error",
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message=message, status_code=500, details=details, **kwargs)


class ExternalServiceError(AppError):
    """Exception raised for external service errors."""

    def __init__(
        self,
        message: str = "External service error",
        service: str | None = None,
        details: dict[str, Any] | None = None,
        **kwargs,
    ):
        error_details = details or {}
        if service:
            error_details["service"] = service

        super().__init__(message=message, status_code=502, details=error_details, **kwargs)
