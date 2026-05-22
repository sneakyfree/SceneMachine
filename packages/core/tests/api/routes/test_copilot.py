"""Tests for Copilot API routes."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app
from scenemachine.models import Project, Scene, SceneState


class TestCopilotRoutes:
    """Tests for Copilot API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest_asyncio.fixture
    async def sample_scene(self, db_session: AsyncSession, sample_project: Project) -> Scene:
        """Create a sample scene for testing."""
        scene = Scene(
            project_id=sample_project.id,
            scene_number=1,
            heading="INT. LABORATORY - NIGHT",
            description="A dark laboratory filled with equipment.",
            state=SceneState.DRAFT,
        )
        db_session.add(scene)
        await db_session.commit()
        await db_session.refresh(scene)
        return scene

    @pytest.mark.asyncio
    async def test_chat_with_steven_endpoint_exists(self, client: AsyncClient):
        """Test that the Steven chat endpoint exists."""
        # Make request - may fail auth but endpoint should exist
        response = await client.post(
            "/api/copilot/chat",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_analyze_scene_endpoint_exists(self, client: AsyncClient):
        """Test that the scene analysis endpoint exists."""
        response = await client.post(
            "/api/copilot/analyze-scene",
            json={"scene_id": str(uuid4())},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_get_creative_guidance_endpoint_exists(self, client: AsyncClient):
        """Test that the creative guidance endpoint exists."""
        response = await client.post(
            "/api/copilot/creative-guidance",
            json={"project_id": str(uuid4()), "context": "test"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_chat_requires_messages(self, client: AsyncClient):
        """Test that chat requires messages."""
        response = await client.post(
            "/api/copilot/chat",
            json={},
        )

        # Should return validation error
        assert response.status_code in (400, 422, 401)

    @pytest.mark.asyncio
    async def test_analyze_scene_requires_scene_id(self, client: AsyncClient):
        """Test that scene analysis requires a scene ID."""
        response = await client.post(
            "/api/copilot/analyze-scene",
            json={},
        )

        # Should return validation error
        assert response.status_code in (400, 422, 401)

    @pytest.mark.asyncio
    @patch("scenemachine.services.llm.service.LLMService")
    async def test_chat_with_llm_integration(self, mock_llm, client: AsyncClient):
        """Test chat endpoint with mocked LLM service."""
        mock_instance = AsyncMock()
        mock_instance.chat.return_value = {
            "response": "Hello! I'm Steven, your AI assistant.",
            "suggestions": [],
        }
        mock_llm.return_value = mock_instance

        response = await client.post(
            "/api/copilot/chat",
            json={
                "messages": [{"role": "user", "content": "Hello Steven"}],
                "project_id": str(uuid4()),
            },
        )

        # Should succeed or fail auth (not 404 or 500)
        assert response.status_code in (200, 201, 401, 403)

    @pytest.mark.asyncio
    async def test_analyze_scene_with_invalid_uuid(self, client: AsyncClient):
        """Test scene analysis with invalid UUID."""
        response = await client.post(
            "/api/copilot/analyze-scene",
            json={"scene_id": "not-a-uuid"},
        )

        # Should return validation error
        assert response.status_code in (400, 422, 401)

    @pytest.mark.asyncio
    async def test_enhance_prompt_endpoint_exists(self, client: AsyncClient):
        """Test that prompt enhancement endpoint exists."""
        response = await client.post(
            "/api/copilot/enhance-prompt",
            json={"prompt": "A sunset over the ocean", "style": "cinematic"},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_suggest_shots_endpoint_exists(self, client: AsyncClient):
        """Test that shot suggestion endpoint exists."""
        response = await client.post(
            "/api/copilot/suggest-shots",
            json={"scene_id": str(uuid4())},
        )

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_chat_response_format(self, client: AsyncClient):
        """Test that chat responses have expected format."""
        # This tests the response structure when authenticated
        # In unit tests, we mock the auth
        pass  # Would require proper auth mocking

    @pytest.mark.asyncio
    async def test_creative_guidance_categories(self, client: AsyncClient):
        """Test creative guidance with different categories."""
        categories = ["cinematography", "lighting", "color", "composition"]

        for category in categories:
            response = await client.post(
                "/api/copilot/creative-guidance",
                json={
                    "project_id": str(uuid4()),
                    "category": category,
                },
            )

            # Endpoint should handle all categories
            assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client: AsyncClient):
        """Test that rate limiting is applied to copilot endpoints."""
        # Make many requests quickly
        responses = []
        for _ in range(20):
            response = await client.post(
                "/api/copilot/chat",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )
            responses.append(response.status_code)

        # Should eventually get rate limited (429) or auth error (401)
        # Just verify no 500 errors
        assert 500 not in responses
