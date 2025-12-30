"""FFmpeg utilities with proper validation and error handling.

Provides a centralized interface for FFmpeg operations with:
- Availability checking at startup
- Detailed error messages
- Progress parsing
- Fallback handling
"""

import asyncio
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Base exception for FFmpeg errors."""

    pass


class FFmpegNotFoundError(FFmpegError):
    """FFmpeg is not installed or not in PATH."""

    pass


class FFmpegExecutionError(FFmpegError):
    """FFmpeg command execution failed."""

    def __init__(self, message: str, stderr: str = "", returncode: int = -1):
        super().__init__(message)
        self.stderr = stderr
        self.returncode = returncode


class FFmpegTimeoutError(FFmpegError):
    """FFmpeg operation timed out."""

    pass


@dataclass
class FFmpegInfo:
    """Information about the FFmpeg installation."""

    available: bool = False
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None
    version: Optional[str] = None
    codecs: List[str] = field(default_factory=list)
    formats: List[str] = field(default_factory=list)
    has_nvenc: bool = False
    has_vaapi: bool = False
    has_qsv: bool = False
    error_message: Optional[str] = None


@dataclass
class VideoInfo:
    """Information about a video file."""

    path: str
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    bitrate: int = 0
    file_size_bytes: int = 0
    has_audio: bool = False
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None


@dataclass
class FFmpegProgress:
    """Progress information from FFmpeg."""

    frame: int = 0
    fps: float = 0.0
    time_seconds: float = 0.0
    bitrate: str = ""
    speed: float = 0.0
    percent: float = 0.0


class FFmpegValidator:
    """Validates and provides information about FFmpeg installation."""

    _instance: Optional["FFmpegValidator"] = None
    _info: Optional[FFmpegInfo] = None

    def __new__(cls) -> "FFmpegValidator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def check(cls) -> FFmpegInfo:
        """Check FFmpeg availability and capabilities.

        Returns:
            FFmpegInfo with details about the installation
        """
        if cls._info is not None:
            return cls._info

        info = FFmpegInfo()

        # Find ffmpeg
        ffmpeg_path = shutil.which("ffmpeg")
        ffprobe_path = shutil.which("ffprobe")

        if not ffmpeg_path:
            info.error_message = (
                "FFmpeg not found. Please install FFmpeg:\n"
                "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  - macOS: brew install ffmpeg\n"
                "  - Windows: Download from https://ffmpeg.org/download.html"
            )
            cls._info = info
            return info

        info.available = True
        info.ffmpeg_path = ffmpeg_path
        info.ffprobe_path = ffprobe_path

        # Get version
        try:
            process = await asyncio.create_subprocess_exec(
                ffmpeg_path,
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            version_output = stdout.decode()

            # Parse version
            version_match = re.search(r"ffmpeg version (\S+)", version_output)
            if version_match:
                info.version = version_match.group(1)

            # Check for hardware acceleration
            info.has_nvenc = "nvenc" in version_output.lower()
            info.has_vaapi = "vaapi" in version_output.lower()
            info.has_qsv = "qsv" in version_output.lower()

        except Exception as e:
            logger.warning(f"Could not get FFmpeg version: {e}")

        # Get supported codecs
        try:
            process = await asyncio.create_subprocess_exec(
                ffmpeg_path,
                "-codecs",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            codec_output = stdout.decode()

            # Parse common video codecs
            common_codecs = ["h264", "hevc", "h265", "vp9", "av1", "prores"]
            for codec in common_codecs:
                if codec in codec_output.lower():
                    info.codecs.append(codec)

        except Exception as e:
            logger.warning(f"Could not get FFmpeg codecs: {e}")

        # Get supported formats
        try:
            process = await asyncio.create_subprocess_exec(
                ffmpeg_path,
                "-formats",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            format_output = stdout.decode()

            # Parse common formats
            common_formats = ["mp4", "mov", "mkv", "webm", "avi", "gif"]
            for fmt in common_formats:
                if fmt in format_output.lower():
                    info.formats.append(fmt)

        except Exception as e:
            logger.warning(f"Could not get FFmpeg formats: {e}")

        cls._info = info
        logger.info(
            f"FFmpeg validated: version={info.version}, "
            f"codecs={len(info.codecs)}, formats={len(info.formats)}"
        )

        return info

    @classmethod
    def require(cls) -> None:
        """Require FFmpeg to be available, raise if not.

        Raises:
            FFmpegNotFoundError: If FFmpeg is not available
        """
        if cls._info is None:
            # Synchronous check for startup validation
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(cls.check())
            finally:
                loop.close()

        if not cls._info or not cls._info.available:
            raise FFmpegNotFoundError(
                cls._info.error_message if cls._info else "FFmpeg not found"
            )

    @classmethod
    def is_available(cls) -> bool:
        """Check if FFmpeg is available."""
        if cls._info is None:
            return False
        return cls._info.available


class FFmpeg:
    """High-level interface for FFmpeg operations."""

    def __init__(self):
        self._info: Optional[FFmpegInfo] = None

    async def ensure_available(self) -> FFmpegInfo:
        """Ensure FFmpeg is available.

        Returns:
            FFmpegInfo with installation details

        Raises:
            FFmpegNotFoundError: If FFmpeg is not available
        """
        self._info = await FFmpegValidator.check()

        if not self._info.available:
            raise FFmpegNotFoundError(self._info.error_message or "FFmpeg not found")

        return self._info

    async def get_video_info(self, video_path: Path) -> VideoInfo:
        """Get detailed information about a video file.

        Args:
            video_path: Path to video file

        Returns:
            VideoInfo with file details

        Raises:
            FFmpegError: If file cannot be analyzed
        """
        await self.ensure_available()

        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")

        info = VideoInfo(path=str(video_path))
        info.file_size_bytes = video_path.stat().st_size

        try:
            cmd = [
                self._info.ffprobe_path or "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise FFmpegExecutionError(
                    f"ffprobe failed: {stderr.decode()}",
                    stderr=stderr.decode(),
                    returncode=process.returncode,
                )

            data = json.loads(stdout.decode())

            # Parse format info
            if "format" in data:
                fmt = data["format"]
                info.duration_seconds = float(fmt.get("duration", 0))
                info.bitrate = int(fmt.get("bit_rate", 0))

            # Parse stream info
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info.width = stream.get("width", 0)
                    info.height = stream.get("height", 0)
                    info.codec = stream.get("codec_name", "")

                    # Parse FPS
                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        if int(den) > 0:
                            info.fps = int(num) / int(den)

                elif stream.get("codec_type") == "audio":
                    info.has_audio = True
                    info.audio_codec = stream.get("codec_name")
                    info.audio_sample_rate = stream.get("sample_rate")

        except json.JSONDecodeError as e:
            raise FFmpegError(f"Failed to parse ffprobe output: {e}")
        except Exception as e:
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Failed to get video info: {e}")

        return info

    async def get_duration(self, file_path: Path) -> float:
        """Get duration of a media file in seconds.

        Args:
            file_path: Path to media file

        Returns:
            Duration in seconds
        """
        await self.ensure_available()

        try:
            cmd = [
                self._info.ffprobe_path or "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise FFmpegExecutionError(
                    f"ffprobe failed: {stderr.decode()}",
                    stderr=stderr.decode(),
                    returncode=process.returncode,
                )

            return float(stdout.decode().strip())

        except ValueError as e:
            raise FFmpegError(f"Could not parse duration: {e}")

    async def extract_frame(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: float = 1.0,
        quality: int = 2,
    ) -> Path:
        """Extract a frame from a video.

        Args:
            video_path: Source video path
            output_path: Output image path
            timestamp: Time in seconds to extract frame
            quality: JPEG quality (2=best, 31=worst)

        Returns:
            Path to extracted frame
        """
        await self.ensure_available()

        if not video_path.exists():
            raise FFmpegError(f"Video file not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._info.ffmpeg_path or "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", str(quality),
            str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0 or not output_path.exists():
            raise FFmpegExecutionError(
                f"Frame extraction failed: {stderr.decode()}",
                stderr=stderr.decode(),
                returncode=process.returncode,
            )

        return output_path

    async def concatenate_videos(
        self,
        input_paths: List[Path],
        output_path: Path,
        progress_callback: Optional[Callable[[FFmpegProgress], None]] = None,
        timeout: int = 3600,
    ) -> Path:
        """Concatenate multiple videos into one.

        Args:
            input_paths: List of video paths to concatenate
            output_path: Output video path
            progress_callback: Optional progress callback
            timeout: Maximum execution time in seconds

        Returns:
            Path to concatenated video
        """
        await self.ensure_available()

        if not input_paths:
            raise FFmpegError("No input videos provided")

        for path in input_paths:
            if not path.exists():
                raise FFmpegError(f"Input video not found: {path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create concat file
        concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
        with open(concat_file, "w") as f:
            for path in input_paths:
                # Escape special characters in paths
                escaped_path = str(path).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            cmd = [
                self._info.ffmpeg_path or "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-progress", "pipe:1",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Calculate total duration for progress
            total_duration = 0.0
            for path in input_paths:
                try:
                    total_duration += await self.get_duration(path)
                except Exception:
                    pass

            # Parse progress output
            if progress_callback and total_duration > 0:
                await self._parse_progress(process, total_duration, progress_callback)

            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            if process.returncode != 0 or not output_path.exists():
                raise FFmpegExecutionError(
                    f"Concatenation failed: {stderr.decode()}",
                    stderr=stderr.decode(),
                    returncode=process.returncode,
                )

        except asyncio.TimeoutError:
            process.kill()
            raise FFmpegTimeoutError(f"Concatenation timed out after {timeout}s")

        finally:
            # Clean up concat file
            concat_file.unlink(missing_ok=True)

        return output_path

    async def transcode(
        self,
        input_path: Path,
        output_path: Path,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        video_bitrate: Optional[str] = None,
        audio_bitrate: str = "192k",
        resolution: Optional[Tuple[int, int]] = None,
        fps: Optional[int] = None,
        crf: Optional[int] = None,
        preset: str = "medium",
        progress_callback: Optional[Callable[[FFmpegProgress], None]] = None,
        timeout: int = 3600,
    ) -> Path:
        """Transcode a video file.

        Args:
            input_path: Source video path
            output_path: Output video path
            video_codec: Video codec (libx264, libx265, etc.)
            audio_codec: Audio codec (aac, mp3, etc.)
            video_bitrate: Video bitrate (e.g., "5M")
            audio_bitrate: Audio bitrate (e.g., "192k")
            resolution: Output resolution (width, height)
            fps: Output frame rate
            crf: Constant rate factor (quality, lower=better)
            preset: Encoding preset (ultrafast to veryslow)
            progress_callback: Optional progress callback
            timeout: Maximum execution time in seconds

        Returns:
            Path to transcoded video
        """
        await self.ensure_available()

        if not input_path.exists():
            raise FFmpegError(f"Input video not found: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._info.ffmpeg_path or "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-c:v", video_codec,
            "-c:a", audio_codec,
            "-preset", preset,
        ]

        if video_bitrate:
            cmd.extend(["-b:v", video_bitrate])

        if crf is not None:
            cmd.extend(["-crf", str(crf)])

        cmd.extend(["-b:a", audio_bitrate])

        if resolution:
            cmd.extend(["-vf", f"scale={resolution[0]}:{resolution[1]}"])

        if fps:
            cmd.extend(["-r", str(fps)])

        cmd.extend(["-progress", "pipe:1", str(output_path)])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Get input duration for progress
            input_duration = await self.get_duration(input_path)

            if progress_callback and input_duration > 0:
                await self._parse_progress(process, input_duration, progress_callback)

            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            if process.returncode != 0 or not output_path.exists():
                raise FFmpegExecutionError(
                    f"Transcoding failed: {stderr.decode()}",
                    stderr=stderr.decode(),
                    returncode=process.returncode,
                )

        except asyncio.TimeoutError:
            process.kill()
            raise FFmpegTimeoutError(f"Transcoding timed out after {timeout}s")

        return output_path

    async def _parse_progress(
        self,
        process: asyncio.subprocess.Process,
        total_duration: float,
        callback: Callable[[FFmpegProgress], None],
    ) -> None:
        """Parse FFmpeg progress output and call callback."""
        progress = FFmpegProgress()

        async def read_progress():
            while True:
                if process.stdout is None:
                    break

                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()

                # Parse progress values
                if line_str.startswith("frame="):
                    try:
                        progress.frame = int(line_str.split("=")[1])
                    except (ValueError, IndexError):
                        pass

                elif line_str.startswith("fps="):
                    try:
                        progress.fps = float(line_str.split("=")[1])
                    except (ValueError, IndexError):
                        pass

                elif line_str.startswith("out_time_ms="):
                    try:
                        time_ms = int(line_str.split("=")[1])
                        progress.time_seconds = time_ms / 1_000_000
                        progress.percent = min(
                            100, (progress.time_seconds / total_duration) * 100
                        )
                    except (ValueError, IndexError):
                        pass

                elif line_str.startswith("speed="):
                    try:
                        speed_str = line_str.split("=")[1].replace("x", "")
                        progress.speed = float(speed_str)
                    except (ValueError, IndexError):
                        pass

                elif line_str.startswith("progress="):
                    # End of frame block, call callback
                    try:
                        callback(progress)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

        try:
            await asyncio.wait_for(read_progress(), timeout=1.0)
        except asyncio.TimeoutError:
            pass


# Global FFmpeg instance
_ffmpeg: Optional[FFmpeg] = None


def get_ffmpeg() -> FFmpeg:
    """Get the global FFmpeg instance."""
    global _ffmpeg
    if _ffmpeg is None:
        _ffmpeg = FFmpeg()
    return _ffmpeg


async def validate_ffmpeg() -> FFmpegInfo:
    """Validate FFmpeg at application startup.

    Returns:
        FFmpegInfo with installation details

    Raises:
        FFmpegNotFoundError: If FFmpeg is required but not available
    """
    ffmpeg = get_ffmpeg()
    return await ffmpeg.ensure_available()
