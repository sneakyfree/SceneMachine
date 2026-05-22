"""Tests for AudioService and TTS providers."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Character, Project
from scenemachine.models.character import CharacterGender
from scenemachine.services.audio import (
    AudioProgress,
    AudioService,
    ElevenLabsProvider,
    MockTTSProvider,
    OpenAITTSProvider,
    TTSProvider,
    TTSRequest,
    TTSResult,
    Voice,
    VoiceGender,
)


class TestVoiceDataclass:
    """Test suite for Voice dataclass."""

    def test_voice_creation(self):
        """Test creating a Voice."""
        voice = Voice(
            id="test-voice-123",
            name="Test Voice",
            provider=TTSProvider.ELEVENLABS,
            gender=VoiceGender.MALE,
            language="en",
            accent="American",
            description="A test voice",
        )
        assert voice.id == "test-voice-123"
        assert voice.gender == VoiceGender.MALE
        assert voice.accent == "American"

    def test_voice_defaults(self):
        """Test Voice default values."""
        voice = Voice(
            id="test",
            name="Test",
            provider=TTSProvider.MOCK,
            gender=VoiceGender.NEUTRAL,
        )
        assert voice.language == "en"
        assert voice.accent is None
        assert voice.preview_url is None


class TestTTSRequest:
    """Test suite for TTSRequest dataclass."""

    def test_request_creation(self):
        """Test creating a TTSRequest."""
        request = TTSRequest(
            text="Hello, world!",
            voice_id="voice-123",
            provider=TTSProvider.ELEVENLABS,
            speed=1.2,
        )
        assert request.text == "Hello, world!"
        assert request.speed == 1.2

    def test_request_defaults(self):
        """Test TTSRequest default values."""
        request = TTSRequest(
            text="Test",
            voice_id="voice-123",
        )
        assert request.provider == TTSProvider.MOCK
        assert request.speed == 1.0
        assert request.stability == 0.5
        assert request.similarity_boost == 0.75
        assert request.output_format == "mp3"


class TestTTSResult:
    """Test suite for TTSResult dataclass."""

    def test_successful_result(self):
        """Test successful TTS result."""
        result = TTSResult(
            success=True,
            audio_path="/path/to/audio.mp3",
            duration_seconds=5.5,
            cost_usd=0.01,
        )
        assert result.success is True
        assert result.duration_seconds == 5.5

    def test_failed_result(self):
        """Test failed TTS result."""
        result = TTSResult(
            success=False,
            error_message="API error",
        )
        assert result.success is False
        assert result.error_message == "API error"


class TestMockTTSProvider:
    """Test suite for MockTTSProvider."""

    @pytest.fixture
    def mock_provider(self):
        return MockTTSProvider()

    async def test_provider_properties(self, mock_provider):
        """Test provider name and type."""
        assert mock_provider.name == "Mock TTS"
        assert mock_provider.provider_type == TTSProvider.MOCK

    async def test_check_availability(self, mock_provider):
        """Test availability always returns True."""
        assert await mock_provider.check_availability() is True

    async def test_get_voices(self, mock_provider):
        """Test getting available voices."""
        voices = await mock_provider.get_voices()

        assert len(voices) == 4
        voice_names = [v.name for v in voices]
        assert "James" in voice_names
        assert "Emily" in voice_names

    async def test_generate(self, mock_provider, tmp_path):
        """Test mock audio generation."""
        with patch("scenemachine.services.audio.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            request = TTSRequest(
                text="Hello, this is a test message.",
                voice_id="mock-male-1",
            )

            result = await mock_provider.generate(request)

            assert result.success is True
            assert result.audio_path is not None
            assert result.duration_seconds > 0
            assert result.cost_usd == 0.0

    async def test_generate_with_progress(self, mock_provider, tmp_path):
        """Test generation with progress callback."""
        with patch("scenemachine.services.audio.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            progress_updates = []

            async def progress_callback(progress: AudioProgress):
                progress_updates.append(progress)

            request = TTSRequest(
                text="Test message",
                voice_id="mock-female-1",
            )

            await mock_provider.generate(request, progress_callback)

            assert len(progress_updates) >= 2
            assert progress_updates[-1].percent == 100
            assert progress_updates[-1].stage == "complete"


class TestElevenLabsProvider:
    """Test suite for ElevenLabsProvider."""

    def test_available_models(self):
        """Test that models are defined."""
        assert "eleven_multilingual_v2" in ElevenLabsProvider.MODELS
        assert "eleven_turbo_v2_5" in ElevenLabsProvider.MODELS
        assert "eleven_flash_v2_5" in ElevenLabsProvider.MODELS

    def test_list_models(self):
        """Test listing available models."""
        models = ElevenLabsProvider.list_models()
        assert len(models) == 3
        for model in models:
            assert "id" in model
            assert "name" in model
            assert "cost_per_char" in model

    def test_estimate_cost(self):
        """Test cost estimation."""
        provider = ElevenLabsProvider(api_key="test-key")

        # 1000 characters at default model ($0.0003/char) = $0.30
        cost = provider.estimate_cost("x" * 1000)
        assert cost == 0.30

    def test_provider_properties(self):
        """Test provider name and type."""
        provider = ElevenLabsProvider(api_key="test-key")
        assert provider.name == "ElevenLabs"
        assert provider.provider_type == TTSProvider.ELEVENLABS

    async def test_get_voices_caching(self):
        """Test voice caching behavior."""
        provider = ElevenLabsProvider(api_key="test-key")

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "voices": [
                {
                    "voice_id": "voice1",
                    "name": "Test Voice",
                    "labels": {"gender": "male", "language": "en"},
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # First call should fetch
            voices1 = await provider.get_voices()
            assert len(voices1) == 1

            # Second call should use cache
            voices2 = await provider.get_voices()
            assert len(voices2) == 1

            # Verify only one HTTP call was made
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 1

    async def test_generate_without_api_key(self):
        """Test that generation fails gracefully without valid setup."""
        provider = ElevenLabsProvider(api_key="invalid-key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": {"message": "Invalid API key"}}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            request = TTSRequest(
                text="Test",
                voice_id="voice-123",
                provider=TTSProvider.ELEVENLABS,
            )

            with patch("scenemachine.services.audio.get_settings") as mock_settings:
                mock_settings.return_value.output_dir = Path("/tmp")

                result = await provider.generate(request)

            assert result.success is False
            assert "401" in result.error_message or "Invalid" in result.error_message


class TestOpenAITTSProvider:
    """Test suite for OpenAITTSProvider."""

    @pytest.fixture
    def openai_provider(self):
        return OpenAITTSProvider(api_key="test-key")

    async def test_provider_properties(self, openai_provider):
        """Test provider name and type."""
        assert openai_provider.name == "OpenAI TTS"
        assert openai_provider.provider_type == TTSProvider.OPENAI

    async def test_get_voices(self, openai_provider):
        """Test getting available voices."""
        voices = await openai_provider.get_voices()

        assert len(voices) == 6
        voice_names = [v.name for v in voices]
        assert "Alloy" in voice_names
        assert "Nova" in voice_names
        assert "Shimmer" in voice_names

    async def test_voice_genders(self, openai_provider):
        """Test voice gender assignments."""
        voices = await openai_provider.get_voices()

        male_voices = [v for v in voices if v.gender == VoiceGender.MALE]
        female_voices = [v for v in voices if v.gender == VoiceGender.FEMALE]
        neutral_voices = [v for v in voices if v.gender == VoiceGender.NEUTRAL]

        assert len(male_voices) >= 1
        assert len(female_voices) >= 1
        assert len(neutral_voices) >= 1


@pytest_asyncio.fixture
async def sample_character(db_session: AsyncSession, sample_project: Project) -> Character:
    """Create a sample character for testing."""
    character = Character(
        project_id=sample_project.id,
        name="JOHN",
        dialogue_count=10,
        scene_count=5,
        gender=CharacterGender.MALE,
    )
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    return character


class TestAudioService:
    """Test suite for AudioService."""

    @pytest_asyncio.fixture
    async def audio_service(self, db_session: AsyncSession) -> AudioService:
        """Create AudioService instance."""
        return AudioService(db_session)

    async def test_service_initialization(self, audio_service):
        """Test service initializes with mock provider."""
        assert TTSProvider.MOCK in audio_service._providers
        mock_provider = audio_service.get_provider(TTSProvider.MOCK)
        assert isinstance(mock_provider, MockTTSProvider)

    async def test_register_provider(self, audio_service):
        """Test registering a custom provider."""
        custom_provider = MockTTSProvider()
        audio_service.register_provider(TTSProvider.MOCK, custom_provider)

        retrieved = audio_service.get_provider(TTSProvider.MOCK)
        assert retrieved is custom_provider

    async def test_get_available_voices(self, audio_service):
        """Test getting available voices."""
        voices = await audio_service.get_available_voices()

        assert len(voices) > 0
        assert all(isinstance(v, Voice) for v in voices)

    async def test_get_voices_filtered_by_gender(self, audio_service):
        """Test filtering voices by gender."""
        male_voices = await audio_service.get_available_voices(gender=VoiceGender.MALE)
        female_voices = await audio_service.get_available_voices(gender=VoiceGender.FEMALE)

        assert all(v.gender == VoiceGender.MALE for v in male_voices)
        assert all(v.gender == VoiceGender.FEMALE for v in female_voices)

    async def test_generate_speech(self, audio_service, tmp_path):
        """Test speech generation."""
        with patch("scenemachine.services.audio.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            result = await audio_service.generate_speech(
                text="Hello, world!",
                voice_id="mock-male-1",
                provider=TTSProvider.MOCK,
            )

            assert result.success is True
            assert result.audio_path is not None

    async def test_generate_speech_invalid_provider(self, audio_service):
        """Test speech generation with unavailable provider."""
        result = await audio_service.generate_speech(
            text="Test",
            voice_id="voice-123",
            provider=TTSProvider.ELEVENLABS,  # Not registered
        )

        assert result.success is False
        assert "not available" in result.error_message

    async def test_assign_voice_to_character(
        self,
        audio_service: AudioService,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test assigning a voice to a character."""
        success = await audio_service.assign_voice_to_character(
            character_id=sample_character.id,
            voice_id="mock-male-1",
            provider=TTSProvider.MOCK,
        )

        assert success is True

        # Verify assignment
        await db_session.refresh(sample_character)
        voice_settings = sample_character.generation_settings.get("voice")
        assert voice_settings is not None
        assert voice_settings["id"] == "mock-male-1"
        assert voice_settings["provider"] == "mock"

    async def test_get_character_voice(
        self,
        audio_service: AudioService,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test getting voice assignment for a character."""
        # Assign voice first
        sample_character.generation_settings = {
            "voice": {"id": "test-voice", "provider": "elevenlabs"}
        }
        await db_session.commit()

        voice = await audio_service.get_character_voice(sample_character.id)

        assert voice is not None
        assert voice["id"] == "test-voice"
        assert voice["provider"] == "elevenlabs"

    async def test_get_character_voice_not_assigned(
        self,
        audio_service: AudioService,
        sample_character: Character,
    ):
        """Test getting voice for character without assignment."""
        voice = await audio_service.get_character_voice(sample_character.id)
        assert voice is None

    async def test_get_available_providers(self, audio_service):
        """Test getting list of available providers."""
        providers = await audio_service.get_available_providers()

        assert len(providers) >= 1
        mock_provider = next((p for p in providers if p["provider"] == "mock"), None)
        assert mock_provider is not None
        assert mock_provider["available"] is True


class TestAudioDurationEstimation:
    """Test suite for audio duration estimation."""

    async def test_mock_duration_estimation(self, tmp_path):
        """Test mock provider duration estimation."""
        with patch("scenemachine.services.audio.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            provider = MockTTSProvider()

            # Short text
            request = TTSRequest(text="Hello", voice_id="mock-male-1")
            result = await provider.generate(request)
            short_duration = result.duration_seconds

            # Longer text
            request = TTSRequest(
                text="This is a much longer sentence with many more words to speak.",
                voice_id="mock-male-1",
            )
            result = await provider.generate(request)
            long_duration = result.duration_seconds

            assert long_duration > short_duration

    async def test_duration_with_speed_adjustment(self, tmp_path):
        """Test duration accounts for speed adjustment."""
        with patch("scenemachine.services.audio.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            provider = MockTTSProvider()
            text = "This is a test message for duration calculation."

            # Normal speed
            request = TTSRequest(text=text, voice_id="mock-male-1", speed=1.0)
            result = await provider.generate(request)
            normal_duration = result.duration_seconds

            # Faster speed
            request = TTSRequest(text=text, voice_id="mock-male-1", speed=2.0)
            result = await provider.generate(request)
            fast_duration = result.duration_seconds

            # Faster speed should result in shorter duration
            assert fast_duration < normal_duration
