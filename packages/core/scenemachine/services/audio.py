"""Audio and Text-to-Speech service for voice generation."""

import asyncio
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.asset import Asset, AssetStatus, AssetType
from scenemachine.models.character import Character

logger = logging.getLogger(__name__)


class TTSProvider(str, Enum):
    """Supported TTS providers."""

    MOCK = "mock"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    AZURE = "azure"


class VoiceGender(str, Enum):
    """Voice gender options."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class Voice:
    """Voice configuration."""

    id: str
    name: str
    provider: TTSProvider
    gender: VoiceGender
    language: str = "en"
    accent: Optional[str] = None
    preview_url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TTSRequest:
    """Text-to-speech generation request."""

    text: str
    voice_id: str
    provider: TTSProvider = TTSProvider.MOCK
    speed: float = 1.0
    pitch: float = 1.0
    stability: float = 0.5  # For ElevenLabs
    similarity_boost: float = 0.75  # For ElevenLabs
    output_format: str = "mp3"


@dataclass
class TTSResult:
    """Text-to-speech generation result."""

    success: bool
    audio_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    cost_usd: Optional[float] = None


@dataclass
class AudioProgress:
    """Progress update for audio generation."""

    percent: float
    stage: str
    message: str


class TTSProviderBase(ABC):
    """Base class for TTS providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> TTSProvider:
        """Provider type enum."""
        pass

    @abstractmethod
    async def get_voices(self) -> List[Voice]:
        """Get available voices."""
        pass

    @abstractmethod
    async def generate(
        self,
        request: TTSRequest,
        progress_callback: Optional[Callable[[AudioProgress], Any]] = None,
    ) -> TTSResult:
        """Generate speech from text."""
        pass

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if provider is available."""
        pass


class MockTTSProvider(TTSProviderBase):
    """Mock TTS provider for testing."""

    @property
    def name(self) -> str:
        return "Mock TTS"

    @property
    def provider_type(self) -> TTSProvider:
        return TTSProvider.MOCK

    async def get_voices(self) -> List[Voice]:
        return [
            Voice(
                id="mock-male-1",
                name="James",
                provider=TTSProvider.MOCK,
                gender=VoiceGender.MALE,
                language="en",
                accent="American",
                description="Deep, professional male voice",
            ),
            Voice(
                id="mock-female-1",
                name="Emily",
                provider=TTSProvider.MOCK,
                gender=VoiceGender.FEMALE,
                language="en",
                accent="American",
                description="Warm, friendly female voice",
            ),
            Voice(
                id="mock-male-2",
                name="William",
                provider=TTSProvider.MOCK,
                gender=VoiceGender.MALE,
                language="en",
                accent="British",
                description="Distinguished British male voice",
            ),
            Voice(
                id="mock-female-2",
                name="Sophie",
                provider=TTSProvider.MOCK,
                gender=VoiceGender.FEMALE,
                language="en",
                accent="British",
                description="Elegant British female voice",
            ),
        ]

    async def generate(
        self,
        request: TTSRequest,
        progress_callback: Optional[Callable[[AudioProgress], Any]] = None,
    ) -> TTSResult:
        """Generate mock audio (creates a silent file)."""
        settings = get_settings()
        output_dir = settings.output_dir / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            await progress_callback(AudioProgress(
                percent=10,
                stage="preparing",
                message="Preparing audio generation...",
            ))

        # Simulate processing time
        await asyncio.sleep(0.5)

        if progress_callback:
            await progress_callback(AudioProgress(
                percent=50,
                stage="generating",
                message="Generating speech...",
            ))

        await asyncio.sleep(0.5)

        # Create a placeholder audio file path
        # In production, would generate actual audio
        output_path = output_dir / f"tts_{request.voice_id}_{hash(request.text) % 10000}.mp3"

        # For mock, just create an empty file or copy a sample
        output_path.touch()

        if progress_callback:
            await progress_callback(AudioProgress(
                percent=100,
                stage="complete",
                message="Audio generation complete",
            ))

        # Estimate duration based on text length (rough: 150 words per minute)
        words = len(request.text.split())
        duration = (words / 150) * 60 / request.speed

        return TTSResult(
            success=True,
            audio_path=str(output_path),
            duration_seconds=duration,
            cost_usd=0.0,
        )

    async def check_availability(self) -> bool:
        return True


class ElevenLabsProvider(TTSProviderBase):
    """Production-ready ElevenLabs TTS provider.

    Features:
    - Multiple model support (multilingual v2, turbo, flash)
    - Voice cloning support
    - Streaming audio generation
    - Accurate audio duration detection
    - Cost tracking
    """

    # Available TTS models
    MODELS = {
        "eleven_multilingual_v2": {
            "name": "Multilingual v2",
            "languages": 29,
            "quality": "high",
            "latency": "medium",
            "cost_per_char": 0.00030,
        },
        "eleven_turbo_v2_5": {
            "name": "Turbo v2.5",
            "languages": 32,
            "quality": "high",
            "latency": "low",
            "cost_per_char": 0.00015,
        },
        "eleven_flash_v2_5": {
            "name": "Flash v2.5",
            "languages": 32,
            "quality": "medium",
            "latency": "very_low",
            "cost_per_char": 0.000075,
        },
    }

    DEFAULT_MODEL = "eleven_multilingual_v2"

    def __init__(self, api_key: str, model_id: Optional[str] = None):
        self.api_key = api_key
        self.model_id = model_id or self.DEFAULT_MODEL
        self.base_url = "https://api.elevenlabs.io/v1"
        self._voices_cache: Optional[List[Voice]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 300  # 5 minutes

    @property
    def name(self) -> str:
        return "ElevenLabs"

    @property
    def provider_type(self) -> TTSProvider:
        return TTSProvider.ELEVENLABS

    def estimate_cost(self, text: str, model_id: Optional[str] = None) -> float:
        """Estimate generation cost in USD."""
        model = model_id or self.model_id
        cost_per_char = self.MODELS.get(model, {}).get("cost_per_char", 0.0003)
        return len(text) * cost_per_char

    async def get_voices(self, use_cache: bool = True) -> List[Voice]:
        """Fetch available voices from ElevenLabs with caching."""
        import time

        # Check cache
        if use_cache and self._voices_cache and self._cache_timestamp:
            if time.time() - self._cache_timestamp < self._cache_ttl:
                return self._voices_cache

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(f"Failed to fetch ElevenLabs voices: {response.status_code}")
                    return self._voices_cache or []

                data = response.json()
                voices = []

                for voice in data.get("voices", []):
                    labels = voice.get("labels", {})
                    gender_str = labels.get("gender", "neutral")
                    gender = VoiceGender.MALE if gender_str == "male" else (
                        VoiceGender.FEMALE if gender_str == "female" else VoiceGender.NEUTRAL
                    )

                    voices.append(Voice(
                        id=voice["voice_id"],
                        name=voice["name"],
                        provider=TTSProvider.ELEVENLABS,
                        gender=gender,
                        language=labels.get("language", "en"),
                        accent=labels.get("accent"),
                        preview_url=voice.get("preview_url"),
                        description=voice.get("description"),
                    ))

                # Update cache
                self._voices_cache = voices
                self._cache_timestamp = time.time()

                return voices

        except Exception as e:
            logger.error(f"Error fetching ElevenLabs voices: {e}")
            return self._voices_cache or []

    async def generate(
        self,
        request: TTSRequest,
        progress_callback: Optional[Callable[[AudioProgress], Any]] = None,
    ) -> TTSResult:
        """Generate speech using ElevenLabs API."""
        settings = get_settings()
        output_dir = settings.output_dir / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            await progress_callback(AudioProgress(
                percent=5,
                stage="preparing",
                message="Connecting to ElevenLabs...",
            ))

        try:
            # Determine model based on text length and request
            model_id = request.extra_params.get("model_id", self.model_id) if hasattr(request, "extra_params") else self.model_id

            # Use streaming for longer texts
            use_streaming = len(request.text) > 500

            async with httpx.AsyncClient() as client:
                if progress_callback:
                    await progress_callback(AudioProgress(
                        percent=10,
                        stage="generating",
                        message=f"Generating speech with {self.MODELS.get(model_id, {}).get('name', model_id)}...",
                    ))

                endpoint = f"{self.base_url}/text-to-speech/{request.voice_id}"
                if use_streaming:
                    endpoint += "/stream"

                payload = {
                    "text": request.text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": request.stability,
                        "similarity_boost": request.similarity_boost,
                        "style": getattr(request, "style", 0.0),
                        "use_speaker_boost": True,
                    },
                }

                # Add output format
                output_format = getattr(request, "output_format", "mp3_44100_128")
                params = {"output_format": output_format}

                response = await client.post(
                    endpoint,
                    headers={
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    params=params,
                    timeout=120.0,
                )

                if progress_callback:
                    await progress_callback(AudioProgress(
                        percent=60,
                        stage="processing",
                        message="Processing audio response...",
                    ))

                if response.status_code != 200:
                    error_msg = f"ElevenLabs API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", {}).get("message", error_msg)
                    except Exception:
                        pass
                    return TTSResult(success=False, error_message=error_msg)

                # Generate unique filename
                import hashlib
                text_hash = hashlib.md5(request.text.encode()).hexdigest()[:8]
                timestamp = int(asyncio.get_event_loop().time() * 1000) % 100000
                output_path = output_dir / f"elevenlabs_{request.voice_id}_{text_hash}_{timestamp}.mp3"

                # Save audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)

                if progress_callback:
                    await progress_callback(AudioProgress(
                        percent=85,
                        stage="finalizing",
                        message="Analyzing audio duration...",
                    ))

                # Get actual audio duration using ffprobe
                duration = await self._get_audio_duration(output_path)

                if progress_callback:
                    await progress_callback(AudioProgress(
                        percent=100,
                        stage="complete",
                        message="Audio generation complete",
                    ))

                # Calculate cost
                cost = self.estimate_cost(request.text, model_id)

                return TTSResult(
                    success=True,
                    audio_path=str(output_path),
                    duration_seconds=duration,
                    cost_usd=cost,
                )

        except httpx.TimeoutException:
            logger.error("ElevenLabs request timed out")
            return TTSResult(success=False, error_message="Request timed out")
        except Exception as e:
            logger.exception("ElevenLabs generation error")
            return TTSResult(success=False, error_message=str(e))

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                return float(stdout.decode().strip())
        except Exception as e:
            logger.warning(f"ffprobe duration detection failed: {e}")

        # Fallback: estimate from file size (rough: 16KB per second for mp3 128kbps)
        try:
            size_bytes = audio_path.stat().st_size
            return size_bytes / 16000
        except Exception:
            return 0.0

    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get user subscription and usage info."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user",
                    headers={"xi-api-key": self.api_key},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to get ElevenLabs user info: {e}")
        return None

    async def check_availability(self) -> bool:
        """Check if ElevenLabs API is accessible and has quota."""
        try:
            user_info = await self.get_user_info()
            if user_info:
                subscription = user_info.get("subscription", {})
                character_limit = subscription.get("character_limit", 0)
                character_count = subscription.get("character_count", 0)
                # Check if there's remaining quota
                return character_count < character_limit
            return False
        except Exception:
            return False

    @classmethod
    def list_models(cls) -> List[Dict[str, Any]]:
        """List available TTS models."""
        return [
            {"id": model_id, **info}
            for model_id, info in cls.MODELS.items()
        ]


class OpenAITTSProvider(TTSProviderBase):
    """OpenAI TTS provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    @property
    def name(self) -> str:
        return "OpenAI TTS"

    @property
    def provider_type(self) -> TTSProvider:
        return TTSProvider.OPENAI

    async def get_voices(self) -> List[Voice]:
        """Get available OpenAI TTS voices."""
        # OpenAI has fixed voices
        return [
            Voice(
                id="alloy",
                name="Alloy",
                provider=TTSProvider.OPENAI,
                gender=VoiceGender.NEUTRAL,
                language="en",
                description="Neutral, balanced voice",
            ),
            Voice(
                id="echo",
                name="Echo",
                provider=TTSProvider.OPENAI,
                gender=VoiceGender.MALE,
                language="en",
                description="Deep, authoritative voice",
            ),
            Voice(
                id="fable",
                name="Fable",
                provider=TTSProvider.OPENAI,
                gender=VoiceGender.NEUTRAL,
                language="en",
                description="Expressive, storytelling voice",
            ),
            Voice(
                id="onyx",
                name="Onyx",
                provider=TTSProvider.OPENAI,
                gender=VoiceGender.MALE,
                language="en",
                description="Deep, resonant voice",
            ),
            Voice(
                id="nova",
                name="Nova",
                provider=TTSProvider.OPENAI,
                gender=VoiceGender.FEMALE,
                language="en",
                description="Warm, engaging female voice",
            ),
            Voice(
                id="shimmer",
                name="Shimmer",
                provider=TTSProvider.OPENAI,
                gender=VoiceGender.FEMALE,
                language="en",
                description="Soft, pleasant female voice",
            ),
        ]

    async def generate(
        self,
        request: TTSRequest,
        progress_callback: Optional[Callable[[AudioProgress], Any]] = None,
    ) -> TTSResult:
        """Generate speech using OpenAI TTS API."""
        settings = get_settings()
        output_dir = settings.output_dir / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            await progress_callback(AudioProgress(
                percent=10,
                stage="preparing",
                message="Connecting to OpenAI...",
            ))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "tts-1-hd",
                        "input": request.text,
                        "voice": request.voice_id,
                        "speed": request.speed,
                    },
                    timeout=60.0,
                )

                if progress_callback:
                    await progress_callback(AudioProgress(
                        percent=70,
                        stage="processing",
                        message="Processing audio...",
                    ))

                if response.status_code != 200:
                    error_msg = f"OpenAI API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                    return TTSResult(success=False, error_message=error_msg)

                # Save audio file
                output_path = output_dir / f"openai_{request.voice_id}_{hash(request.text) % 10000}.mp3"
                with open(output_path, "wb") as f:
                    f.write(response.content)

                if progress_callback:
                    await progress_callback(AudioProgress(
                        percent=100,
                        stage="complete",
                        message="Audio generation complete",
                    ))

                # Estimate duration
                words = len(request.text.split())
                duration = (words / 150) * 60

                # Estimate cost ($0.015 per 1000 characters for tts-1-hd)
                cost = len(request.text) * 0.000015

                return TTSResult(
                    success=True,
                    audio_path=str(output_path),
                    duration_seconds=duration,
                    cost_usd=cost,
                )

        except Exception as e:
            logger.error(f"OpenAI TTS generation error: {e}")
            return TTSResult(success=False, error_message=str(e))

    async def check_availability(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False


class AudioService:
    """Service for managing audio generation and TTS."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._providers: Dict[TTSProvider, TTSProviderBase] = {
            TTSProvider.MOCK: MockTTSProvider(),
        }
        self._settings = get_settings()

    def register_provider(self, provider_type: TTSProvider, provider: TTSProviderBase) -> None:
        """Register a TTS provider."""
        self._providers[provider_type] = provider

    def get_provider(self, provider_type: TTSProvider) -> Optional[TTSProviderBase]:
        """Get a registered provider."""
        return self._providers.get(provider_type)

    async def initialize_providers(self) -> None:
        """Initialize providers from application settings."""
        # Register ElevenLabs if key available
        elevenlabs_key = self._settings.elevenlabs_api_key
        if elevenlabs_key:
            self.register_provider(
                TTSProvider.ELEVENLABS,
                ElevenLabsProvider(api_key=elevenlabs_key)
            )
            logger.info("Registered ElevenLabs TTS provider")

        # Register OpenAI TTS if key available
        openai_key = self._settings.openai_api_key
        if openai_key:
            self.register_provider(
                TTSProvider.OPENAI,
                OpenAITTSProvider(api_key=openai_key)
            )
            logger.info("Registered OpenAI TTS provider")

    async def get_available_voices(
        self,
        provider: Optional[TTSProvider] = None,
        gender: Optional[VoiceGender] = None,
        language: Optional[str] = None,
    ) -> List[Voice]:
        """Get available voices, optionally filtered."""
        voices = []

        providers_to_check = (
            [self._providers[provider]] if provider and provider in self._providers
            else self._providers.values()
        )

        for p in providers_to_check:
            try:
                provider_voices = await p.get_voices()
                voices.extend(provider_voices)
            except Exception as e:
                logger.warning(f"Failed to get voices from {p.name}: {e}")

        # Apply filters
        if gender:
            voices = [v for v in voices if v.gender == gender]
        if language:
            voices = [v for v in voices if v.language == language]

        return voices

    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        provider: TTSProvider = TTSProvider.MOCK,
        speed: float = 1.0,
        progress_callback: Optional[Callable[[AudioProgress], Any]] = None,
    ) -> TTSResult:
        """Generate speech from text."""
        provider_instance = self._providers.get(provider)
        if not provider_instance:
            return TTSResult(
                success=False,
                error_message=f"Provider {provider.value} not available",
            )

        request = TTSRequest(
            text=text,
            voice_id=voice_id,
            provider=provider,
            speed=speed,
        )

        return await provider_instance.generate(request, progress_callback)

    async def generate_dialogue(
        self,
        shot_id: UUID,
        progress_callback: Optional[Callable[[AudioProgress], Any]] = None,
    ) -> TTSResult:
        """Generate dialogue audio for a shot."""
        from scenemachine.models.shot import Shot

        # Get shot and its dialogue
        stmt = select(Shot).where(Shot.id == shot_id)
        result = await self._session.execute(stmt)
        shot = result.scalar_one_or_none()

        if not shot:
            return TTSResult(success=False, error_message="Shot not found")

        if not shot.dialogue:
            return TTSResult(success=False, error_message="Shot has no dialogue")

        # Get character voice settings if available
        voice_id = "mock-male-1"  # Default
        provider = TTSProvider.MOCK

        # Try to get character-specific voice
        if shot.scene:
            # Could look up character voice assignments
            pass

        return await self.generate_speech(
            text=shot.dialogue,
            voice_id=voice_id,
            provider=provider,
            progress_callback=progress_callback,
        )

    async def assign_voice_to_character(
        self,
        character_id: UUID,
        voice_id: str,
        provider: TTSProvider,
    ) -> bool:
        """Assign a voice to a character."""
        stmt = select(Character).where(Character.id == character_id)
        result = await self._session.execute(stmt)
        character = result.scalar_one_or_none()

        if not character:
            return False

        # Store voice assignment in character's additional data
        if not character.generation_settings:
            character.generation_settings = {}

        character.generation_settings["voice"] = {
            "id": voice_id,
            "provider": provider.value,
        }

        await self._session.commit()
        return True

    async def get_character_voice(
        self,
        character_id: UUID,
    ) -> Optional[Dict[str, str]]:
        """Get voice assignment for a character."""
        stmt = select(Character).where(Character.id == character_id)
        result = await self._session.execute(stmt)
        character = result.scalar_one_or_none()

        if not character or not character.generation_settings:
            return None

        return character.generation_settings.get("voice")

    async def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available TTS providers with status."""
        providers = []

        for provider_type, provider in self._providers.items():
            available = await provider.check_availability()
            providers.append({
                "provider": provider_type.value,
                "name": provider.name,
                "available": available,
            })

        return providers
