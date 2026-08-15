"""Tests for the application-level error model and exception handlers."""

from app.domain.exceptions import ConflictError, NotFoundError
from fastapi import FastAPI
from httpx import AsyncClient


def _mount_test_routes(app: FastAPI) -> None:
    """Attach throwaway routes that exercise the exception handlers."""
    if getattr(app.state, "_test_routes_mounted", False):
        return

    @app.get("/_test/not-found")
    async def _not_found() -> None:
        raise NotFoundError("media not found")

    @app.get("/_test/conflict")
    async def _conflict() -> None:
        raise ConflictError("duplicate scan")

    @app.get("/_test/broken")
    async def _broken() -> None:
        raise ValueError("boom")

    @app.get("/_test/validation")
    async def _validation(limit: int) -> int:
        return limit

    app.state._test_routes_mounted = True


async def test_not_found_error_envelope(app: FastAPI, client: AsyncClient) -> None:
    _mount_test_routes(app)
    response = await client.get("/_test/not-found")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "media not found"


async def test_conflict_error_envelope(app: FastAPI, client: AsyncClient) -> None:
    _mount_test_routes(app)
    response = await client.get("/_test/conflict")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_unhandled_error_is_sanitized(app: FastAPI, client: AsyncClient) -> None:
    _mount_test_routes(app)
    response = await client.get("/_test/broken")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Internal server error"
    assert "Traceback" not in response.text
    assert "boom" not in response.text


async def test_request_validation_error(app: FastAPI, client: AsyncClient) -> None:
    _mount_test_routes(app)
    response = await client.get("/_test/validation")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


async def test_unknown_route_matches_contract(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"
