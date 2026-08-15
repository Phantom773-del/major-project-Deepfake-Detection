"""Domain-level application exceptions.

These are raised by services/domain code and translated to HTTP responses by the
API exception handlers. They never expose internals, stack traces or database
details to clients.
"""

from typing import Any


class AppError(Exception):
    """Base application error carrying a stable machine-readable code."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailure(AppError):
    """Raised for application-level validation failures (after HTTP-layer checks)."""

    status_code = 400
    code = "VALIDATION_ERROR"
