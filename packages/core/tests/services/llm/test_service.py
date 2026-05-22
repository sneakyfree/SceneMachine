"""Tests for LLM service."""

import pytest

from scenemachine.services.llm.service import (
    LLMProvider,
    LLMResponse,
    LLMService,
    MockBackend,
    get_llm_service,
    reset_llm_service,
)


class TestLLMResponse:
    """Tests for LLMResponse parsing."""

    def test_parse_json_simple(self):
        """Should parse simple JSON."""
        response = LLMResponse(
            content='{"key": "value"}',
            model="test",
            provider=LLMProvider.MOCK,
        )
        parsed = response.parse_json()
        assert parsed == {"key": "value"}

    def test_parse_json_array(self):
        """Should parse JSON array."""
        response = LLMResponse(
            content='[{"id": 1}, {"id": 2}]',
            model="test",
            provider=LLMProvider.MOCK,
        )
        parsed = response.parse_json()
        assert parsed == [{"id": 1}, {"id": 2}]

    def test_parse_json_with_markdown(self):
        """Should extract JSON from markdown code block."""
        response = LLMResponse(
            content='Here is the result:\n```json\n{"score": 0.85}\n```',
            model="test",
            provider=LLMProvider.MOCK,
        )
        parsed = response.parse_json()
        assert parsed == {"score": 0.85}

    def test_parse_json_with_text_prefix(self):
        """Should find JSON after text."""
        response = LLMResponse(
            content='Based on my analysis: {"result": "success"}',
            model="test",
            provider=LLMProvider.MOCK,
        )
        parsed = response.parse_json()
        assert parsed == {"result": "success"}

    def test_parse_json_invalid(self):
        """Should return None for invalid JSON."""
        response = LLMResponse(
            content="This is just plain text",
            model="test",
            provider=LLMProvider.MOCK,
        )
        parsed = response.parse_json()
        assert parsed is None


class TestMockBackend:
    """Tests for mock backend."""

    @pytest.mark.asyncio
    async def test_custom_response(self):
        """Should return custom responses for matching keys."""
        backend = MockBackend(responses={
            "hello": '{"greeting": "Hi there!"}'
        })

        response = await backend.complete(
            messages=[{"role": "user", "content": "hello world"}]
        )

        assert response.provider == LLMProvider.MOCK
        parsed = response.parse_json()
        assert parsed == {"greeting": "Hi there!"}

    @pytest.mark.asyncio
    async def test_analysis_response(self):
        """Should return analysis response for analyze queries."""
        backend = MockBackend()

        response = await backend.complete(
            messages=[{"role": "user", "content": "analyze this project"}]
        )

        parsed = response.parse_json()
        assert "overallScore" in parsed
        assert "pacing" in parsed

    @pytest.mark.asyncio
    async def test_scene_suggestion_response(self):
        """Should return scene suggestions."""
        backend = MockBackend()

        response = await backend.complete(
            messages=[{"role": "user", "content": "suggest improvements for scene"}]
        )

        parsed = response.parse_json()
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert "id" in parsed[0]

    @pytest.mark.asyncio
    async def test_shot_suggestion_response(self):
        """Should return shot suggestions."""
        backend = MockBackend()

        response = await backend.complete(
            messages=[{"role": "user", "content": "suggest improvements for shot"}]
        )

        parsed = response.parse_json()
        assert isinstance(parsed, list)

    @pytest.mark.asyncio
    async def test_enhance_prompt_response(self):
        """Should return enhanced prompt."""
        backend = MockBackend()

        response = await backend.complete(
            messages=[{"role": "user", "content": "enhance this prompt"}]
        )

        # Should be plain text, not JSON
        assert "cinematic" in response.content.lower()

    @pytest.mark.asyncio
    async def test_call_history(self):
        """Should track call history."""
        backend = MockBackend()

        await backend.complete(
            messages=[{"role": "user", "content": "test 1"}]
        )
        await backend.complete(
            messages=[{"role": "user", "content": "test 2"}]
        )

        assert len(backend.call_history) == 2


class TestLLMService:
    """Tests for LLM service."""

    @pytest.mark.asyncio
    async def test_chat(self):
        """Should handle chat interaction."""
        service = LLMService(primary_provider=LLMProvider.MOCK)

        result = await service.chat(
            message="How can I improve this scene?",
            project_context={"project_name": "Test Project"},
        )

        assert "message" in result
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)

    @pytest.mark.asyncio
    async def test_analyze_project(self):
        """Should analyze project."""
        service = LLMService(primary_provider=LLMProvider.MOCK)

        result = await service.analyze_project(
            project_context={"id": "proj_123", "name": "Test"},
            scenes=[{"heading": "INT. OFFICE - DAY"}],
            characters=[{"name": "John"}],
        )

        assert "overallScore" in result
        assert "pacing" in result
        assert "characterDevelopment" in result
        assert "generatedAt" in result

    @pytest.mark.asyncio
    async def test_suggest_scene(self):
        """Should suggest scene improvements."""
        service = LLMService(primary_provider=LLMProvider.MOCK)

        result = await service.suggest_scene(
            scene={"heading": "INT. OFFICE - DAY", "description": "A meeting"},
            characters=[{"name": "John"}],
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_suggest_shot(self):
        """Should suggest shot improvements."""
        service = LLMService(primary_provider=LLMProvider.MOCK)

        result = await service.suggest_shot(
            shot={"shot_type": "MEDIUM", "description": "Character enters"},
            scene_context={"heading": "INT. OFFICE - DAY"},
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_enhance_prompt(self):
        """Should enhance video generation prompt."""
        service = LLMService(primary_provider=LLMProvider.MOCK)

        result = await service.enhance_prompt(
            original_prompt="A person walking",
            shot_context={"shot_type": "WIDE", "mood": "dramatic"},
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_shot_breakdown(self):
        """Should generate shot breakdown."""
        service = LLMService(primary_provider=LLMProvider.MOCK)

        result = await service.generate_shot_breakdown(
            scene={"heading": "INT. OFFICE - DAY", "content": "John enters the room."},
            characters=[{"name": "John"}],
        )

        assert "shots" in result
        assert isinstance(result["shots"], list)


class TestGetLLMService:
    """Tests for get_llm_service function."""

    def test_singleton_pattern(self):
        """Should return same instance."""
        reset_llm_service()

        service1 = get_llm_service()
        service2 = get_llm_service()

        assert service1 is service2

        reset_llm_service()

    def test_default_to_mock(self):
        """Should default to mock when no API keys."""
        import os

        # Ensure no API keys
        anthropic_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        openai_key = os.environ.pop("OPENAI_API_KEY", None)

        try:
            reset_llm_service()
            service = get_llm_service()

            assert service.primary_provider == LLMProvider.MOCK
        finally:
            # Restore keys if they existed
            if anthropic_key:
                os.environ["ANTHROPIC_API_KEY"] = anthropic_key
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
            reset_llm_service()


class TestLLMServiceFallback:
    """Tests for provider fallback."""

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Should fall back to secondary provider on failure."""
        # Create a failing backend
        class FailingBackend:
            async def complete(self, *args, **kwargs):
                raise Exception("Primary failed")

        service = LLMService(
            primary_provider=LLMProvider.ANTHROPIC,
            fallback_provider=LLMProvider.MOCK,
        )

        # Replace Anthropic backend with failing one
        service._backends[LLMProvider.ANTHROPIC] = FailingBackend()

        # Should fall back to mock
        result = await service.chat(
            message="Test",
            project_context={},
        )

        assert "message" in result
