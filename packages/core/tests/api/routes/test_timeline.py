"""Tests for timeline API routes."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_get_tracks_requires_auth(app):
    """GET /api/v1/timeline/projects/{id}/tracks should require auth."""
    project_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/timeline/projects/{project_id}/tracks"
        )
    # Should return 401/403 (not 404) since route exists but requires auth
    assert response.status_code in (401, 403, 422)
