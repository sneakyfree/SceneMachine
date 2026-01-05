"""
FFmpeg transcoding utilities for video processing.

Handles video transcoding to multiple quality levels for adaptive streaming.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ...shared.config import get_settings


@dataclass
class VideoInfo:
    """Information about a video file."""

    duration_seconds: float
    width: int
    height: int
    fps: float
    codec: str
    bitrate: int
    audio_codec: Optional[str]
    audio_channels: Optional[int]
    audio_sample_rate: Optional[int]
    file_size: int


@dataclass
class TranscodeProfile:
    """Profile for video transcoding."""

    name: str  # e.g., "1080p", "720p", "480p"
    width: int
    height: int
    video_bitrate: str  # e.g., "5000k"
    audio_bitrate: str  # e.g., "128k"
    preset: str  # FFmpeg preset (ultrafast, fast, medium, slow)


# Standard transcoding profiles
TRANSCODE_PROFILES = [
    TranscodeProfile("2160p", 3840, 2160, "15000k", "192k", "medium"),
    TranscodeProfile("1080p", 1920, 1080, "5000k", "128k", "medium"),
    TranscodeProfile("720p", 1280, 720, "2500k", "128k", "medium"),
    TranscodeProfile("480p", 854, 480, "1000k", "96k", "fast"),
    TranscodeProfile("360p", 640, 360, "500k", "64k", "fast"),
]


def get_ffprobe_path() -> str:
    """Get the path to ffprobe executable."""
    return shutil.which("ffprobe") or "ffprobe"


def get_ffmpeg_path() -> str:
    """Get the path to ffmpeg executable."""
    return shutil.which("ffmpeg") or "ffmpeg"


async def get_video_info(file_path: str) -> VideoInfo:
    """
    Get information about a video file using ffprobe.

    Args:
        file_path: Path to the video file

    Returns:
        VideoInfo object with video details
    """
    cmd = [
        get_ffprobe_path(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    data = json.loads(stdout.decode())

    # Find video stream
    video_stream = None
    audio_stream = None
    for stream in data.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio" and audio_stream is None:
            audio_stream = stream

    if video_stream is None:
        raise ValueError("No video stream found")

    # Parse frame rate
    fps_str = video_stream.get("r_frame_rate", "24/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)

    # Get format info
    format_info = data.get("format", {})

    return VideoInfo(
        duration_seconds=float(format_info.get("duration", 0)),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=fps,
        codec=video_stream.get("codec_name", "unknown"),
        bitrate=int(format_info.get("bit_rate", 0)),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        audio_channels=int(audio_stream.get("channels", 0)) if audio_stream else None,
        audio_sample_rate=int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
        file_size=int(format_info.get("size", 0)),
    )


def get_applicable_profiles(video_info: VideoInfo) -> list[TranscodeProfile]:
    """
    Get the transcoding profiles applicable for a video.

    Only includes profiles with resolution <= source resolution.
    """
    profiles = []
    for profile in TRANSCODE_PROFILES:
        if profile.height <= video_info.height:
            profiles.append(profile)
    return profiles


async def generate_thumbnail(
    input_path: str,
    output_path: str,
    time_offset: float = 0,
    width: int = 640,
    height: int = 360,
) -> str:
    """
    Generate a thumbnail from a video.

    Args:
        input_path: Path to the source video
        output_path: Path to save the thumbnail
        time_offset: Time in seconds to extract frame from
        width: Thumbnail width
        height: Thumbnail height

    Returns:
        Path to the generated thumbnail
    """
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-ss", str(time_offset),
        "-i", input_path,
        "-vframes", "1",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "2",
        output_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"Thumbnail generation failed: {stderr.decode()}")

    return output_path


async def generate_thumbnails(
    input_path: str,
    output_dir: str,
    count: int = 3,
    width: int = 640,
    height: int = 360,
) -> list[str]:
    """
    Generate multiple thumbnails from a video at different timestamps.

    Args:
        input_path: Path to the source video
        output_dir: Directory to save thumbnails
        count: Number of thumbnails to generate
        width: Thumbnail width
        height: Thumbnail height

    Returns:
        List of paths to generated thumbnails
    """
    video_info = await get_video_info(input_path)
    duration = video_info.duration_seconds

    # Generate thumbnails at evenly spaced intervals
    thumbnails = []
    for i in range(count):
        time_offset = (duration / (count + 1)) * (i + 1)
        output_path = os.path.join(output_dir, f"thumbnail_{i}.jpg")
        await generate_thumbnail(input_path, output_path, time_offset, width, height)
        thumbnails.append(output_path)

    return thumbnails


async def transcode_video(
    input_path: str,
    output_path: str,
    profile: TranscodeProfile,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> str:
    """
    Transcode a video to a specific profile.

    Args:
        input_path: Path to the source video
        output_path: Path to save the transcoded video
        profile: Transcoding profile to use
        progress_callback: Optional callback(progress_percent)

    Returns:
        Path to the transcoded video
    """
    # Get video duration for progress calculation
    video_info = await get_video_info(input_path)
    duration = video_info.duration_seconds

    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", profile.preset,
        "-b:v", profile.video_bitrate,
        "-maxrate", profile.video_bitrate,
        "-bufsize", f"{int(profile.video_bitrate[:-1]) * 2}k",
        "-vf", f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac",
        "-b:a", profile.audio_bitrate,
        "-ar", "44100",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        output_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Parse progress from stdout
    time_pattern = re.compile(r"out_time_ms=(\d+)")
    last_progress = 0

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        line_str = line.decode()
        match = time_pattern.search(line_str)
        if match and duration > 0:
            time_ms = int(match.group(1))
            progress = min(int((time_ms / 1000000) / duration * 100), 100)
            if progress > last_progress and progress_callback:
                progress_callback(progress)
                last_progress = progress

    await process.wait()

    if process.returncode != 0:
        stderr = await process.stderr.read()
        raise RuntimeError(f"Transcoding failed: {stderr.decode()}")

    return output_path


async def transcode_to_hls(
    input_path: str,
    output_dir: str,
    profiles: Optional[list[TranscodeProfile]] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """
    Transcode a video to HLS format with multiple quality levels.

    Args:
        input_path: Path to the source video
        output_dir: Directory to save HLS files
        profiles: List of profiles to transcode to (auto-detected if None)
        progress_callback: Optional callback(profile_name, progress_percent)

    Returns:
        Dict with transcoding results including manifest paths
    """
    video_info = await get_video_info(input_path)

    if profiles is None:
        profiles = get_applicable_profiles(video_info)

    os.makedirs(output_dir, exist_ok=True)

    results = {
        "source_info": {
            "duration": video_info.duration_seconds,
            "width": video_info.width,
            "height": video_info.height,
        },
        "variants": {},
    }

    # Transcode each profile
    for profile in profiles:
        profile_dir = os.path.join(output_dir, profile.name)
        os.makedirs(profile_dir, exist_ok=True)

        # Transcode to HLS segments
        playlist_path = os.path.join(profile_dir, "playlist.m3u8")

        def profile_progress(progress: int):
            if progress_callback:
                progress_callback(profile.name, progress)

        cmd = [
            get_ffmpeg_path(),
            "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", profile.preset,
            "-b:v", profile.video_bitrate,
            "-maxrate", profile.video_bitrate,
            "-bufsize", f"{int(profile.video_bitrate[:-1]) * 2}k",
            "-vf", f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease",
            "-c:a", "aac",
            "-b:a", profile.audio_bitrate,
            "-ar", "44100",
            "-hls_time", "6",
            "-hls_playlist_type", "vod",
            "-hls_segment_filename", os.path.join(profile_dir, "segment_%03d.ts"),
            playlist_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"HLS transcoding failed for {profile.name}: {stderr.decode()}")

        # Count segments
        segments = [f for f in os.listdir(profile_dir) if f.endswith(".ts")]

        results["variants"][profile.name] = {
            "playlist": playlist_path,
            "width": profile.width,
            "height": profile.height,
            "bitrate": profile.video_bitrate,
            "segments": len(segments),
        }

        if progress_callback:
            progress_callback(profile.name, 100)

    # Generate master playlist
    master_playlist_path = os.path.join(output_dir, "master.m3u8")
    with open(master_playlist_path, "w") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n")
        for profile in profiles:
            variant = results["variants"][profile.name]
            bandwidth = int(profile.video_bitrate[:-1]) * 1000
            f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={variant['width']}x{variant['height']}\n")
            f.write(f"{profile.name}/playlist.m3u8\n")

    results["master_playlist"] = master_playlist_path

    return results


class TranscodingPipeline:
    """
    Complete transcoding pipeline for video processing.

    Handles the full workflow from source upload to HLS output.
    """

    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="transcode_")
        self.settings = get_settings()

    async def process(
        self,
        source_path: str,
        video_id: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> dict:
        """
        Process a video through the full transcoding pipeline.

        Args:
            source_path: Path to the source video file
            video_id: Unique video ID for organizing output
            progress_callback: Optional callback(stage, progress_percent)

        Returns:
            Dict with processing results
        """
        output_dir = os.path.join(self.work_dir, video_id)
        os.makedirs(output_dir, exist_ok=True)

        results = {
            "video_id": video_id,
            "stages": {},
        }

        # Stage 1: Get video info
        if progress_callback:
            progress_callback("analyzing", 0)

        video_info = await get_video_info(source_path)
        results["source_info"] = {
            "duration_seconds": video_info.duration_seconds,
            "width": video_info.width,
            "height": video_info.height,
            "fps": video_info.fps,
            "codec": video_info.codec,
            "file_size": video_info.file_size,
        }
        results["stages"]["analyzing"] = {"status": "completed"}

        if progress_callback:
            progress_callback("analyzing", 100)

        # Stage 2: Generate thumbnails
        if progress_callback:
            progress_callback("thumbnails", 0)

        thumb_dir = os.path.join(output_dir, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        thumbnails = await generate_thumbnails(source_path, thumb_dir)
        results["thumbnails"] = thumbnails
        results["stages"]["thumbnails"] = {"status": "completed", "count": len(thumbnails)}

        if progress_callback:
            progress_callback("thumbnails", 100)

        # Stage 3: Transcode to HLS
        if progress_callback:
            progress_callback("transcoding", 0)

        hls_dir = os.path.join(output_dir, "hls")

        def transcode_progress(profile: str, progress: int):
            if progress_callback:
                # Estimate overall progress based on profile index
                profiles = get_applicable_profiles(video_info)
                profile_names = [p.name for p in profiles]
                if profile in profile_names:
                    idx = profile_names.index(profile)
                    base_progress = (idx / len(profiles)) * 100
                    profile_contribution = (1 / len(profiles)) * progress
                    overall = int(base_progress + profile_contribution)
                    progress_callback("transcoding", overall)

        hls_results = await transcode_to_hls(
            source_path,
            hls_dir,
            progress_callback=transcode_progress,
        )

        results["hls"] = hls_results
        results["stages"]["transcoding"] = {"status": "completed"}

        if progress_callback:
            progress_callback("transcoding", 100)

        results["output_dir"] = output_dir
        results["status"] = "completed"

        return results

    def cleanup(self):
        """Clean up temporary files."""
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
