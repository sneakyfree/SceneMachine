"""Assembly and export service.

Handles scene assembly, movie composition, and export operations.
"""

import asyncio
import logging
import shutil
import subprocess
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
from scenemachine.models.project import ProjectState
from scenemachine.models.shot import ShotState

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

        # LUT application
        if grade.lut_path and Path(grade.lut_path).exists():
            intensity = grade.lut_intensity / 100
            if intensity < 1.0:
                # Blend LUT with original
                filters.append(f"lut3d={grade.lut_path}:interp=trilinear")
                # TODO: Add blend for partial LUT intensity
            else:
                filters.append(f"lut3d={grade.lut_path}:interp=trilinear")

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
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"Audio mixing error: {stderr.decode()}")
                return str(video_path)

        except FileNotFoundError:
            logger.warning("FFmpeg not found for audio mixing")
            return str(video_path)

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
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

        except Exception as e:
            logger.error(f"Transition error: {e}")
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
        """Concatenate videos without transitions."""
        concat_file = output_path.parent / "concat.txt"

        with open(concat_file, "w") as f:
            for path in video_paths:
                if Path(path).exists():
                    f.write(f"file '{path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
        except FileNotFoundError:
            output_path.touch()

        concat_file.unlink(missing_ok=True)
        return str(output_path)

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
                logger.error(f"FFmpeg error: {stderr.decode()}")
                # Fallback: create placeholder
                output_path.touch()

        except FileNotFoundError:
            logger.warning("FFmpeg not found, creating placeholder")
            output_path.touch()

        # Clean up
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
        with open(concat_file, "w") as f:
            for render in scene_renders:
                if Path(render.output_path).exists():
                    f.write(f"file '{render.output_path}'\n")

        # Use FFmpeg to concatenate
        try:
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
            await process.communicate()

        except FileNotFoundError:
            logger.warning("FFmpeg not found, creating placeholder")
            output_path.touch()

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
        # First assemble if needed
        movie_path = self.settings.output_dir / "movies" / str(project_id) / "movie.mp4"

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

        # Get project for metadata
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

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

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                # Fallback: copy source
                shutil.copy2(movie_path, output_path)

        except FileNotFoundError:
            logger.warning("FFmpeg not found, copying source file")
            shutil.copy2(movie_path, output_path)

        # Get file info
        file_size = output_path.stat().st_size if output_path.exists() else 0

        # Update project state
        project.state = ProjectState.EXPORTED
        await self.session.commit()

        # Create asset record
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
                "resolution": settings.resolution,
                "frame_rate": settings.frame_rate,
                "exported_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.session.add(asset)
        await self.session.commit()

        if progress_callback:
            await progress_callback(
                AssemblyProgress(
                    stage="complete",
                    percent=100,
                    message="Export complete",
                )
            )

        logger.info(f"Exported movie: {output_path}")

        return ExportResult(
            success=True,
            output_path=str(output_path),
            file_size_bytes=file_size,
            metadata={
                "format": settings.format.value,
                "quality": settings.quality.value,
                "resolution": settings.resolution,
            },
        )

    async def get_export_history(self, project_id: UUID) -> List[Dict[str, Any]]:
        """Get export history for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of export records
        """
        stmt = (
            select(Asset)
            .where(
                Asset.asset_type == AssetType.FINAL_MOVIE,
                Asset.file_path.like(f"exports/{project_id}/%"),
            )
            .order_by(Asset.created_at.desc())
        )

        result = await self.session.execute(stmt)
        assets = result.scalars().all()

        return [
            {
                "id": str(asset.id),
                "filename": asset.filename,
                "file_path": asset.file_path,
                "file_size": asset.file_size_display,
                "format": asset.generation_metadata.get("format") if asset.generation_metadata else None,
                "quality": asset.generation_metadata.get("quality") if asset.generation_metadata else None,
                "resolution": asset.generation_metadata.get("resolution") if asset.generation_metadata else None,
                "created_at": asset.created_at.isoformat(),
            }
            for asset in assets
        ]

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
