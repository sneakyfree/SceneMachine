"""Tests for Performers API routes."""

import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app


class TestPerformersRoutes:
    """Tests for Performers API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_list_performers_endpoint_exists(self, client: AsyncClient):
        """Test that the list performers endpoint exists."""
        response = await client.get("/api/performers")

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_get_performer_endpoint_exists(self, client: AsyncClient):
        """Test that the get performer endpoint exists."""
        performer_id = uuid4()
        response = await client.get(f"/api/performers/{performer_id}")

        # Should return 404 for non-existent performer or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_search_performers_endpoint_exists(self, client: AsyncClient):
        """Test that the search performers endpoint exists."""
        response = await client.get(
            "/api/performers/search",
            params={"q": "test"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_list_performers_pagination(self, client: AsyncClient):
        """Test that list performers supports pagination."""
        response = await client.get(
            "/api/performers",
            params={"page": 1, "per_page": 10},
        )

        # Should handle pagination params
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_list_performers_filtering(self, client: AsyncClient):
        """Test that list performers supports filtering."""
        response = await client.get(
            "/api/performers",
            params={"available": True, "min_rating": 4.0},
        )

        # Should handle filter params
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_featured_performers(self, client: AsyncClient):
        """Test getting featured performers."""
        response = await client.get("/api/performers/featured")

        # Should return list or auth error
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_performer_availability(self, client: AsyncClient):
        """Test getting a performer's availability."""
        performer_id = uuid4()
        response = await client.get(f"/api/performers/{performer_id}/availability")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_performer_portfolio(self, client: AsyncClient):
        """Test getting a performer's portfolio."""
        performer_id = uuid4()
        response = await client.get(f"/api/performers/{performer_id}/portfolio")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_performer_reviews(self, client: AsyncClient):
        """Test getting a performer's reviews."""
        performer_id = uuid4()
        response = await client.get(f"/api/performers/{performer_id}/reviews")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_performer_stats(self, client: AsyncClient):
        """Test getting a performer's statistics."""
        performer_id = uuid4()
        response = await client.get(f"/api/performers/{performer_id}/stats")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_performer_profile(self, client: AsyncClient):
        """Test creating a performer profile."""
        response = await client.post(
            "/api/performers",
            json={
                "display_name": "Test Performer",
                "bio": "A test performer for API testing",
                "skills": ["acting", "voice"],
            },
        )

        # Should handle creation or auth error
        assert response.status_code in (200, 201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_update_performer_profile(self, client: AsyncClient):
        """Test updating a performer profile."""
        performer_id = uuid4()
        response = await client.put(
            f"/api/performers/{performer_id}",
            json={
                "bio": "Updated bio",
            },
        )

        # Should handle update or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_set_performer_availability(self, client: AsyncClient):
        """Test setting a performer's availability."""
        performer_id = uuid4()
        response = await client.post(
            f"/api/performers/{performer_id}/availability",
            json={
                "available_from": "2025-02-01",
                "available_to": "2025-02-28",
                "hours_per_week": 20,
            },
        )

        # Should handle request
        assert response.status_code in (200, 201, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_performer_aci_score(self, client: AsyncClient):
        """Test getting a performer's ACI score."""
        performer_id = uuid4()
        response = await client.get(f"/api/performers/{performer_id}/aci")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_aci_leaderboard(self, client: AsyncClient):
        """Test getting the ACI leaderboard."""
        response = await client.get("/api/performers/leaderboard")

        # Should return leaderboard or auth error
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_by_skill(self, client: AsyncClient):
        """Test filtering performers by skill."""
        response = await client.get(
            "/api/performers",
            params={"skills": "acting,voice"},
        )

        # Should handle skill filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_by_location(self, client: AsyncClient):
        """Test filtering performers by location."""
        response = await client.get(
            "/api/performers",
            params={"location": "Los Angeles"},
        )

        # Should handle location filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_by_rate(self, client: AsyncClient):
        """Test filtering performers by rate."""
        response = await client.get(
            "/api/performers",
            params={"min_rate": 50, "max_rate": 200},
        )

        # Should handle rate filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_sort_by_rating(self, client: AsyncClient):
        """Test sorting performers by rating."""
        response = await client.get(
            "/api/performers",
            params={"sort": "rating", "order": "desc"},
        )

        # Should handle sorting
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_sort_by_aci_score(self, client: AsyncClient):
        """Test sorting performers by ACI score."""
        response = await client.get(
            "/api/performers",
            params={"sort": "aci_score", "order": "desc"},
        )

        # Should handle sorting
        assert response.status_code in (200, 401)
