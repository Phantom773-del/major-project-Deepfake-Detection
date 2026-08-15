"""Versioned API router assembly."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, media, scans

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(media.router)
api_router.include_router(scans.router)
