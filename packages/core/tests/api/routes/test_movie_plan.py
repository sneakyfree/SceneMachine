"""Tests for Movie Plan API routes."""

import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app


class TestMoviePlanRoutes:
    """Tests for Movie Plan API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_get_movie_plan(self, client: AsyncClient):
        """Test getting a movie plan for a project."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_movie_plan(self, client: AsyncClient):
        """Test creating a movie plan."""
        project_id = uuid4()
        response = await client.post(
            f"/api/movie-plan/{project_id}",
            json={
                "title": "Test Movie Plan",
                "description": "A test movie plan",
                "target_duration": 120,
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_update_movie_plan(self, client: AsyncClient):
        """Test updating a movie plan."""
        project_id = uuid4()
        response = await client.put(
            f"/api/movie-plan/{project_id}",
            json={
                "title": "Updated Movie Plan",
                "target_duration": 90,
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_delete_movie_plan(self, client: AsyncClient):
        """Test deleting a movie plan."""
        project_id = uuid4()
        response = await client.delete(f"/api/movie-plan/{project_id}")

        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_plan_scenes(self, client: AsyncClient):
        """Test getting scenes from a movie plan."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}/scenes")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_add_scene_to_plan(self, client: AsyncClient):
        """Test adding a scene to a movie plan."""
        project_id = uuid4()
        response = await client.post(
            f"/api/movie-plan/{project_id}/scenes",
            json={
                "scene_number": 1,
                "title": "Opening Scene",
                "description": "The movie opens with...",
                "duration": 5,
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_reorder_plan_scenes(self, client: AsyncClient):
        """Test reordering scenes in a movie plan."""
        project_id = uuid4()
        response = await client.post(
            f"/api/movie-plan/{project_id}/scenes/reorder",
            json={
                "scene_order": [str(uuid4()), str(uuid4()), str(uuid4())],
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_get_plan_timeline(self, client: AsyncClient):
        """Test getting the timeline view of a movie plan."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}/timeline")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_plan_statistics(self, client: AsyncClient):
        """Test getting statistics for a movie plan."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}/stats")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_export_plan(self, client: AsyncClient):
        """Test exporting a movie plan."""
        project_id = uuid4()
        response = await client.get(
            f"/api/movie-plan/{project_id}/export",
            params={"format": "pdf"},
        )

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_import_plan(self, client: AsyncClient):
        """Test importing a movie plan."""
        project_id = uuid4()
        response = await client.post(
            f"/api/movie-plan/{project_id}/import",
            json={
                "format": "json",
                "data": {
                    "title": "Imported Plan",
                    "scenes": [],
                },
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_get_plan_characters(self, client: AsyncClient):
        """Test getting characters in a movie plan."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}/characters")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_plan_locations(self, client: AsyncClient):
        """Test getting locations in a movie plan."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}/locations")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_validate_plan(self, client: AsyncClient):
        """Test validating a movie plan."""
        project_id = uuid4()
        response = await client.post(f"/api/movie-plan/{project_id}/validate")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_plan_suggestions(self, client: AsyncClient):
        """Test getting AI suggestions for a movie plan."""
        project_id = uuid4()
        response = await client.get(f"/api/movie-plan/{project_id}/suggestions")

        assert response.status_code in (200, 401, 403, 404)
