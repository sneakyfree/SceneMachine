"""Tests for pipeline API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_pipeline_status_not_found(app):
    """GET /api/v1/pipeline/status/{id} returns 404 for unknown pipeline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/pipeline/status/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_pipeline_requires_body(app):
    """POST /api/v1/pipeline/start without body should return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/pipeline/start")
    assert response.status_code == 422
