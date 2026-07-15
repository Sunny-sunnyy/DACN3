"""Safe error types matching the architecture guide error shape."""

from typing import Any


class AppError(Exception):
    """Base application error with code, message, and optional details."""

    def __init__(self, code: str, message: str, details: list[Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or []


class ValidationError(AppError):
    """Request validation failure."""

    def __init__(self, message: str, details: list[Any] | None = None) -> None:
        super().__init__(code="VALIDATION_ERROR", message=message, details=details)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str) -> None:
        super().__init__(code="NOT_FOUND", message=message)


def error_response(code: str, message: str, details: list[Any] | None = None) -> dict[str, Any]:
    """Return the safe error shape used by all endpoints."""
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }
    return body
