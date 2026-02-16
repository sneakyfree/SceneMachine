"""Tests for billing API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_billing_plans_returns_200(app):
    """GET /api/v1/billing/plans should return 200 with plan list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/billing/plans")
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data


@pytest.mark.asyncio
async def test_billing_usage_requires_auth(app):
    """GET /api/v1/billing/usage should require authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/billing/usage")
    # Should return 401/403 (not 404)
    assert response.status_code in (401, 403, 422)
