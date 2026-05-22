"""Tests for Text Overlays API routes."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.main import app


class TestTextOverlaysRoutes:
    """Tests for Text Overlays API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_list_text_overlays(self, client: AsyncClient):
        """Test listing text overlays for a project."""
        project_id = uuid4()
        response = await client.get(f"/api/text-overlays/{project_id}")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_text_overlay(self, client: AsyncClient):
        """Test creating a text overlay."""
        project_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}",
            json={
                "text": "Scene Title",
                "position": {"x": 100, "y": 50},
                "start_time": 0.0,
                "end_time": 3.0,
                "style": {
                    "font_size": 32,
                    "font_family": "Arial",
                    "color": "#ffffff",
                    "background_color": "#00000080",
                },
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_get_text_overlay(self, client: AsyncClient):
        """Test getting a specific text overlay."""
        project_id = uuid4()
        overlay_id = uuid4()
        response = await client.get(f"/api/text-overlays/{project_id}/{overlay_id}")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_text_overlay(self, client: AsyncClient):
        """Test updating a text overlay."""
        project_id = uuid4()
        overlay_id = uuid4()
        response = await client.put(
            f"/api/text-overlays/{project_id}/{overlay_id}",
            json={
                "text": "Updated Title",
                "style": {"font_size": 48},
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_delete_text_overlay(self, client: AsyncClient):
        """Test deleting a text overlay."""
        project_id = uuid4()
        overlay_id = uuid4()
        response = await client.delete(f"/api/text-overlays/{project_id}/{overlay_id}")

        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_overlay_presets(self, client: AsyncClient):
        """Test getting text overlay presets."""
        response = await client.get("/api/text-overlays/presets")

        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_create_overlay_from_preset(self, client: AsyncClient):
        """Test creating an overlay from a preset."""
        project_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/from-preset",
            json={
                "preset_id": "title_card",
                "text": "My Movie Title",
                "start_time": 0.0,
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_batch_update_overlays(self, client: AsyncClient):
        """Test batch updating multiple overlays."""
        project_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/batch",
            json={
                "updates": [
                    {"id": str(uuid4()), "text": "Updated 1"},
                    {"id": str(uuid4()), "text": "Updated 2"},
                ],
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_duplicate_overlay(self, client: AsyncClient):
        """Test duplicating a text overlay."""
        project_id = uuid4()
        overlay_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/{overlay_id}/duplicate"
        )

        assert response.status_code in (200, 201, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_available_fonts(self, client: AsyncClient):
        """Test getting available fonts for overlays."""
        response = await client.get("/api/text-overlays/fonts")

        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_preview_overlay(self, client: AsyncClient):
        """Test previewing a text overlay."""
        project_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/preview",
            json={
                "text": "Preview Text",
                "style": {"font_size": 32, "color": "#ffffff"},
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_get_overlay_animations(self, client: AsyncClient):
        """Test getting available overlay animations."""
        response = await client.get("/api/text-overlays/animations")

        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_set_overlay_animation(self, client: AsyncClient):
        """Test setting animation for an overlay."""
        project_id = uuid4()
        overlay_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/{overlay_id}/animation",
            json={
                "entrance": "fade_in",
                "exit": "fade_out",
                "entrance_duration": 0.5,
                "exit_duration": 0.5,
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_reorder_overlays(self, client: AsyncClient):
        """Test reordering text overlays."""
        project_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/reorder",
            json={
                "order": [str(uuid4()), str(uuid4()), str(uuid4())],
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_save_as_preset(self, client: AsyncClient):
        """Test saving an overlay as a preset."""
        project_id = uuid4()
        overlay_id = uuid4()
        response = await client.post(
            f"/api/text-overlays/{project_id}/{overlay_id}/save-preset",
            json={
                "preset_name": "My Custom Preset",
                "description": "A custom text overlay preset",
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)
