"""Assembly and export service.

Handles scene assembly, movie composition, and export operations.
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.config import get_settings
from scenemachine.models import Project, Scene, Shot
from scenemachine.models.asset import Asset, AssetStatus, AssetType
from scenemachine.models.export_history import (
    ExportHistory,
    ExportStatus as ExportHistoryStatus,
)
from scenemachine.models.project import ProjectState
from scenemachine.models.shot import ShotState
from scenemachine.utils.ffmpeg import (
    FFmpeg,
    FFmpegError,
    FFmpegNotFoundError,
    FFmpegExecutionError,
    get_ffmpeg,
)

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    MP4_H264 = "mp4_h264"  # Standard H.264 in MP4
    MP4_H265 = "mp4_h265"  # HEVC in MP4
    MOV_PRORES = "mov_prores"  # ProRes in MOV
    WEBM_VP9 = "webm_vp9"  # VP9 in WebM
    MKV_H264 = "mkv_h264"  # H.264 in MKV


class ExportQuality(str, Enum):
    """Export quality presets."""

    DRAFT = "draft"  # Fast, lower quality
    STANDARD = "standard"  # Balanced
    HIGH = "high"  # High quality
    MASTER = "master"  # Maximum quality


@dataclass
class ColorGradeSettings:
    """Color grading settings for export."""

    exposure: float = 0.0  # -2 to 2
    contrast: float = 0.0  # -100 to 100
    saturation: float = 0.0  # -100 to 100
    temperature: float = 0.0  # -100 to 100 (cool to warm)
    vignette_amount: float = 0.0  # 0 to 100
    lut_path: Optional[str] = None
    lut_intensity: float = 100.0  # 0 to 100


@dataclass
class ExportSettings:
    """Settings for movie export."""

    format: ExportFormat = ExportFormat.MP4_H264
    quality: ExportQuality = ExportQuality.HIGH
    resolution: str = "1920x1080"
    frame_rate: int = 24
    video_bitrate: str = "10M"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    include_audio: bool = True
    include_subtitles: bool = False
    watermark: Optional[str] = None
    watermark_position: str = "bottom_right"
    watermark_opacity: float = 0.5
    color_grade: Optional[ColorGradeSettings] = None
    subtitle_path: Optional[str] = None
    audio_tracks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AssemblyProgress:
    """Progress update for assembly operation."""

    stage: str
    percent: float
    message: str
    current_scene: Optional[int] = None
    total_scenes: Optional[int] = None


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    output_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneRender:
    """Rendered scene information."""

    scene_id: str
    scene_number: str
    output_path: str
    duration_seconds: float
    shot_count: int


@dataclass
class Timeline:
    """Movie timeline representation."""

    project_id: str
    total_duration: float
    scene_count: int
    shot_count: int
    scenes: List[Dict[str, Any]]


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    async def __call__(self, progress: AssemblyProgress) -> None:
        """Called when progress updates."""
        ...


class AssemblyService:
    """Service for assembling shots into scenes and exporting movies.

    Handles:
    - Scene assembly from approved shots
    - Movie composition from scenes
    - Export with various formats and quality settings
    - Progress tracking
    """

    # FFmpeg codec settings by format
    CODEC_SETTINGS = {
        ExportFormat.MP4_H264: {
            "video_codec": "libx264",
            "profile": "high",
            "preset": "medium",
            "container": "mp4",
        },
        ExportFormat.MP4_H265: {
            "video_codec": "libx265",
            "profile": "main",
            "preset": "medium",
            "container": "mp4",
        },
        ExportFormat.MOV_PRORES: {
            "video_codec": "prores_ks",
            "profile": "3",  # ProRes 422 HQ
            "preset": None,
            "container": "mov",
        },
        ExportFormat.WEBM_VP9: {
            "video_codec": "libvpx-vp9",
            "profile": None,
            "preset": None,
            "container": "webm",
        },
        ExportFormat.MKV_H264: {
            "video_codec": "libx264",
            "profile": "high",
            "preset": "medium",
            "container": "mkv",
        },
    }

    # Quality presets
    QUALITY_SETTINGS = {
        ExportQuality.DRAFT: {"crf": 28, "preset_override": "ultrafast"},
        ExportQuality.STANDARD: {"crf": 23, "preset_override": "medium"},
        ExportQuality.HIGH: {"crf": 18, "preset_override": "slow"},
        ExportQuality.MASTER: {"crf": 14, "preset_override": "veryslow"},
    }

    # Watermark position mapping
    WATERMARK_POSITIONS = {
        "top_left": "10:10",
        "top_center": "(W-w)/2:10",
        "top_right": "W-w-10:10",
        "center": "(W-w)/2:(H-h)/2",
        "bottom_left": "10:H-h-10",
        "bottom_center": "(W-w)/2:H-h-10",
        "bottom_right": "W-w-10:H-h-10",
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize assembly service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()
        self._ffmpeg: Optional[FFmpeg] = None

    async def _get_ffmpeg(self) -> FFmpeg:
        """Get FFmpeg instance, checking availability on first use.

        Returns:
            FFmpeg instance

        Raises:
            FFmpegNotFoundError: If FFmpeg is not available
        """
        if self._ffmpeg is None:
            self._ffmpeg = get_ffmpeg()
            # Validate FFmpeg is available
            await self._ffmpeg.ensure_available()
        return self._ffmpeg

    def _build_color_grade_filter(self, grade: ColorGradeSettings) -> str:
        """Build FFmpeg filter string for color grading.

        Args:
            grade: Color grade settings

        Returns:
            FFmpeg filter string
        """
        filters = []

        # Exposure (brightness adjustment)
        if grade.exposure != 0:
            brightness = grade.exposure * 0.5  # Scale to reasonable range
            filters.append(f"eq=brightness={brightness:.2f}")

        # Contrast
        if grade.contrast != 0:
            contrast = 1 + (grade.contrast / 100)
            filters.append(f"eq=contrast={contrast:.2f}")

        # Saturation
        if grade.saturation != 0:
            saturation = 1 + (grade.saturation / 100)
            filters.append(f"eq=saturation={saturation:.2f}")

        # Temperature (color balance)
        if grade.temperature != 0:
            if grade.temperature > 0:
                # Warm: boost red, reduce blue
                r_gain = 1 + (grade.temperature / 200)
                b_gain = 1 - (grade.temperature / 200)
                filters.append(f"colorbalance=rs={r_gain - 1:.2f}:bs={-(1 - b_gain):.2f}")
            else:
                # Cool: boost blue, reduce red
                r_gain = 1 + (grade.temperature / 200)
                b_gain = 1 - (grade.temperature / 200)
                filters.append(f"colorbalance=rs={r_gain - 1:.2f}:bs={b_gain - 1:.2f}")

        # Vignette
        if grade.vignette_amount > 0:
            amount = grade.vignette_amount / 100
            filters.append(f"vignette=PI*{amount:.2f}")

        # LUT application with intensity blending
        if grade.lut_path and Path(grade.lut_path).exists():
            intensity = grade.lut_intensity / 100
            escaped_lut_path = grade.lut_path.replace(":", "\\:")
            if intensity < 1.0 and intensity > 0:
                # Blend LUT with original using split and blend
                # Split input, apply LUT to one branch, blend with specified intensity
                blend_expr = f"A*{1-intensity:.3f}+B*{intensity:.3f}"
                filters.append(
                    f"split[lut_orig][lut_togr];"
                    f"[lut_togr]lut3d={escaped_lut_path}:interp=trilinear[lut_graded];"
                    f"[lut_orig][lut_graded]blend=all_expr='{blend_expr}'"
                )
            elif intensity >= 1.0:
                # Full LUT intensity - apply directly
                filters.append(f"lut3d={escaped_lut_path}:interp=trilinear")
            # intensity == 0 means no LUT applied, skip

        return ",".join(filters) if filters else ""

    def _build_watermark_filter(
        self,
        watermark_path: str,
        position: str = "bottom_right",
        opacity: float = 0.5,
    ) -> str:
        """Build FFmpeg filter string for watermark overlay.

        Args:
            watermark_path: Path to watermark image
            position: Position preset
            opacity: Opacity (0.0 to 1.0)

        Returns:
            FFmpeg filter string
        """
        pos = self.WATERMARK_POSITIONS.get(position, "W-w-10:H-h-10")
        return f"[1:v]format=rgba,colorchannelmixer=aa={opacity:.2f}[wm];[0:v][wm]overlay={pos}"

    def _build_subtitle_filter(self, subtitle_path: str, style: Optional[str] = None) -> str:
        """Build FFmpeg filter string for subtitle overlay.

        Args:
            subtitle_path: Path to subtitle file (SRT/VTT/ASS)
            style: Optional ASS style string

        Returns:
            FFmpeg filter string
        """
        # Escape path for FFmpeg filter
        escaped_path = subtitle_path.replace(":", "\\:").replace("'", "\\'")

        if style:
            return f"subtitles={escaped_path}:force_style='{style}'"
        return f"subtitles={escaped_path}"

    async def generate_subtitles(
        self,
        project_id: UUID,
        output_path: Path,
    ) -> str:
        """Generate subtitle file from dialogue data.

        Args:
            project_id: Project UUID
            output_path: Output directory for subtitle file

        Returns:
            Path to generated subtitle file
        """
        stmt = (
            select(Project)
            .options(
                selectinload(Project.scenes).selectinload(Scene.shots)
            )
            .where(Project.id == project_id)
        )
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        srt_path = output_path / "subtitles.srt"
        subtitle_index = 1
        current_time = 0.0

        with open(srt_path, "w", encoding="utf-8") as f:
            for scene in sorted(project.scenes, key=lambda s: s.sequence_number):
                for shot in sorted(scene.shots, key=lambda s: s.sequence_number):
                    if shot.dialogue and shot.state == ShotState.APPROVED:
                        # Calculate timing
                        start_time = current_time
                        end_time = current_time + shot.duration_seconds

                        # Format times as SRT timestamps
                        start_str = self._format_srt_time(start_time)
                        end_str = self._format_srt_time(end_time)

                        # Write subtitle entry
                        f.write(f"{subtitle_index}\n")
                        f.write(f"{start_str} --> {end_str}\n")
                        f.write(f"{shot.dialogue}\n\n")

                        subtitle_index += 1

                    current_time += shot.duration_seconds if shot.state == ShotState.APPROVED else 0

        return str(srt_path)

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    async def mix_audio_tracks(
        self,
        video_path: Path,
        audio_tracks: List[Dict[str, Any]],
        output_path: Path,
    ) -> str:
        """Mix multiple audio tracks with the video.

        Args:
            video_path: Path to video file
            audio_tracks: List of audio track configs with path, volume, start_time
            output_path: Output path for mixed video

        Returns:
            Path to output file
        """
        if not audio_tracks:
            return str(video_path)

        # Build FFmpeg command for audio mixing
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]

        # Add audio inputs
        for track in audio_tracks:
            cmd.extend(["-i", track["path"]])

        # Build filter complex for mixing
        filter_parts = []
        mix_inputs = ["[0:a]"]  # Start with video's audio

        for i, track in enumerate(audio_tracks, start=1):
            volume = track.get("volume", 1.0)
            delay = track.get("start_time", 0) * 1000  # Convert to ms

            # Apply delay and volume
            filter_parts.append(f"[{i}:a]adelay={delay:.0f}|{delay:.0f},volume={volume:.2f}[a{i}]")
            mix_inputs.append(f"[a{i}]")

        # Combine with amix
        filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest[aout]")

        filter_complex = ";".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ])

        try:
            # Ensure FFmpeg is available
            ffmpeg = await self._get_ffmpeg()

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                raise FFmpegExecutionError(
                    f"Audio mixing failed: {error_msg}",
                    return_code=process.returncode,
                    stderr=error_msg,
                )

        except FFmpegNotFoundError:
            raise  # Re-raise FFmpeg not found errors
        except FFmpegError:
            raise  # Re-raise FFmpeg execution errors
        except Exception as e:
            raise FFmpegExecutionError(f"Audio mixing failed: {e}")

        return str(output_path)

    async def apply_transitions(
        self,
        shot_paths: List[str],
        transitions: List[Dict[str, Any]],
        output_path: Path,
    ) -> str:
        """Apply transitions between shots.

        Args:
            shot_paths: List of shot video paths
            transitions: List of transition configs (type, duration)
            output_path: Output path

        Returns:
            Path to output file
        """
        if len(shot_paths) < 2 or not transitions:
            # No transitions needed, use concat
            return await self._concat_videos(shot_paths, output_path)

        # Build complex filter for transitions
        filter_parts = []
        inputs = ""

        for i, path in enumerate(shot_paths):
            inputs += f"-i {path} "

        # Build xfade chain
        current_output = "[0:v]"
        offset = 0.0

        for i, (path, trans) in enumerate(zip(shot_paths[1:], transitions)):
            trans_type = trans.get("type", "fade")
            duration = trans.get("duration", 500) / 1000  # ms to seconds

            # Get video duration (approximate)
            # In production, use ffprobe
            video_duration = 3.0  # Default

            offset += video_duration - duration

            next_input = f"[{i + 1}:v]"
            output_label = f"[v{i}]" if i < len(shot_paths) - 2 else "[vout]"

            # Map transition types to xfade transitions
            xfade_type = self._map_transition_type(trans_type)

            filter_parts.append(
                f"{current_output}{next_input}xfade=transition={xfade_type}:"
                f"duration={duration}:offset={offset}{output_label}"
            )

            current_output = output_label if i < len(shot_paths) - 2 else ""

        filter_complex = ";".join(filter_parts)

        cmd = f"ffmpeg -y {inputs}-filter_complex \"{filter_complex}\" -map \"[vout]\" {output_path}"

        try:
            # Ensure FFmpeg is available first
            await self._get_ffmpeg()

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.warning(f"Transition failed, falling back to concat: {error_msg}")
                return await self._concat_videos(shot_paths, output_path)

        except FFmpegNotFoundError:
            raise  # Re-raise - FFmpeg is required
        except Exception as e:
            logger.warning(f"Transition error, falling back to concat: {e}")
            return await self._concat_videos(shot_paths, output_path)

        return str(output_path)

    def _map_transition_type(self, trans_type: str) -> str:
        """Map our transition types to FFmpeg xfade transitions."""
        mapping = {
            "fade": "fade",
            "dissolve": "dissolve",
            "wipe_left": "wipeleft",
            "wipe_right": "wiperight",
            "wipe_up": "wipeup",
            "wipe_down": "wipedown",
            "slide_left": "slideleft",
            "slide_right": "slideright",
            "zoom_in": "zoomin",
            "zoom_out": "fadefast",
            "blur": "smoothleft",
            "flash": "fadewhite",
        }
        return mapping.get(trans_type, "fade")

    async def _concat_videos(self, video_paths: List[str], output_path: Path) -> str:
        """Concatenate videos without transitions.

        Args:
            video_paths: List of video file paths to concatenate
            output_path: Output file path

        Returns:
            Path to output file

        Raises:
            FFmpegNotFoundError: If FFmpeg is not available
            FFmpegExecutionError: If concatenation fails
            ValueError: If no valid video paths provided
        """
        # Filter to existing files only
        existing_paths = [p for p in video_paths if Path(p).exists()]
        if not existing_paths:
            raise ValueError("No valid video files to concatenate")

        concat_file = output_path.parent / "concat.txt"

        try:
            with open(concat_file, "w") as f:
                for path in existing_paths:
                    f.write(f"file '{path}'\n")

            # Use FFmpeg utility for concatenation
            ffmpeg = await self._get_ffmpeg()
            await ffmpeg.concatenate_videos(
                input_paths=[Path(p) for p in existing_paths],
                output_path=output_path,
            )

            return str(output_path)

        finally:
            concat_file.unlink(missing_ok=True)

    async def get_timeline(self, project_id: UUID) -> Timeline:
        """Get the project timeline.

        Args:
            project_id: Project UUID

        Returns:
            Timeline with scenes and shots
        """
        stmt = (
            select(Project)
            .options(
                selectinload(Project.scenes).selectinload(Scene.shots)
            )
            .where(Project.id == project_id)
        )
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        scenes_data = []
        total_duration = 0.0
        total_shots = 0

        for scene in sorted(project.scenes, key=lambda s: s.sequence_number):
            approved_shots = [
                s for s in scene.shots if s.state == ShotState.APPROVED
            ]

            scene_duration = sum(s.duration_seconds for s in approved_shots)
            total_duration += scene_duration
            total_shots += len(approved_shots)

            scenes_data.append({
                "id": str(scene.id),
                "scene_number": scene.scene_number,
                "heading": scene.heading,
                "location": scene.location,
                "time_of_day": scene.time_of_day.value,
                "duration_seconds": scene_duration,
                "shot_count": len(approved_shots),
                "all_shots_approved": len(approved_shots) == len(scene.shots),
                "start_time": total_duration - scene_duration,
                "shots": [
                    {
                        "id": str(shot.id),
                        "shot_number": shot.shot_number,
                        "shot_type": shot.shot_type.value,
                        "duration_seconds": shot.duration_seconds,
                        "output_path": shot.output_video_path,
                        "thumbnail_path": shot.output_thumbnail_path,
                        "state": shot.state.value,
                    }
                    for shot in sorted(approved_shots, key=lambda s: s.sequence_number)
                ],
            })

        return Timeline(
            project_id=str(project_id),
            total_duration=total_duration,
            scene_count=len(project.scenes),
            shot_count=total_shots,
            scenes=scenes_data,
        )

    async def assemble_scene(
        self,
        scene_id: UUID,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> SceneRender:
        """Assemble approved shots into a scene video.

        Args:
            scene_id: Scene UUID
            progress_callback: Optional progress callback

        Returns:
            SceneRender with output path
        """
        stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.id == scene_id)
        )
        result = await self.session.execute(stmt)
        scene = result.scalar_one_or_none()

        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        # Get approved shots
        approved_shots = [
            s for s in scene.shots
            if s.state == ShotState.APPROVED and s.output_video_path
        ]

        if not approved_shots:
            raise ValueError(f"Scene {scene_id} has no approved shots")

        sorted_shots = sorted(approved_shots, key=lambda s: s.sequence_number)

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="assembling",
                    percent=10,
                    message=f"Assembling scene {scene.scene_number}",
                )
            )

        # Create output directory
        output_dir = self.settings.output_dir / "scenes" / str(scene_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "scene.mp4"

        # Build concat list
        concat_file = output_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for shot in sorted_shots:
                shot_path = self.settings.output_dir / shot.output_video_path
                if shot_path.exists():
                    f.write(f"file '{shot_path.absolute()}'\n")

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="encoding",
                    percent=50,
                    message="Encoding scene video",
                )
            )

        # Use FFmpeg to concatenate
        try:
            ffmpeg = await self._get_ffmpeg()

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                raise FFmpegExecutionError(
                    f"Scene assembly failed: {error_msg}",
                    return_code=process.returncode,
                    stderr=error_msg,
                )

        finally:
            # Clean up concat file
            concat_file.unlink(missing_ok=True)

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="complete",
                    percent=100,
                    message="Scene assembled",
                )
            )

        # Calculate duration
        total_duration = sum(s.duration_seconds for s in sorted_shots)

        # Store scene render path
        scene.rendered_video_path = f"scenes/{scene_id}/scene.mp4"
        await self.session.commit()

        return SceneRender(
            scene_id=str(scene_id),
            scene_number=scene.scene_number,
            output_path=str(output_path),
            duration_seconds=total_duration,
            shot_count=len(sorted_shots),
        )

    async def assemble_movie(
        self,
        project_id: UUID,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Assemble all scenes into the complete movie.

        Args:
            project_id: Project UUID
            progress_callback: Optional progress callback

        Returns:
            Path to assembled movie
        """
        stmt = (
            select(Project)
            .options(
                selectinload(Project.scenes).selectinload(Scene.shots)
            )
            .where(Project.id == project_id)
        )
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Update project state
        project.state = ProjectState.ASSEMBLY_IN_PROGRESS
        await self.session.commit()

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="preparing",
                    percent=5,
                    message="Preparing assembly",
                    total_scenes=len(project.scenes),
                )
            )

        # Assemble each scene
        scene_renders: List[SceneRender] = []
        sorted_scenes = sorted(project.scenes, key=lambda s: s.sequence_number)

        for i, scene in enumerate(sorted_scenes):
            if progress_callback:
                await progress_callback(
                    AssemblyProgress(
                        stage="scene_assembly",
                        percent=10 + (i * 60 / len(sorted_scenes)),
                        message=f"Assembling scene {scene.scene_number}",
                        current_scene=i + 1,
                        total_scenes=len(sorted_scenes),
                    )
                )

            try:
                render = await self.assemble_scene(scene.id)
                scene_renders.append(render)
            except ValueError as e:
                logger.warning(f"Skipping scene {scene.id}: {e}")
                continue

        if not scene_renders:
            raise ValueError("No scenes could be assembled")

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="concatenating",
                    percent=75,
                    message="Concatenating scenes",
                )
            )

        # Create output directory
        output_dir = self.settings.output_dir / "movies" / str(project_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "movie.mp4"

        # Build concat list
        concat_file = output_dir / "concat.txt"
        valid_scene_paths = [
            render.output_path for render in scene_renders
            if Path(render.output_path).exists()
        ]

        if not valid_scene_paths:
            raise ValueError("No valid scene renders to assemble")

        with open(concat_file, "w") as f:
            for path in valid_scene_paths:
                f.write(f"file '{path}'\n")

        # Use FFmpeg to concatenate
        try:
            ffmpeg = await self._get_ffmpeg()

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                raise FFmpegExecutionError(
                    f"Movie assembly failed: {error_msg}",
                    return_code=process.returncode,
                    stderr=error_msg,
                )

        finally:
            # Clean up
            concat_file.unlink(missing_ok=True)

        # Update project state
        project.state = ProjectState.COMPLETE
        await self.session.commit()

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="complete",
                    percent=100,
                    message="Movie assembled successfully",
                )
            )

        logger.info(f"Assembled movie for project {project_id}: {output_path}")

        return str(output_path)

    async def export_movie(
        self,
        project_id: UUID,
        settings: ExportSettings,
        output_filename: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ExportResult:
        """Export the assembled movie with specified settings.

        Args:
            project_id: Project UUID
            settings: Export settings
            output_filename: Optional custom filename
            progress_callback: Optional progress callback

        Returns:
            ExportResult with output path
        """
        # Get project for metadata
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Create export history record
        export_record = ExportHistory(
            project_id=project_id,
            format=settings.format.value,
            quality=settings.quality.value,
            resolution=settings.resolution,
            frame_rate=settings.frame_rate,
            video_bitrate=settings.video_bitrate,
            audio_bitrate=settings.audio_bitrate,
            status=ExportHistoryStatus.PENDING.value,
            include_subtitles=settings.include_subtitles,
            include_audio=settings.include_audio,
            has_watermark=settings.watermark is not None,
            has_color_grade=settings.color_grade is not None,
            export_settings={
                "format": settings.format.value,
                "quality": settings.quality.value,
                "resolution": settings.resolution,
                "frame_rate": settings.frame_rate,
                "video_bitrate": settings.video_bitrate,
                "audio_bitrate": settings.audio_bitrate,
                "watermark_position": settings.watermark_position if settings.watermark else None,
            },
        )
        self.session.add(export_record)
        await self.session.commit()
        await self.session.refresh(export_record)

        start_time = datetime.now(timezone.utc)
        export_record.started_at = start_time
        export_record.status = ExportHistoryStatus.IN_PROGRESS.value
        await self.session.commit()

        # First assemble if needed
        movie_path = self.settings.output_dir / "movies" / str(project_id) / "movie.mp4"

        try:
            if not movie_path.exists():
                if progress_callback:
                    await progress_callback(
                        AssemblyProgress(
                            stage="assembling",
                            percent=5,
                            message="Assembling movie first",
                        )
                    )
                await self.assemble_movie(project_id)

            if progress_callback:
                await progress_callback(
                    AssemblyProgress(
                        stage="exporting",
                        percent=20,
                        message=f"Exporting as {settings.format.value}",
                    )
                )

            export_record.status = ExportHistoryStatus.ENCODING.value
            export_record.progress_percent = 20.0
            export_record.progress_message = "Encoding video"
            await self.session.commit()

        except Exception as e:
            # Update export record with failure
            export_record.status = ExportHistoryStatus.FAILED.value
            export_record.error_message = str(e)
            export_record.error_code = "ASSEMBLY_FAILED"
            export_record.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise

        # Create export directory
        export_dir = self.settings.output_dir / "exports" / str(project_id)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Determine output filename
        codec_settings = self.CODEC_SETTINGS[settings.format]
        container = codec_settings["container"]

        if output_filename:
            if not output_filename.endswith(f".{container}"):
                output_filename = f"{output_filename}.{container}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = project.name.replace(" ", "_").replace("/", "-")[:50]
            output_filename = f"{safe_name}_{timestamp}.{container}"

        output_path = export_dir / output_filename

        # Build FFmpeg command
        quality = self.QUALITY_SETTINGS[settings.quality]
        width, height = settings.resolution.split("x")

        # Generate subtitles if requested
        subtitle_file = None
        if settings.include_subtitles:
            if progress_callback:
                await progress_callback(
                    AssemblyProgress(
                        stage="subtitles",
                        percent=25,
                        message="Generating subtitles",
                    )
                )
            subtitle_file = await self.generate_subtitles(project_id, export_dir)

        # Build video filter chain
        video_filters = [f"scale={width}:{height}"]

        # Add color grading
        if settings.color_grade:
            grade_filter = self._build_color_grade_filter(settings.color_grade)
            if grade_filter:
                video_filters.append(grade_filter)

        # Add subtitles
        if subtitle_file and Path(subtitle_file).exists():
            subtitle_filter = self._build_subtitle_filter(subtitle_file)
            video_filters.append(subtitle_filter)

        try:
            cmd = ["ffmpeg", "-y", "-i", str(movie_path)]

            # Add watermark input if specified
            watermark_path = None
            if settings.watermark:
                watermark_path = self.settings.output_dir / "assets" / settings.watermark
                if not watermark_path.exists():
                    # Check if it's an absolute path
                    watermark_path = Path(settings.watermark)

                if watermark_path.exists():
                    cmd.extend(["-i", str(watermark_path)])

            cmd.extend(["-c:v", codec_settings["video_codec"]])

            # Add codec-specific options
            if codec_settings.get("profile"):
                cmd.extend(["-profile:v", codec_settings["profile"]])

            preset = quality.get("preset_override") or codec_settings.get("preset")
            if preset:
                cmd.extend(["-preset", preset])

            # Add quality settings
            if "crf" in quality:
                cmd.extend(["-crf", str(quality["crf"])])

            # Build complex filter if watermark is used
            if watermark_path and watermark_path.exists():
                watermark_filter = self._build_watermark_filter(
                    str(watermark_path),
                    settings.watermark_position,
                    settings.watermark_opacity,
                )
                # Combine with video filters
                combined_filter = f"{watermark_filter};[out]{','.join(video_filters)}[final]"
                cmd.extend(["-filter_complex", combined_filter, "-map", "[final]"])
            else:
                # Simple video filter chain
                cmd.extend(["-vf", ",".join(video_filters)])

            # Add frame rate
            cmd.extend(["-r", str(settings.frame_rate)])

            # Add bitrate
            cmd.extend(["-b:v", settings.video_bitrate])

            # Audio settings
            if settings.include_audio:
                cmd.extend([
                    "-c:a", settings.audio_codec,
                    "-b:a", settings.audio_bitrate,
                ])
            else:
                cmd.extend(["-an"])

            cmd.append(str(output_path))

            if progress_callback:
                await progress_callback(
                    AssemblyProgress(
                        stage="encoding",
                        percent=50,
                        message="Encoding video",
                    )
                )

            # Ensure FFmpeg is available
            ffmpeg = await self._get_ffmpeg()

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown FFmpeg error"
                raise FFmpegExecutionError(
                    f"Export encoding failed: {error_msg}",
                    return_code=process.returncode,
                    stderr=error_msg,
                )

        except FFmpegNotFoundError as e:
            # Update export record with failure
            export_record.status = ExportHistoryStatus.FAILED.value
            export_record.error_message = str(e)
            export_record.error_code = "FFMPEG_NOT_FOUND"
            export_record.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise
        except FFmpegError as e:
            # Update export record with failure
            export_record.status = ExportHistoryStatus.FAILED.value
            export_record.error_message = str(e)
            export_record.error_code = "FFMPEG_ERROR"
            export_record.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise

        # Verify export with progress update
        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="verifying",
                    percent=90,
                    message="Verifying exported video",
                )
            )

        export_record.status = ExportHistoryStatus.VERIFYING.value
        export_record.progress_percent = 90.0
        export_record.progress_message = "Verifying exported video"
        await self.session.commit()

        # Verify the exported file
        verification_result = await self._verify_export(output_path, settings)

        if not verification_result["valid"]:
            logger.error(f"Export verification failed: {verification_result['error']}")
            # Update export record with verification failure
            export_record.status = ExportHistoryStatus.FAILED.value
            export_record.error_message = f"Verification failed: {verification_result['error']}"
            export_record.error_code = "VERIFICATION_FAILED"
            export_record.completed_at = datetime.now(timezone.utc)
            export_record.verification_result = verification_result
            await self.session.commit()
            return ExportResult(
                success=False,
                error_message=f"Export verification failed: {verification_result['error']}",
                metadata=verification_result,
            )

        # Get verified file info
        file_size = verification_result.get("file_size_bytes", 0)
        actual_duration = verification_result.get("duration_seconds")
        actual_resolution = verification_result.get("resolution")

        # Calculate encoding duration
        end_time = datetime.now(timezone.utc)
        encoding_duration = (end_time - start_time).total_seconds()

        # Update export record with success
        export_record.status = ExportHistoryStatus.COMPLETED.value
        export_record.progress_percent = 100.0
        export_record.progress_message = "Export complete"
        export_record.completed_at = end_time
        export_record.encoding_duration_seconds = encoding_duration
        export_record.output_filename = output_filename
        export_record.output_path = str(output_path)
        export_record.file_size_bytes = file_size
        export_record.actual_duration_seconds = actual_duration
        export_record.actual_resolution = actual_resolution
        export_record.actual_fps = verification_result.get("fps")
        export_record.video_codec = verification_result.get("video_codec")
        export_record.audio_codec = verification_result.get("audio_codec")
        export_record.verification_result = verification_result
        await self.session.commit()

        # Update project state
        project.state = ProjectState.EXPORTED
        await self.session.commit()

        # Create asset record with verified metadata
        asset = Asset(
            asset_type=AssetType.FINAL_MOVIE,
            status=AssetStatus.READY,
            filename=output_filename,
            file_path=f"exports/{project_id}/{output_filename}",
            file_size_bytes=file_size,
            mime_type=f"video/{container}",
            generation_metadata={
                "format": settings.format.value,
                "quality": settings.quality.value,
                "resolution": actual_resolution or settings.resolution,
                "frame_rate": verification_result.get("fps", settings.frame_rate),
                "duration_seconds": actual_duration,
                "video_codec": verification_result.get("video_codec"),
                "audio_codec": verification_result.get("audio_codec"),
                "exported_at": end_time.isoformat(),
                "verified": True,
                "export_history_id": str(export_record.id),
            },
        )
        self.session.add(asset)
        await self.session.commit()

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="complete",
                    percent=100,
                    message="Export complete and verified",
                )
            )

        logger.info(f"Exported and verified movie: {output_path}")

        return ExportResult(
            success=True,
            output_path=str(output_path),
            file_size_bytes=file_size,
            duration_seconds=actual_duration,
            metadata={
                "format": settings.format.value,
                "quality": settings.quality.value,
                "resolution": actual_resolution or settings.resolution,
                "fps": verification_result.get("fps"),
                "video_codec": verification_result.get("video_codec"),
                "audio_codec": verification_result.get("audio_codec"),
                "verified": True,
                "export_history_id": str(export_record.id),
                "encoding_time_seconds": encoding_duration,
            },
        )

    async def _verify_export(
        self,
        output_path: Path,
        settings: ExportSettings,
    ) -> Dict[str, Any]:
        """Verify an exported video file is valid.

        Args:
            output_path: Path to exported video
            settings: Export settings used

        Returns:
            Verification result dict with 'valid' key
        """
        result: Dict[str, Any] = {"valid": False}

        # Check file exists
        if not output_path.exists():
            result["error"] = "Output file does not exist"
            return result

        # Check file size
        file_size = output_path.stat().st_size
        result["file_size_bytes"] = file_size

        if file_size < 1000:  # Less than 1KB is suspicious
            result["error"] = f"Output file too small ({file_size} bytes)"
            return result

        # Get video info using FFmpeg
        try:
            ffmpeg = await self._get_ffmpeg()
            video_info = await ffmpeg.get_video_info(output_path)

            result["duration_seconds"] = video_info.duration
            result["resolution"] = f"{video_info.width}x{video_info.height}"
            result["fps"] = video_info.fps
            result["video_codec"] = video_info.codec
            result["audio_codec"] = video_info.audio_codec
            result["bit_rate"] = video_info.bit_rate

            # Verify duration is reasonable (at least 0.5 seconds)
            if video_info.duration < 0.5:
                result["error"] = f"Video duration too short ({video_info.duration:.2f}s)"
                return result

            # Verify resolution matches expected (with some tolerance)
            expected_width, expected_height = map(int, settings.resolution.split("x"))
            if abs(video_info.width - expected_width) > 10 or abs(video_info.height - expected_height) > 10:
                logger.warning(
                    f"Resolution mismatch: expected {settings.resolution}, "
                    f"got {video_info.width}x{video_info.height}"
                )
                # Not a failure, just a warning

            result["valid"] = True
            return result

        except FFmpegNotFoundError:
            # Can't verify without FFmpeg, but file exists and has content
            logger.warning("FFmpeg not available for verification, assuming valid")
            result["valid"] = True
            result["error"] = None
            return result

        except Exception as e:
            result["error"] = f"Verification failed: {str(e)}"
            return result

    async def get_export_history(self, project_id: UUID) -> List[Dict[str, Any]]:
        """Get export history for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of export records with detailed metadata
        """
        stmt = (
            select(ExportHistory)
            .where(ExportHistory.project_id == project_id)
            .order_by(ExportHistory.created_at.desc())
        )

        result = await self.session.execute(stmt)
        exports = result.scalars().all()

        return [export.to_dict() for export in exports]

    async def get_export_by_id(self, export_id: UUID) -> Optional[ExportHistory]:
        """Get a specific export record by ID.

        Args:
            export_id: Export history UUID

        Returns:
            ExportHistory record or None
        """
        stmt = select(ExportHistory).where(ExportHistory.id == export_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_export(self, export_id: UUID) -> bool:
        """Delete an export record and its file.

        Args:
            export_id: Export history UUID

        Returns:
            True if deleted, False if not found
        """
        export = await self.get_export_by_id(export_id)
        if not export:
            return False

        # Delete the file if it exists
        if export.output_path:
            output_path = Path(export.output_path)
            if output_path.exists():
                output_path.unlink()
                logger.info(f"Deleted export file: {output_path}")

        # Delete the record
        await self.session.delete(export)
        await self.session.commit()
        logger.info(f"Deleted export record: {export_id}")

        return True

    async def get_export_stats(self, project_id: UUID) -> Dict[str, Any]:
        """Get export statistics for a project.

        Args:
            project_id: Project UUID

        Returns:
            Statistics about exports
        """
        stmt = (
            select(ExportHistory)
            .where(ExportHistory.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        exports = result.scalars().all()

        if not exports:
            return {
                "total_exports": 0,
                "completed_exports": 0,
                "failed_exports": 0,
                "total_file_size_bytes": 0,
                "total_encoding_time_seconds": 0,
                "average_encoding_time_seconds": 0,
            }

        completed = [e for e in exports if e.status == ExportHistoryStatus.COMPLETED.value]
        failed = [e for e in exports if e.status == ExportHistoryStatus.FAILED.value]

        total_size = sum(e.file_size_bytes or 0 for e in completed)
        total_encoding_time = sum(e.encoding_duration_seconds or 0 for e in completed)
        avg_encoding_time = total_encoding_time / len(completed) if completed else 0

        return {
            "total_exports": len(exports),
            "completed_exports": len(completed),
            "failed_exports": len(failed),
            "pending_exports": len([e for e in exports if e.status == ExportHistoryStatus.PENDING.value]),
            "in_progress_exports": len([e for e in exports if e.status in (
                ExportHistoryStatus.IN_PROGRESS.value,
                ExportHistoryStatus.ENCODING.value,
                ExportHistoryStatus.VERIFYING.value,
            )]),
            "total_file_size_bytes": total_size,
            "total_file_size_display": self._format_file_size(total_size),
            "total_encoding_time_seconds": total_encoding_time,
            "average_encoding_time_seconds": avg_encoding_time,
            "formats_used": list(set(e.format for e in completed)),
            "qualities_used": list(set(e.quality for e in completed)),
        }

    def _format_file_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    async def get_export_formats(self) -> List[Dict[str, Any]]:
        """Get available export formats.

        Returns:
            List of format options
        """
        format_info = {
            ExportFormat.MP4_H264: {
                "name": "MP4 (H.264)",
                "description": "Universal compatibility, good quality",
                "recommended": True,
            },
            ExportFormat.MP4_H265: {
                "name": "MP4 (H.265/HEVC)",
                "description": "Better compression, newer devices",
                "recommended": False,
            },
            ExportFormat.MOV_PRORES: {
                "name": "MOV (ProRes)",
                "description": "Professional editing, large files",
                "recommended": False,
            },
            ExportFormat.WEBM_VP9: {
                "name": "WebM (VP9)",
                "description": "Web streaming, open format",
                "recommended": False,
            },
            ExportFormat.MKV_H264: {
                "name": "MKV (H.264)",
                "description": "Flexible container, good for archival",
                "recommended": False,
            },
        }

        return [
            {
                "value": fmt.value,
                "name": info["name"],
                "description": info["description"],
                "recommended": info["recommended"],
            }
            for fmt, info in format_info.items()
        ]

    async def get_quality_presets(self) -> List[Dict[str, Any]]:
        """Get available quality presets.

        Returns:
            List of quality options
        """
        quality_info = {
            ExportQuality.DRAFT: {
                "name": "Draft",
                "description": "Fast export for preview",
                "file_size": "Small",
            },
            ExportQuality.STANDARD: {
                "name": "Standard",
                "description": "Balanced quality and size",
                "file_size": "Medium",
            },
            ExportQuality.HIGH: {
                "name": "High",
                "description": "High quality for distribution",
                "file_size": "Large",
            },
            ExportQuality.MASTER: {
                "name": "Master",
                "description": "Maximum quality, slow export",
                "file_size": "Very Large",
            },
        }

        return [
            {
                "value": qual.value,
                "name": info["name"],
                "description": info["description"],
                "file_size": info["file_size"],
            }
            for qual, info in quality_info.items()
        ]


async def get_assembly_service(session: AsyncSession) -> AssemblyService:
    """Factory function for AssemblyService."""
    return AssemblyService(session)
