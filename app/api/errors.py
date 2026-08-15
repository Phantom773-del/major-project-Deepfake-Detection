"""API exception handling.

Translates domain exceptions and framework errors into the stable error envelope
defined in ``docs/API_CONTRACTS.md``. Internal details (stack traces, database
errors) are logged but never returned to clients.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import AppError
from app.schemas.common import Envelope, ErrorBody

logger = logging.getLogger(__name__)


def _error_response(
    request: Request, code: str, message: str, status_code: int, details: object = None
) -> JSONResponse:
    body = Envelope[None](
        data=None,
        error=ErrorBody(code=code, message=message, details=details),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """Register all application-level exception handlers."""

    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return _error_response(_request, exc.code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            request, "VALIDATION_ERROR", "Request validation failed", 422, exc.errors()
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(request, "HTTP_ERROR", str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(request, "INTERNAL_ERROR", "Internal server error", 500)
