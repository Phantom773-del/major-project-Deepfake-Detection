"""Shared API response envelopes.

All API responses follow the contract in ``docs/API_CONTRACTS.md``:
``{data, error, meta}``.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str
    details: Any = None


class Pagination(BaseModel):
    """Pagination metadata shared by list endpoints."""

    page: int
    page_size: int
    total: int
    pages: int


class Meta(BaseModel):
    """Response metadata."""

    request_id: str | None = None
    pagination: Pagination | None = None


class Envelope[T](BaseModel):
    """Stable response envelope: exactly one of ``data``/``error`` is set."""

    data: T | None = None
    error: ErrorBody | None = None
    meta: Meta = Field(default_factory=Meta)
