"""Audio Mixer Service for multi-track audio composition.

Provides audio mixing functionality for video production:
- Multi-track audio mixing with volume control
- Audio effects (fade in/out, crossfade, compression)
- Spatial audio (panning, stereo positioning)
- Audio normalization and leveling
- Music and sound effects library management
- FFmpeg-based audio processing
"""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from scenemachine.config import get_settings

logger = logging.getLogger(__name__)


class AudioTrackType(StrEnum):
    """Types of audio tracks."""

    DIALOGUE = "dialogue"
    MUSIC = "music"
    SFX = "sfx"  # Sound effects
    AMBIENT = "ambient"
    VOICEOVER = "voiceover"
    FOLEY = "foley"


class AudioFormat(StrEnum):
    """Supported audio output formats."""

    MP3 = "mp3"
    WAV = "wav"
    AAC = "aac"
    FLAC = "flac"
    OGG = "ogg"


class FadeType(StrEnum):
    """Types of audio fades."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    SINE = "sine"


@dataclass
class AudioEffect:
    """Base class for audio effects."""

    effect_type: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class FadeEffect(AudioEffect):
    """Fade in/out effect."""

    def __init__(
        self,
        fade_in_duration: float = 0.0,
        fade_out_duration: float = 0.0,
        fade_type: FadeType = FadeType.LINEAR,
    ) -> None:
        super().__init__(
            effect_type="fade",
            parameters={
                "fade_in": fade_in_duration,
                "fade_out": fade_out_duration,
                "type": fade_type.value,
            },
        )


@dataclass
class CompressorEffect(AudioEffect):
    """Dynamic range compressor."""

    def __init__(
        self,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 5.0,
        release_ms: float = 50.0,
        makeup_gain_db: float = 0.0,
    ) -> None:
        super().__init__(
            effect_type="compressor",
            parameters={
                "threshold": threshold_db,
                "ratio": ratio,
                "attack": attack_ms,
                "release": release_ms,
                "makeup": makeup_gain_db,
            },
        )


@dataclass
class EqualizerBand:
    """Single EQ band."""

    frequency: float  # Hz
    gain: float  # dB
    q: float = 1.0  # Q factor


@dataclass
class EqualizerEffect(AudioEffect):
    """Parametric equalizer."""

    def __init__(self, bands: list[EqualizerBand]) -> None:
        super().__init__(
            effect_type="equalizer",
            parameters={"bands": [{"freq": b.frequency, "gain": b.gain, "q": b.q} for b in bands]},
        )


@dataclass
class AudioTrack:
    """A single audio track in the mix."""

    id: str
    name: str
    track_type: AudioTrackType
    file_path: str
    start_time: float = 0.0  # seconds from start of mix
    duration: float | None = None  # None = use full file duration
    volume: float = 1.0  # 0.0 to 2.0 (0% to 200%)
    pan: float = 0.0  # -1.0 (left) to 1.0 (right)
    muted: bool = False
    solo: bool = False
    effects: list[AudioEffect] = field(default_factory=list)
    trim_start: float = 0.0  # seconds trimmed from start of file
    trim_end: float = 0.0  # seconds trimmed from end of file

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.track_type.value,
            "file_path": self.file_path,
            "start_time": self.start_time,
            "duration": self.duration,
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "solo": self.solo,
            "effects": [{"type": e.effect_type, "params": e.parameters} for e in self.effects],
            "trim_start": self.trim_start,
            "trim_end": self.trim_end,
        }


@dataclass
class AudioMix:
    """Complete audio mix configuration."""

    id: str
    name: str
    tracks: list[AudioTrack] = field(default_factory=list)
    master_volume: float = 1.0
    master_effects: list[AudioEffect] = field(default_factory=list)
    sample_rate: int = 44100
    channels: int = 2  # 1=mono, 2=stereo
    duration: float | None = None  # Auto-calculated if None

    def add_track(self, track: AudioTrack) -> None:
        """Add a track to the mix."""
        self.tracks.append(track)

    def remove_track(self, track_id: str) -> bool:
        """Remove a track from the mix."""
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                self.tracks.pop(i)
                return True
        return False

    def get_track(self, track_id: str) -> AudioTrack | None:
        """Get a track by ID."""
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None

    def calculate_duration(self) -> float:
        """Calculate total mix duration based on tracks."""
        if not self.tracks:
            return 0.0

        max_end = 0.0
        for track in self.tracks:
            if not track.muted:
                track_end = track.start_time + (track.duration or 0.0)
                max_end = max(max_end, track_end)

        return max_end

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tracks": [t.to_dict() for t in self.tracks],
            "master_volume": self.master_volume,
            "master_effects": [
                {"type": e.effect_type, "params": e.parameters} for e in self.master_effects
            ],
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration": self.duration or self.calculate_duration(),
        }


@dataclass
class MixProgress:
    """Progress update for mix rendering."""

    percent: float
    stage: str
    message: str
    current_track: str | None = None


@dataclass
class MixResult:
    """Result of mix rendering."""

    success: bool
    output_path: str | None = None
    duration_seconds: float = 0.0
    error_message: str | None = None
    processing_time_seconds: float = 0.0


class AudioMixerService:
    """Service for audio mixing operations.

    Uses FFmpeg for audio processing and mixing.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._ffmpeg_path = "ffmpeg"
        self._ffprobe_path = "ffprobe"

    async def check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                self._ffmpeg_path,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def get_audio_info(self, file_path: str) -> dict[str, Any] | None:
        """Get audio file information using ffprobe."""
        try:
            cmd = [
                self._ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                data = json.loads(stdout.decode())
                format_info = data.get("format", {})
                audio_stream = None

                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "audio":
                        audio_stream = stream
                        break

                return {
                    "duration": float(format_info.get("duration", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 44100))
                    if audio_stream
                    else 44100,
                    "channels": audio_stream.get("channels", 2) if audio_stream else 2,
                    "codec": audio_stream.get("codec_name", "unknown")
                    if audio_stream
                    else "unknown",
                    "bit_rate": int(format_info.get("bit_rate", 0)),
                    "file_size": int(format_info.get("size", 0)),
                }

        except Exception as e:
            logger.warning(f"Failed to get audio info: {e}")

        return None

    def create_mix(self, name: str) -> AudioMix:
        """Create a new audio mix."""
        return AudioMix(
            id=str(uuid4()),
            name=name,
        )

    def create_track(
        self,
        name: str,
        file_path: str,
        track_type: AudioTrackType = AudioTrackType.DIALOGUE,
        start_time: float = 0.0,
        volume: float = 1.0,
    ) -> AudioTrack:
        """Create a new audio track."""
        return AudioTrack(
            id=str(uuid4()),
            name=name,
            track_type=track_type,
            file_path=file_path,
            start_time=start_time,
            volume=volume,
        )

    async def render_mix(
        self,
        mix: AudioMix,
        output_path: str,
        output_format: AudioFormat = AudioFormat.MP3,
        progress_callback: Callable[[MixProgress], Any] | None = None,
    ) -> MixResult:
        """Render an audio mix to a file using FFmpeg."""
        import time

        start_time = time.time()

        if progress_callback:
            await progress_callback(
                MixProgress(
                    percent=0,
                    stage="preparing",
                    message="Preparing audio mix...",
                )
            )

        # Check FFmpeg availability
        if not await self.check_ffmpeg():
            return MixResult(
                success=False,
                error_message="FFmpeg not found. Please install FFmpeg.",
            )

        # Filter out muted tracks
        active_tracks = [t for t in mix.tracks if not t.muted]

        # Handle solo mode
        solo_tracks = [t for t in active_tracks if t.solo]
        if solo_tracks:
            active_tracks = solo_tracks

        if not active_tracks:
            return MixResult(
                success=False,
                error_message="No active tracks to mix.",
            )

        try:
            # Build FFmpeg filter complex
            filter_parts = []
            input_labels = []
            input_args = []

            for i, track in enumerate(active_tracks):
                input_label = f"[{i}:a]"
                input_labels.append(input_label)
                input_args.extend(["-i", track.file_path])

                # Build filter chain for this track
                filters = []

                # Trim
                if track.trim_start > 0 or track.trim_end > 0:
                    trim_end = f":end={track.duration}" if track.duration else ""
                    filters.append(f"atrim=start={track.trim_start}{trim_end}")

                # Delay (start time)
                if track.start_time > 0:
                    delay_ms = int(track.start_time * 1000)
                    filters.append(f"adelay={delay_ms}|{delay_ms}")

                # Volume
                if track.volume != 1.0:
                    filters.append(f"volume={track.volume}")

                # Pan (stereo positioning)
                if track.pan != 0.0:
                    # Convert pan (-1 to 1) to stereo pan filter
                    left = max(0, 1 - track.pan)
                    right = max(0, 1 + track.pan)
                    filters.append(f"pan=stereo|c0={left}*c0|c1={right}*c1")

                # Apply effects
                for effect in track.effects:
                    if effect.effect_type == "fade":
                        params = effect.parameters
                        if params.get("fade_in", 0) > 0:
                            filters.append(f"afade=t=in:d={params['fade_in']}")
                        if params.get("fade_out", 0) > 0:
                            filters.append(f"afade=t=out:d={params['fade_out']}")

                    elif effect.effect_type == "compressor":
                        params = effect.parameters
                        filters.append(
                            f"acompressor=threshold={params['threshold']}dB:"
                            f"ratio={params['ratio']}:"
                            f"attack={params['attack']}:"
                            f"release={params['release']}:"
                            f"makeup={params['makeup']}"
                        )

                    elif effect.effect_type == "equalizer":
                        for band in effect.parameters.get("bands", []):
                            filters.append(
                                f"equalizer=f={band['freq']}:"
                                f"width_type=q:width={band['q']}:"
                                f"g={band['gain']}"
                            )

                # Build filter chain for this track
                out_label = f"[a{i}]"
                if filters:
                    filter_chain = ",".join(filters)
                    filter_parts.append(f"{input_label}{filter_chain}{out_label}")
                else:
                    filter_parts.append(f"{input_label}acopy{out_label}")

                input_labels[i] = out_label

                if progress_callback:
                    percent = 10 + (40 * (i + 1) / len(active_tracks))
                    await progress_callback(
                        MixProgress(
                            percent=percent,
                            stage="processing",
                            message=f"Processing track: {track.name}",
                            current_track=track.name,
                        )
                    )

            # Mix all tracks together
            mix_inputs = "".join(input_labels)
            filter_parts.append(
                f"{mix_inputs}amix=inputs={len(active_tracks)}:duration=longest:normalize=0[mixed]"
            )

            # Master volume
            if mix.master_volume != 1.0:
                filter_parts.append(f"[mixed]volume={mix.master_volume}[master]")
                final_label = "[master]"
            else:
                final_label = "[mixed]"

            # Master effects
            master_filters = []
            for effect in mix.master_effects:
                if effect.effect_type == "compressor":
                    params = effect.parameters
                    master_filters.append(
                        f"acompressor=threshold={params['threshold']}dB:ratio={params['ratio']}"
                    )

            if master_filters:
                filter_parts.append(f"{final_label}{','.join(master_filters)}[final]")
                final_label = "[final]"

            # Build final filter complex
            filter_complex = ";".join(filter_parts)

            if progress_callback:
                await progress_callback(
                    MixProgress(
                        percent=60,
                        stage="rendering",
                        message="Rendering final mix...",
                    )
                )

            # Determine output codec
            codec_args = []
            if output_format == AudioFormat.MP3:
                codec_args = ["-codec:a", "libmp3lame", "-q:a", "2"]
            elif output_format == AudioFormat.AAC:
                codec_args = ["-codec:a", "aac", "-b:a", "192k"]
            elif output_format == AudioFormat.FLAC:
                codec_args = ["-codec:a", "flac"]
            elif output_format == AudioFormat.OGG:
                codec_args = ["-codec:a", "libvorbis", "-q:a", "6"]
            elif output_format == AudioFormat.WAV:
                codec_args = ["-codec:a", "pcm_s16le"]

            # Build FFmpeg command
            cmd = [
                self._ffmpeg_path,
                "-y",  # Overwrite output
                *input_args,
                "-filter_complex",
                filter_complex,
                "-map",
                final_label,
                "-ar",
                str(mix.sample_rate),
                "-ac",
                str(mix.channels),
                *codec_args,
                output_path,
            ]

            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "FFmpeg mix failed"
                return MixResult(
                    success=False,
                    error_message=error_msg,
                )

            if progress_callback:
                await progress_callback(
                    MixProgress(
                        percent=90,
                        stage="finalizing",
                        message="Finalizing output...",
                    )
                )

            # Get output duration
            output_info = await self.get_audio_info(output_path)
            duration = output_info.get("duration", 0) if output_info else 0

            if progress_callback:
                await progress_callback(
                    MixProgress(
                        percent=100,
                        stage="complete",
                        message="Mix complete",
                    )
                )

            return MixResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                processing_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception("Audio mix error")
            return MixResult(
                success=False,
                error_message=str(e),
            )

    async def normalize_audio(
        self,
        input_path: str,
        output_path: str,
        target_lufs: float = -14.0,
        true_peak: float = -1.0,
    ) -> MixResult:
        """Normalize audio to target loudness using EBU R128."""
        import time

        start_time = time.time()

        try:
            # Two-pass loudnorm for best quality
            cmd = [
                self._ffmpeg_path,
                "-y",
                "-i",
                input_path,
                "-af",
                f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11",
                output_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Normalization failed"
                return MixResult(success=False, error_message=error_msg)

            output_info = await self.get_audio_info(output_path)
            duration = output_info.get("duration", 0) if output_info else 0

            return MixResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                processing_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception("Audio normalization error")
            return MixResult(success=False, error_message=str(e))

    async def apply_fade(
        self,
        input_path: str,
        output_path: str,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> MixResult:
        """Apply fade in/out to audio file."""
        import time

        start_time = time.time()

        try:
            # Get input duration for fade out
            input_info = await self.get_audio_info(input_path)
            duration = input_info.get("duration", 0) if input_info else 0

            filters = []
            if fade_in > 0:
                filters.append(f"afade=t=in:st=0:d={fade_in}")
            if fade_out > 0:
                fade_start = duration - fade_out
                filters.append(f"afade=t=out:st={fade_start}:d={fade_out}")

            if not filters:
                # No fades, just copy
                import shutil

                shutil.copy(input_path, output_path)
                return MixResult(
                    success=True,
                    output_path=output_path,
                    duration_seconds=duration,
                    processing_time_seconds=time.time() - start_time,
                )

            cmd = [
                self._ffmpeg_path,
                "-y",
                "-i",
                input_path,
                "-af",
                ",".join(filters),
                output_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if process.returncode != 0:
                return MixResult(success=False, error_message="Fade application failed")

            return MixResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                processing_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception("Audio fade error")
            return MixResult(success=False, error_message=str(e))

    async def crossfade(
        self,
        audio1_path: str,
        audio2_path: str,
        output_path: str,
        crossfade_duration: float = 2.0,
    ) -> MixResult:
        """Crossfade between two audio files."""
        import time

        start_time = time.time()

        try:
            cmd = [
                self._ffmpeg_path,
                "-y",
                "-i",
                audio1_path,
                "-i",
                audio2_path,
                "-filter_complex",
                f"acrossfade=d={crossfade_duration}:c1=tri:c2=tri",
                output_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Crossfade failed"
                return MixResult(success=False, error_message=error_msg)

            output_info = await self.get_audio_info(output_path)
            duration = output_info.get("duration", 0) if output_info else 0

            return MixResult(
                success=True,
                output_path=output_path,
                duration_seconds=duration,
                processing_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception("Audio crossfade error")
            return MixResult(success=False, error_message=str(e))


# Singleton instance
_audio_mixer_service: AudioMixerService | None = None


def get_audio_mixer_service() -> AudioMixerService:
    """Get or create the audio mixer service singleton."""
    global _audio_mixer_service
    if _audio_mixer_service is None:
        _audio_mixer_service = AudioMixerService()
    return _audio_mixer_service
