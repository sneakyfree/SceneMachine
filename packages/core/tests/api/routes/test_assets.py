"""Tests for assets API routes."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_list_assets_requires_auth(app):
    """GET /api/v1/assets/projects/{id}/assets should require auth."""
    project_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/assets/projects/{project_id}/assets")
    # Should return 401/403 (not 404) since route exists but requires auth
    assert response.status_code in (401, 403, 422)
