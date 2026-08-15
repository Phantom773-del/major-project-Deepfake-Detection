"""Tests for the health endpoint contract."""

from httpx import AsyncClient


async def test_health_returns_ok_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["error"] is None
    data = body["data"]
    assert data["status"] == "ok"
    assert data["service"] == "PHANTOM PHOENIX Backend"
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "/api/v1"


async def test_health_content_type(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.headers["content-type"].startswith("application/json")
