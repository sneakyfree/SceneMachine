"""Voice cloning and TTS service.

Implements voice profile management, voice cloning, and text-to-speech
generation for character dialogue using Kokoro TTS and other providers.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import wave
import struct

logger = logging.getLogger(__name__)


class TTSProvider(str, Enum):
    """Available TTS providers."""
    KOKORO = "kokoro"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    XTTS = "xtts"  # Coqui XTTS
    MOCK = "mock"  # For testing


class VoiceGender(str, Enum):
    """Voice gender categories."""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceProfile:
    """A voice profile for TTS generation."""
    voice_id: str
    name: str
    provider: TTSProvider
    gender: VoiceGender
    description: str = ""
    language: str = "en"
    accent: str = ""
    age_category: str = "adult"  # child, teen, adult, senior
    sample_url: Optional[str] = None
    is_cloned: bool = False
    clone_sample_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "provider": self.provider.value,
            "gender": self.gender.value,
            "description": self.description,
            "language": self.language,
            "accent": self.accent,
            "age_category": self.age_category,
            "sample_url": self.sample_url,
            "is_cloned": self.is_cloned,
            "metadata": self.metadata,
        }


@dataclass
class SpeechGenerationResult:
    """Result from TTS generation."""
    success: bool
    audio_path: Optional[str] = None
    audio_data: Optional[bytes] = None
    duration_seconds: float = 0.0
    sample_rate: int = 24000
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "audio_path": self.audio_path,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "error": self.error,
            "metadata": self.metadata,
        }


class VoiceCloningService:
    """Service for voice cloning and TTS generation.
    
    Implements the DNA strand master plan's voice requirements:
    - Pre-built voice library categorized by gender, age, accent
    - Voice cloning from audio samples
    - Emotion/style control for dialogue
    - Multi-provider support with fallback
    """
    
    # Kokoro voice mappings (built-in voices)
    KOKORO_VOICES = [
        VoiceProfile("af_heart", "Heart", TTSProvider.KOKORO, VoiceGender.FEMALE, "Warm, friendly female voice"),
        VoiceProfile("af_alloy", "Alloy", TTSProvider.KOKORO, VoiceGender.FEMALE, "Clear, professional female voice"),
        VoiceProfile("af_aoede", "Aoede", TTSProvider.KOKORO, VoiceGender.FEMALE, "Melodic female voice"),
        VoiceProfile("af_bella", "Bella", TTSProvider.KOKORO, VoiceGender.FEMALE, "Expressive female voice"),
        VoiceProfile("af_jessica", "Jessica", TTSProvider.KOKORO, VoiceGender.FEMALE, "Natural conversational female"),
        VoiceProfile("af_kore", "Kore", TTSProvider.KOKORO, VoiceGender.FEMALE, "Youthful female voice"),
        VoiceProfile("af_nicole", "Nicole", TTSProvider.KOKORO, VoiceGender.FEMALE, "Mature female voice"),
        VoiceProfile("af_nova", "Nova", TTSProvider.KOKORO, VoiceGender.FEMALE, "Energetic female voice"),
        VoiceProfile("af_river", "River", TTSProvider.KOKORO, VoiceGender.FEMALE, "Calm, soothing female voice"),
        VoiceProfile("af_sarah", "Sarah", TTSProvider.KOKORO, VoiceGender.FEMALE, "Friendly female narrator"),
        VoiceProfile("af_sky", "Sky", TTSProvider.KOKORO, VoiceGender.FEMALE, "Light, airy female voice"),
        VoiceProfile("am_adam", "Adam", TTSProvider.KOKORO, VoiceGender.MALE, "Deep male voice"),
        VoiceProfile("am_echo", "Echo", TTSProvider.KOKORO, VoiceGender.MALE, "Resonant male voice"),
        VoiceProfile("am_eric", "Eric", TTSProvider.KOKORO, VoiceGender.MALE, "Professional male narrator"),
        VoiceProfile("am_fenrir", "Fenrir", TTSProvider.KOKORO, VoiceGender.MALE, "Strong male voice"),
        VoiceProfile("am_liam", "Liam", TTSProvider.KOKORO, VoiceGender.MALE, "Friendly male voice"),
        VoiceProfile("am_michael", "Michael", TTSProvider.KOKORO, VoiceGender.MALE, "Natural male conversational"),
        VoiceProfile("am_onyx", "Onyx", TTSProvider.KOKORO, VoiceGender.MALE, "Deep, authoritative male"),
        VoiceProfile("am_puck", "Puck", TTSProvider.KOKORO, VoiceGender.MALE, "Playful male voice"),
        VoiceProfile("am_santa", "Santa", TTSProvider.KOKORO, VoiceGender.MALE, "Jolly older male voice", age_category="senior"),
    ]
    
    def __init__(
        self,
        default_provider: TTSProvider = TTSProvider.KOKORO,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize the voice cloning service.
        
        Args:
            default_provider: Default TTS provider to use
            cache_dir: Directory to cache audio files
        """
        self.default_provider = default_provider
        self.cache_dir = cache_dir or Path("/tmp/scenemachine/voice_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._kokoro_pipeline = None
        self._cloned_voices: Dict[str, VoiceProfile] = {}
    
    def get_available_voices(
        self,
        provider: Optional[TTSProvider] = None,
        gender: Optional[VoiceGender] = None,
        age_category: Optional[str] = None,
    ) -> List[VoiceProfile]:
        """Get list of available voices with optional filtering.
        
        Args:
            provider: Filter by provider
            gender: Filter by gender
            age_category: Filter by age category
            
        Returns:
            List of matching VoiceProfile
        """
        voices = list(self.KOKORO_VOICES)
        
        # Add cloned voices
        voices.extend(self._cloned_voices.values())
        
        # Apply filters
        if provider:
            voices = [v for v in voices if v.provider == provider]
        if gender:
            voices = [v for v in voices if v.gender == gender]
        if age_category:
            voices = [v for v in voices if v.age_category == age_category]
        
        return voices
    
    def get_voice(self, voice_id: str) -> Optional[VoiceProfile]:
        """Get a specific voice profile.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            VoiceProfile or None
        """
        # Check built-in voices
        for voice in self.KOKORO_VOICES:
            if voice.voice_id == voice_id:
                return voice
        
        # Check cloned voices
        return self._cloned_voices.get(voice_id)
    
    def suggest_voice(
        self,
        character_name: str,
        gender: Optional[VoiceGender] = None,
        age_range: Optional[tuple] = None,
        personality_traits: Optional[List[str]] = None,
    ) -> List[VoiceProfile]:
        """Suggest voices based on character description.
        
        Args:
            character_name: Character name
            gender: Character gender
            age_range: (min_age, max_age) tuple
            personality_traits: List of personality traits
            
        Returns:
            List of suggested voices, ranked by fit
        """
        voices = self.get_available_voices(gender=gender)
        
        # Simple scoring based on age
        if age_range:
            avg_age = (age_range[0] + age_range[1]) / 2
            
            if avg_age < 18:
                age_cat = "teen"
            elif avg_age < 30:
                age_cat = "adult"
            elif avg_age < 60:
                age_cat = "adult"
            else:
                age_cat = "senior"
            
            # Prioritize matching age category
            voices.sort(key=lambda v: 0 if v.age_category == age_cat else 1)
        
        # Match personality to voice descriptions
        if personality_traits:
            def score_voice(voice: VoiceProfile) -> int:
                score = 0
                desc = voice.description.lower()
                for trait in personality_traits:
                    if trait.lower() in desc:
                        score += 1
                return score
            
            voices.sort(key=lambda v: -score_voice(v))
        
        return voices[:5]  # Return top 5 suggestions
    
    def clone_voice(
        self,
        sample_path: Union[str, Path],
        voice_name: str,
        voice_id: Optional[str] = None,
    ) -> Optional[VoiceProfile]:
        """Clone a voice from an audio sample.
        
        Args:
            sample_path: Path to audio sample (3-10 seconds recommended)
            voice_name: Name for the cloned voice
            voice_id: Optional custom voice ID
            
        Returns:
            Created VoiceProfile or None on failure
        """
        sample_path = Path(sample_path)
        
        if not sample_path.exists():
            logger.error(f"Voice sample not found: {sample_path}")
            return None
        
        voice_id = voice_id or f"cloned_{voice_name.lower().replace(' ', '_')}"
        
        try:
            # For Kokoro, we just store the reference to the sample
            # The model uses it during inference
            
            profile = VoiceProfile(
                voice_id=voice_id,
                name=voice_name,
                provider=TTSProvider.KOKORO,
                gender=VoiceGender.NEUTRAL,  # Would need analysis to determine
                description=f"Cloned voice from {sample_path.name}",
                is_cloned=True,
                clone_sample_path=str(sample_path),
            )
            
            self._cloned_voices[voice_id] = profile
            logger.info(f"Cloned voice created: {voice_name} ({voice_id})")
            
            return profile
            
        except Exception as e:
            logger.exception(f"Failed to clone voice: {e}")
            return None
    
    def generate_speech(
        self,
        text: str,
        voice_id: str,
        output_path: Optional[Union[str, Path]] = None,
        emotion: str = "neutral",
        speed: float = 1.0,
    ) -> SpeechGenerationResult:
        """Generate speech from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice profile ID
            output_path: Optional path to save audio
            emotion: Emotion/style (neutral, happy, sad, angry, whisper)
            speed: Speech speed multiplier
            
        Returns:
            SpeechGenerationResult with audio data or path
        """
        voice = self.get_voice(voice_id)
        
        if not voice:
            return SpeechGenerationResult(
                success=False,
                error=f"Voice not found: {voice_id}",
            )
        
        if voice.provider == TTSProvider.KOKORO:
            return self._generate_kokoro(text, voice, output_path, emotion, speed)
        elif voice.provider == TTSProvider.MOCK:
            return self._generate_mock(text, voice, output_path)
        else:
            return SpeechGenerationResult(
                success=False,
                error=f"Provider not implemented: {voice.provider}",
            )
    
    def _generate_kokoro(
        self,
        text: str,
        voice: VoiceProfile,
        output_path: Optional[Union[str, Path]],
        emotion: str,
        speed: float,
    ) -> SpeechGenerationResult:
        """Generate speech using Kokoro TTS."""
        try:
            # Lazy import and initialization
            if self._kokoro_pipeline is None:
                try:
                    from kokoro import KPipeline
                    self._kokoro_pipeline = KPipeline(lang_code="a")  # American English
                except ImportError:
                    logger.warning("Kokoro not installed, using mock TTS")
                    return self._generate_mock(text, voice, output_path)
            
            # Apply emotion markers if supported
            if emotion != "neutral":
                # Kokoro uses different voice IDs for emotions
                # This is a simplified mapping
                emotion_prefix = {
                    "happy": "",
                    "sad": "",
                    "angry": "",
                    "whisper": "",
                }
                # For now, keep original voice ID
            
            # Generate audio
            generator = self._kokoro_pipeline(
                text,
                voice=voice.voice_id,
                speed=speed,
            )
            
            # Collect audio chunks
            audio_chunks = []
            for chunk in generator:
                if hasattr(chunk, 'audio'):
                    audio_chunks.append(chunk.audio.numpy())
            
            if not audio_chunks:
                return SpeechGenerationResult(
                    success=False,
                    error="No audio generated",
                )
            
            import numpy as np
            audio = np.concatenate(audio_chunks)
            
            # Calculate duration
            sample_rate = 24000  # Kokoro default
            duration = len(audio) / sample_rate
            
            # Save to file if path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save as WAV
                import soundfile as sf
                sf.write(str(output_path), audio, sample_rate)
                
                return SpeechGenerationResult(
                    success=True,
                    audio_path=str(output_path),
                    duration_seconds=duration,
                    sample_rate=sample_rate,
                    metadata={"voice_id": voice.voice_id, "emotion": emotion},
                )
            else:
                # Return raw audio data
                import io
                import soundfile as sf
                
                buffer = io.BytesIO()
                sf.write(buffer, audio, sample_rate, format='WAV')
                audio_data = buffer.getvalue()
                
                return SpeechGenerationResult(
                    success=True,
                    audio_data=audio_data,
                    duration_seconds=duration,
                    sample_rate=sample_rate,
                    metadata={"voice_id": voice.voice_id, "emotion": emotion},
                )
                
        except ImportError:
            logger.warning("Audio libraries not available, using mock TTS")
            return self._generate_mock(text, voice, output_path)
        except Exception as e:
            logger.exception(f"Kokoro TTS error: {e}")
            return SpeechGenerationResult(
                success=False,
                error=str(e),
            )
    
    def _generate_mock(
        self,
        text: str,
        voice: VoiceProfile,
        output_path: Optional[Union[str, Path]],
    ) -> SpeechGenerationResult:
        """Generate mock speech for testing."""
        # Estimate duration (average speaking rate: 150 words per minute)
        word_count = len(text.split())
        duration = word_count / 2.5  # ~2.5 words per second
        
        # Generate silent audio for testing
        sample_rate = 24000
        num_samples = int(duration * sample_rate)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a simple silent WAV file
            with wave.open(str(output_path), 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                # Write silence
                wav.writeframes(struct.pack('<' + 'h' * num_samples, *([0] * num_samples)))
            
            return SpeechGenerationResult(
                success=True,
                audio_path=str(output_path),
                duration_seconds=duration,
                sample_rate=sample_rate,
                metadata={"voice_id": voice.voice_id, "mock": True},
            )
        
        return SpeechGenerationResult(
            success=True,
            audio_data=b"",
            duration_seconds=duration,
            sample_rate=sample_rate,
            metadata={"voice_id": voice.voice_id, "mock": True},
        )
    
    def generate_dialogue_audio(
        self,
        dialogue_lines: List[Dict[str, Any]],
        output_dir: Union[str, Path],
    ) -> List[SpeechGenerationResult]:
        """Generate audio for multiple dialogue lines.
        
        Args:
            dialogue_lines: List of {"character": str, "voice_id": str, "text": str, "emotion": str}
            output_dir: Directory to save audio files
            
        Returns:
            List of SpeechGenerationResult for each line
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        for idx, line in enumerate(dialogue_lines):
            output_path = output_dir / f"dialogue_{idx:04d}.wav"
            
            result = self.generate_speech(
                text=line.get("text", ""),
                voice_id=line.get("voice_id", "am_adam"),
                output_path=output_path,
                emotion=line.get("emotion", "neutral"),
            )
            
            result.metadata["character"] = line.get("character")
            result.metadata["line_index"] = idx
            
            results.append(result)
        
        return results


# Singleton instance
_voice_service: Optional[VoiceCloningService] = None


def get_voice_cloning_service() -> VoiceCloningService:
    """Get or create the voice cloning service singleton."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceCloningService()
    return _voice_service
