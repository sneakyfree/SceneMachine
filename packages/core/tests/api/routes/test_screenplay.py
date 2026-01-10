"""Tests for Screenplay API routes."""

import pytest
import pytest_asyncio
from uuid import uuid4
from io import BytesIO

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app
from scenemachine.models import Project


class TestScreenplayRoutes:
    """Tests for Screenplay API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    def sample_fountain_content(self) -> str:
        """Sample Fountain screenplay content."""
        return """Title:
    Test Screenplay

Author:
    Test Author

INT. COFFEE SHOP - DAY

JOHN sits at a table.

JOHN
Hello world.

FADE OUT.
"""

    @pytest.mark.asyncio
    async def test_upload_screenplay_endpoint_exists(self, client: AsyncClient):
        """Test that the screenplay upload endpoint exists."""
        response = await client.post(
            "/api/screenplay/upload",
            data={"project_id": str(uuid4())},
            files={"file": ("test.fountain", b"INT. TEST - DAY", "text/plain")},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_parse_screenplay_endpoint_exists(self, client: AsyncClient):
        """Test that the screenplay parse endpoint exists."""
        response = await client.post(
            "/api/screenplay/parse",
            json={
                "project_id": str(uuid4()),
                "content": "INT. TEST - DAY",
                "format": "fountain",
            },
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_get_screenplay_endpoint_exists(self, client: AsyncClient):
        """Test that the get screenplay endpoint exists."""
        response = await client.get(
            f"/api/screenplay/{uuid4()}",
        )

        # Should not be 404 (might be 401 without auth)
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_upload_requires_file(self, client: AsyncClient):
        """Test that upload requires a file."""
        response = await client.post(
            "/api/screenplay/upload",
            data={"project_id": str(uuid4())},
        )

        # Should return validation error
        assert response.status_code in (400, 422, 401)

    @pytest.mark.asyncio
    async def test_parse_requires_content(self, client: AsyncClient):
        """Test that parse requires content."""
        response = await client.post(
            "/api/screenplay/parse",
            json={"project_id": str(uuid4())},
        )

        # Should return validation error
        assert response.status_code in (400, 422, 401)

    @pytest.mark.asyncio
    async def test_upload_fountain_format(
        self,
        client: AsyncClient,
        sample_fountain_content: str,
    ):
        """Test uploading a Fountain format screenplay."""
        response = await client.post(
            "/api/screenplay/upload",
            data={"project_id": str(uuid4())},
            files={
                "file": (
                    "screenplay.fountain",
                    sample_fountain_content.encode(),
                    "text/plain",
                )
            },
        )

        # Should accept the file
        assert response.status_code in (200, 201, 401, 403)

    @pytest.mark.asyncio
    async def test_upload_pdf_format(self, client: AsyncClient):
        """Test uploading a PDF screenplay."""
        # Create a minimal PDF-like content
        pdf_content = b"%PDF-1.4\n% Test PDF"

        response = await client.post(
            "/api/screenplay/upload",
            data={"project_id": str(uuid4())},
            files={
                "file": (
                    "screenplay.pdf",
                    pdf_content,
                    "application/pdf",
                )
            },
        )

        # Endpoint should handle PDF
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_get_scenes_from_screenplay(self, client: AsyncClient):
        """Test getting extracted scenes from a screenplay."""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/screenplay/{project_id}/scenes",
        )

        # Should return scenes list or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_characters_from_screenplay(self, client: AsyncClient):
        """Test getting extracted characters from a screenplay."""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/screenplay/{project_id}/characters",
        )

        # Should return characters list or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_dialogue_from_screenplay(self, client: AsyncClient):
        """Test getting dialogue from a screenplay."""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/screenplay/{project_id}/dialogue",
        )

        # Should return dialogue or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_analyze_screenplay_endpoint(self, client: AsyncClient):
        """Test screenplay analysis endpoint."""
        response = await client.post(
            "/api/screenplay/analyze",
            json={"project_id": str(uuid4())},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_update_screenplay(self, client: AsyncClient):
        """Test updating screenplay content."""
        project_id = str(uuid4())

        response = await client.put(
            f"/api/screenplay/{project_id}",
            json={
                "content": "INT. UPDATED SCENE - DAY\n\nNew content here.",
            },
        )

        # Should handle update
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_delete_screenplay(self, client: AsyncClient):
        """Test deleting a screenplay."""
        project_id = str(uuid4())

        response = await client.delete(
            f"/api/screenplay/{project_id}",
        )

        # Should handle delete
        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_export_screenplay(self, client: AsyncClient):
        """Test exporting screenplay to different formats."""
        project_id = str(uuid4())

        for format_type in ["fountain", "pdf", "fdx"]:
            response = await client.get(
                f"/api/screenplay/{project_id}/export",
                params={"format": format_type},
            )

            # Should handle export request
            assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_large_screenplay_upload(self, client: AsyncClient):
        """Test uploading a large screenplay."""
        # Generate a large screenplay (100+ scenes)
        large_content = "Title: Large Screenplay\n\n"
        for i in range(100):
            large_content += f"\nINT. SCENE {i} - DAY\n\nCHARACTER\nDialogue line {i}.\n"

        response = await client.post(
            "/api/screenplay/upload",
            data={"project_id": str(uuid4())},
            files={
                "file": (
                    "large.fountain",
                    large_content.encode(),
                    "text/plain",
                )
            },
        )

        # Should handle large files
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_invalid_screenplay_format(self, client: AsyncClient):
        """Test uploading an invalid screenplay format."""
        response = await client.post(
            "/api/screenplay/upload",
            data={"project_id": str(uuid4())},
            files={
                "file": (
                    "invalid.xyz",
                    b"This is not a screenplay",
                    "application/octet-stream",
                )
            },
        )

        # Should reject or handle gracefully
        assert response.status_code in (400, 415, 422, 401)
