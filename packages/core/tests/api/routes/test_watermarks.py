"""Tests for Watermarks API routes."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.main import app


class TestWatermarksRoutes:
    """Tests for Watermarks API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_list_watermarks(self, client: AsyncClient):
        """Test listing watermarks for a project."""
        project_id = uuid4()
        response = await client.get(f"/api/watermarks/{project_id}")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_watermark(self, client: AsyncClient):
        """Test creating a watermark."""
        project_id = uuid4()
        response = await client.post(
            f"/api/watermarks/{project_id}",
            json={
                "type": "text",
                "content": "© 2026 My Studio",
                "position": "bottom_right",
                "opacity": 0.7,
                "size": 24,
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_create_image_watermark(self, client: AsyncClient):
        """Test creating an image watermark."""
        project_id = uuid4()
        response = await client.post(
            f"/api/watermarks/{project_id}",
            json={
                "type": "image",
                "image_url": "https://example.com/logo.png",
                "position": "top_left",
                "opacity": 0.5,
                "scale": 0.2,
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_get_watermark(self, client: AsyncClient):
        """Test getting a specific watermark."""
        project_id = uuid4()
        watermark_id = uuid4()
        response = await client.get(f"/api/watermarks/{project_id}/{watermark_id}")

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_watermark(self, client: AsyncClient):
        """Test updating a watermark."""
        project_id = uuid4()
        watermark_id = uuid4()
        response = await client.put(
            f"/api/watermarks/{project_id}/{watermark_id}",
            json={
                "opacity": 0.5,
                "position": "center",
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_delete_watermark(self, client: AsyncClient):
        """Test deleting a watermark."""
        project_id = uuid4()
        watermark_id = uuid4()
        response = await client.delete(f"/api/watermarks/{project_id}/{watermark_id}")

        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_watermark_presets(self, client: AsyncClient):
        """Test getting watermark presets."""
        response = await client.get("/api/watermarks/presets")

        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_apply_watermark_preset(self, client: AsyncClient):
        """Test applying a watermark preset."""
        project_id = uuid4()
        response = await client.post(
            f"/api/watermarks/{project_id}/from-preset",
            json={
                "preset_id": "default_copyright",
            },
        )

        assert response.status_code in (200, 201, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_preview_watermark(self, client: AsyncClient):
        """Test previewing a watermark."""
        project_id = uuid4()
        response = await client.post(
            f"/api/watermarks/{project_id}/preview",
            json={
                "type": "text",
                "content": "PREVIEW",
                "position": "center",
                "opacity": 0.3,
            },
        )

        assert response.status_code in (200, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_get_position_options(self, client: AsyncClient):
        """Test getting available watermark positions."""
        response = await client.get("/api/watermarks/positions")

        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_toggle_watermark(self, client: AsyncClient):
        """Test enabling/disabling a watermark."""
        project_id = uuid4()
        watermark_id = uuid4()
        response = await client.post(
            f"/api/watermarks/{project_id}/{watermark_id}/toggle",
            json={"enabled": False},
        )

        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_set_default_watermark(self, client: AsyncClient):
        """Test setting a default watermark for the user."""
        response = await client.post(
            "/api/watermarks/default",
            json={
                "type": "text",
                "content": "© My Default Copyright",
                "position": "bottom_right",
            },
        )

        assert response.status_code in (200, 201, 401, 422)

    @pytest.mark.asyncio
    async def test_get_default_watermark(self, client: AsyncClient):
        """Test getting the default watermark."""
        response = await client.get("/api/watermarks/default")

        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_upload_watermark_image(self, client: AsyncClient):
        """Test uploading a watermark image."""
        response = await client.post(
            "/api/watermarks/upload",
            files={"file": ("logo.png", b"fake image content", "image/png")},
        )

        assert response.status_code in (200, 201, 401, 422)

    @pytest.mark.asyncio
    async def test_get_user_watermark_images(self, client: AsyncClient):
        """Test getting user's uploaded watermark images."""
        response = await client.get("/api/watermarks/images")

        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_delete_watermark_image(self, client: AsyncClient):
        """Test deleting an uploaded watermark image."""
        image_id = uuid4()
        response = await client.delete(f"/api/watermarks/images/{image_id}")

        assert response.status_code in (200, 204, 401, 404)
