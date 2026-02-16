"""Tests for character lab API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_capabilities_returns_200(app):
    """GET /api/v1/character-lab/capabilities should return 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/character-lab/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "face_embedding" in data
    assert "voice_cloning" in data
    assert "image_generation" in data
