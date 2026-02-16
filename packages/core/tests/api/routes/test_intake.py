"""Tests for intake API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_supported_formats_returns_200(app):
    """GET /api/v1/intake/supported-formats should return 200 with format list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/intake/supported-formats")
    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert len(data["formats"]) >= 3  # fountain, fdx, pdf, txt


@pytest.mark.asyncio
async def test_parse_text_requires_body(app):
    """POST /api/v1/intake/parse/text without body should return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/intake/parse/text")
    assert response.status_code == 422
