"""Scan + media API tests via ASGI client (real PostgreSQL)."""

import uuid
from typing import Any

from app.domain.scan import STAGE_ORDER
from httpx import AsyncClient


def _media_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "original_filename": "sample.png",
        "media_type": "IMAGE",
        "storage_path": "s3://bucket/ref-123",
        "mime_type": "image/png",
        "size_bytes": 2048,
        "sha256": "a" * 64,
        "width": 640,
        "height": 480,
    }
    payload.update(overrides)
    return payload


async def test_create_media(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/media", json=_media_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["error"] is None
    data = body["data"]
    assert data["original_filename"] == "sample.png"
    assert data["media_type"] == "IMAGE"
    assert "storage_path" not in data


async def test_create_media_rejects_bad_sha256(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/media", json=_media_payload(sha256="not-a-valid-hash")
    )
    assert resp.status_code == 422
    assert resp.json()["data"] is None


async def test_create_scan(client: AsyncClient) -> None:
    media_resp = await client.post("/api/v1/media", json=_media_payload())
    media_id = media_resp.json()["data"]["id"]

    resp = await client.post("/api/v1/scans", json={"media_id": media_id})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["status"] == "CREATED"
    assert data["media_id"] == media_id
    assert len(data["stages"]) == len(STAGE_ORDER)
    assert data["stages"][0]["name"] == "validate"
    assert [s["sequence"] for s in data["stages"]] == list(range(len(STAGE_ORDER)))
    assert data["media"]["id"] == media_id


async def test_create_scan_unknown_media_returns_404(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/scans", json={"media_id": str(uuid.uuid4())})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_create_scan_invalid_media_id_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/scans", json={"media_id": "not-a-uuid"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_get_scan_detail(client: AsyncClient) -> None:
    media_resp = await client.post("/api/v1/media", json=_media_payload())
    media_id = media_resp.json()["data"]["id"]
    scan_resp = await client.post("/api/v1/scans", json={"media_id": media_id})
    scan_id = scan_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/scans/{scan_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == scan_id
    assert data["media"]["id"] == media_id
    assert len(data["stages"]) == len(STAGE_ORDER)


async def test_get_scan_not_found(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/scans/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_list_scans_pagination(client: AsyncClient) -> None:
    media_resp = await client.post("/api/v1/media", json=_media_payload())
    media_id = media_resp.json()["data"]["id"]
    for _ in range(3):
        await client.post("/api/v1/scans", json={"media_id": media_id})

    resp = await client.get("/api/v1/scans?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total": 3,
        "pages": 2,
    }

    resp2 = await client.get("/api/v1/scans?page=2&page_size=2")
    assert len(resp2.json()["data"]) == 1


async def test_list_scans_filters_by_status(client: AsyncClient) -> None:
    media_resp = await client.post("/api/v1/media", json=_media_payload())
    media_id = media_resp.json()["data"]["id"]
    await client.post("/api/v1/scans", json={"media_id": media_id})

    resp = await client.get("/api/v1/scans?status=FAILED")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
