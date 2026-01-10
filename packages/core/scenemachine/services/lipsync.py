"""Lip Sync Service for audio-driven facial animation.

Provides audio-to-lip-sync functionality using multiple providers:
- Rhubarb Lip Sync (local, open-source)
- Wav2Lip (AI-based)
- SadTalker (AI-based talking head)
- LatentSync (coming soon)

The service analyzes audio to generate phoneme timing data
and can apply lip-sync to video files.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from scenemachine.config import get_settings

logger = logging.getLogger(__name__)


class LipSyncProvider(str, Enum):
    """Supported lip sync providers."""

    MOCK = "mock"
    RHUBARB = "rhubarb"
    WAV2LIP = "wav2lip"
    SADTALKER = "sadtalker"


class Phoneme(str, Enum):
    """Universal phoneme set based on Preston Blair shapes."""

    # Preston Blair mouth shapes
    A = "A"  # Jaw drop - ah, aw
    B = "B"  # Closed - m, b, p
    C = "C"  # Tight O - oo, oh
    D = "D"  # Wide O - r, er
    E = "E"  # Bite - ch, j, sh
    F = "F"  # Lip curl - f, v
    G = "G"  # Tongue - l, th, d
    H = "H"  # Wide - ee, i
    X = "X"  # Rest position (silence)


@dataclass
class PhonemeEvent:
    """A single phoneme event with timing."""

    phoneme: Phoneme
    start_time: float  # seconds
    end_time: float  # seconds

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phoneme": self.phoneme.value,
            "start": round(self.start_time, 3),
            "end": round(self.end_time, 3),
            "duration": round(self.duration, 3),
        }


@dataclass
class LipSyncData:
    """Complete lip sync data for an audio clip."""

    audio_path: str
    duration_seconds: float
    phonemes: List[PhonemeEvent] = field(default_factory=list)
    sample_rate: int = 44100
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio_path": self.audio_path,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "phoneme_count": len(self.phonemes),
            "phonemes": [p.to_dict() for p in self.phonemes],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LipSyncData":
        phonemes = [
            PhonemeEvent(
                phoneme=Phoneme(p["phoneme"]),
                start_time=p["start"],
                end_time=p["end"],
            )
            for p in data.get("phonemes", [])
        ]
        return cls(
            audio_path=data["audio_path"],
            duration_seconds=data["duration_seconds"],
            phonemes=phonemes,
            sample_rate=data.get("sample_rate", 44100),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LipSyncResult:
    """Result of lip sync processing."""

    success: bool
    lip_sync_data: Optional[LipSyncData] = None
    output_video_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_seconds: float = 0.0


@dataclass
class LipSyncProgress:
    """Progress update for lip sync processing."""

    percent: float
    stage: str
    message: str


class LipSyncProviderBase(ABC):
    """Base class for lip sync providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> LipSyncProvider:
        """Provider type enum."""
        pass

    @abstractmethod
    async def analyze_audio(
        self,
        audio_path: str,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Analyze audio and extract phoneme timing."""
        pass

    @abstractmethod
    async def apply_to_video(
        self,
        video_path: str,
        lip_sync_data: LipSyncData,
        output_path: str,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Apply lip sync to a video file."""
        pass

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if provider is available."""
        pass


class MockLipSyncProvider(LipSyncProviderBase):
    """Mock lip sync provider for testing."""

    @property
    def name(self) -> str:
        return "Mock Lip Sync"

    @property
    def provider_type(self) -> LipSyncProvider:
        return LipSyncProvider.MOCK

    async def analyze_audio(
        self,
        audio_path: str,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Generate mock phoneme data."""
        import time
        start_time = time.time()

        if progress_callback:
            await progress_callback(LipSyncProgress(
                percent=10,
                stage="analyzing",
                message="Analyzing audio file...",
            ))

        # Simulate processing
        await asyncio.sleep(0.3)

        if progress_callback:
            await progress_callback(LipSyncProgress(
                percent=50,
                stage="extracting",
                message="Extracting phonemes...",
            ))

        await asyncio.sleep(0.2)

        # Generate mock phoneme sequence
        # In reality, this would come from audio analysis
        duration = 3.0  # Mock duration
        phonemes = self._generate_mock_phonemes(duration)

        if progress_callback:
            await progress_callback(LipSyncProgress(
                percent=100,
                stage="complete",
                message="Analysis complete",
            ))

        lip_sync_data = LipSyncData(
            audio_path=audio_path,
            duration_seconds=duration,
            phonemes=phonemes,
            metadata={"provider": "mock"},
        )

        return LipSyncResult(
            success=True,
            lip_sync_data=lip_sync_data,
            processing_time_seconds=time.time() - start_time,
        )

    def _generate_mock_phonemes(self, duration: float) -> List[PhonemeEvent]:
        """Generate a mock phoneme sequence."""
        phonemes = []
        current_time = 0.0
        phoneme_list = list(Phoneme)

        while current_time < duration:
            # Random phoneme duration 0.05-0.15 seconds
            import random
            phoneme_duration = random.uniform(0.05, 0.15)
            end_time = min(current_time + phoneme_duration, duration)

            phonemes.append(PhonemeEvent(
                phoneme=random.choice(phoneme_list),
                start_time=current_time,
                end_time=end_time,
            ))

            current_time = end_time

        return phonemes

    async def apply_to_video(
        self,
        video_path: str,
        lip_sync_data: LipSyncData,
        output_path: str,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Mock lip sync application (copies input to output)."""
        import shutil
        import time

        start_time = time.time()

        if progress_callback:
            await progress_callback(LipSyncProgress(
                percent=50,
                stage="applying",
                message="Applying lip sync to video...",
            ))

        await asyncio.sleep(0.5)

        # Mock: just copy the input video
        shutil.copy(video_path, output_path)

        if progress_callback:
            await progress_callback(LipSyncProgress(
                percent=100,
                stage="complete",
                message="Lip sync applied",
            ))

        return LipSyncResult(
            success=True,
            lip_sync_data=lip_sync_data,
            output_video_path=output_path,
            processing_time_seconds=time.time() - start_time,
        )

    async def check_availability(self) -> bool:
        return True


class RhubarbLipSyncProvider(LipSyncProviderBase):
    """Rhubarb Lip Sync provider.

    Uses the open-source Rhubarb Lip Sync tool for
    audio analysis and phoneme extraction.

    https://github.com/DanielSWolf/rhubarb-lip-sync
    """

    def __init__(self, executable_path: Optional[str] = None):
        self.executable_path = executable_path or "rhubarb"

    @property
    def name(self) -> str:
        return "Rhubarb Lip Sync"

    @property
    def provider_type(self) -> LipSyncProvider:
        return LipSyncProvider.RHUBARB

    async def analyze_audio(
        self,
        audio_path: str,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Analyze audio using Rhubarb."""
        import time
        start_time = time.time()

        if progress_callback:
            await progress_callback(LipSyncProgress(
                percent=10,
                stage="preparing",
                message="Preparing audio for analysis...",
            ))

        try:
            # Run Rhubarb
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                output_json = f.name

            cmd = [
                self.executable_path,
                "-f", "json",
                "-o", output_json,
                "--machineReadable",
                audio_path,
            ]

            if progress_callback:
                await progress_callback(LipSyncProgress(
                    percent=20,
                    stage="analyzing",
                    message="Running Rhubarb analysis...",
                ))

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Rhubarb analysis failed"
                return LipSyncResult(success=False, error_message=error_msg)

            if progress_callback:
                await progress_callback(LipSyncProgress(
                    percent=80,
                    stage="parsing",
                    message="Parsing phoneme data...",
                ))

            # Parse Rhubarb output
            with open(output_json, "r") as f:
                rhubarb_data = json.load(f)

            # Convert to our format
            phonemes = []
            mouth_cues = rhubarb_data.get("mouthCues", [])

            for i, cue in enumerate(mouth_cues):
                start = cue["start"]
                end = cue["end"]
                shape = cue["value"]

                # Map Rhubarb shapes to our phonemes
                phoneme = self._map_rhubarb_shape(shape)
                phonemes.append(PhonemeEvent(
                    phoneme=phoneme,
                    start_time=start,
                    end_time=end,
                ))

            # Get audio duration
            duration = rhubarb_data.get("metadata", {}).get("duration", 0.0)

            # Clean up temp file
            Path(output_json).unlink(missing_ok=True)

            if progress_callback:
                await progress_callback(LipSyncProgress(
                    percent=100,
                    stage="complete",
                    message="Analysis complete",
                ))

            lip_sync_data = LipSyncData(
                audio_path=audio_path,
                duration_seconds=duration,
                phonemes=phonemes,
                metadata={
                    "provider": "rhubarb",
                    "sound_file": rhubarb_data.get("metadata", {}).get("soundFile"),
                },
            )

            return LipSyncResult(
                success=True,
                lip_sync_data=lip_sync_data,
                processing_time_seconds=time.time() - start_time,
            )

        except FileNotFoundError:
            return LipSyncResult(
                success=False,
                error_message="Rhubarb executable not found. Please install Rhubarb Lip Sync.",
            )
        except Exception as e:
            logger.exception("Rhubarb analysis error")
            return LipSyncResult(success=False, error_message=str(e))

    def _map_rhubarb_shape(self, shape: str) -> Phoneme:
        """Map Rhubarb mouth shapes to our phoneme enum."""
        # Rhubarb uses the same Preston Blair shapes
        mapping = {
            "A": Phoneme.A,
            "B": Phoneme.B,
            "C": Phoneme.C,
            "D": Phoneme.D,
            "E": Phoneme.E,
            "F": Phoneme.F,
            "G": Phoneme.G,
            "H": Phoneme.H,
            "X": Phoneme.X,
        }
        return mapping.get(shape, Phoneme.X)

    async def apply_to_video(
        self,
        video_path: str,
        lip_sync_data: LipSyncData,
        output_path: str,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Apply lip sync to video using FFmpeg with phoneme data.

        Note: This is a placeholder. Real implementation would
        require a video manipulation library or AI model.
        """
        # For now, return an error suggesting use of an AI provider
        return LipSyncResult(
            success=False,
            error_message="Rhubarb only provides phoneme extraction. Use Wav2Lip or SadTalker for video lip sync.",
        )

    async def check_availability(self) -> bool:
        """Check if Rhubarb is installed."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.executable_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False


class LipSyncService:
    """Service for managing lip sync operations."""

    def __init__(self):
        self._providers: Dict[LipSyncProvider, LipSyncProviderBase] = {
            LipSyncProvider.MOCK: MockLipSyncProvider(),
        }
        self._settings = get_settings()

    def register_provider(
        self,
        provider_type: LipSyncProvider,
        provider: LipSyncProviderBase,
    ) -> None:
        """Register a lip sync provider."""
        self._providers[provider_type] = provider

    def get_provider(
        self,
        provider_type: LipSyncProvider,
    ) -> Optional[LipSyncProviderBase]:
        """Get a registered provider."""
        return self._providers.get(provider_type)

    async def initialize_providers(self) -> None:
        """Initialize providers from application settings."""
        # Register Rhubarb if available
        rhubarb_path = getattr(self._settings, "rhubarb_path", None)
        rhubarb = RhubarbLipSyncProvider(rhubarb_path)
        if await rhubarb.check_availability():
            self.register_provider(LipSyncProvider.RHUBARB, rhubarb)
            logger.info("Registered Rhubarb Lip Sync provider")

    async def analyze_audio(
        self,
        audio_path: str,
        provider: LipSyncProvider = LipSyncProvider.MOCK,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Analyze audio and extract phoneme timing."""
        provider_instance = self._providers.get(provider)
        if not provider_instance:
            return LipSyncResult(
                success=False,
                error_message=f"Provider {provider.value} not available",
            )

        return await provider_instance.analyze_audio(audio_path, progress_callback)

    async def apply_to_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        provider: LipSyncProvider = LipSyncProvider.MOCK,
        progress_callback: Optional[Callable[[LipSyncProgress], Any]] = None,
    ) -> LipSyncResult:
        """Full pipeline: analyze audio and apply lip sync to video."""
        provider_instance = self._providers.get(provider)
        if not provider_instance:
            return LipSyncResult(
                success=False,
                error_message=f"Provider {provider.value} not available",
            )

        # First, analyze the audio
        analysis_result = await provider_instance.analyze_audio(
            audio_path,
            progress_callback,
        )

        if not analysis_result.success or not analysis_result.lip_sync_data:
            return analysis_result

        # Then apply to video
        return await provider_instance.apply_to_video(
            video_path,
            analysis_result.lip_sync_data,
            output_path,
            progress_callback,
        )

    async def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available lip sync providers with status."""
        providers = []

        for provider_type, provider in self._providers.items():
            available = await provider.check_availability()
            providers.append({
                "provider": provider_type.value,
                "name": provider.name,
                "available": available,
            })

        return providers


# Singleton instance
_lip_sync_service: Optional[LipSyncService] = None


def get_lip_sync_service() -> LipSyncService:
    """Get or create the lip sync service singleton."""
    global _lip_sync_service
    if _lip_sync_service is None:
        _lip_sync_service = LipSyncService()
    return _lip_sync_service
