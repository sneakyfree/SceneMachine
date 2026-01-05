"""Export history model.

Tracks all exports for projects with detailed metadata and status.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin, JSONType


class ExportStatus(str, Enum):
    """Export status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ENCODING = "encoding"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, Enum):
    """Supported export formats."""

    MP4_H264 = "mp4_h264"
    MP4_H265 = "mp4_h265"
    MOV_PRORES = "mov_prores"
    WEBM_VP9 = "webm_vp9"
    MKV_H264 = "mkv_h264"


class ExportQuality(str, Enum):
    """Export quality presets."""

    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    MASTER = "master"


class ExportHistory(Base, UUIDMixin, TimestampMixin):
    """Export history record.

    Tracks individual export operations with full metadata,
    timing, and status information.
    """

    __tablename__ = "export_history"

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Export settings
    format: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ExportFormat.MP4_H264.value,
    )
    quality: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ExportQuality.HIGH.value,
    )
    resolution: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1920x1080",
    )
    frame_rate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
    )
    video_bitrate: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    audio_bitrate: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ExportStatus.PENDING.value,
        index=True,
    )
    progress_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    progress_message: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Output information
    output_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    output_path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Verified metadata from FFmpeg probe
    actual_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    actual_resolution: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    actual_fps: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    video_codec: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    audio_codec: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    encoding_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Additional metadata
    export_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
    )
    verification_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Include subtitles, watermark, color grade info
    include_subtitles: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    include_audio: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )
    has_watermark: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    has_color_grade: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    # Relationship back to project
    project = relationship("Project", back_populates="export_history")

    @property
    def is_complete(self) -> bool:
        """Check if export is complete."""
        return self.status == ExportStatus.COMPLETED.value

    @property
    def is_failed(self) -> bool:
        """Check if export failed."""
        return self.status == ExportStatus.FAILED.value

    @property
    def encoding_time_display(self) -> str:
        """Human-readable encoding time."""
        if not self.encoding_duration_seconds:
            return "N/A"
        mins, secs = divmod(int(self.encoding_duration_seconds), 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    @property
    def file_size_display(self) -> str:
        """Human-readable file size."""
        if not self.file_size_bytes:
            return "N/A"

        size = self.file_size_bytes
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def duration_display(self) -> str:
        """Human-readable duration."""
        if not self.actual_duration_seconds:
            return "N/A"

        total_secs = int(self.actual_duration_seconds)
        hours, remainder = divmod(total_secs, 3600)
        mins, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "format": self.format,
            "quality": self.quality,
            "resolution": self.actual_resolution or self.resolution,
            "frame_rate": self.actual_fps or self.frame_rate,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "progress_message": self.progress_message,
            "output_filename": self.output_filename,
            "output_path": self.output_path,
            "file_size_bytes": self.file_size_bytes,
            "file_size_display": self.file_size_display,
            "duration_seconds": self.actual_duration_seconds,
            "duration_display": self.duration_display,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "encoding_time": self.encoding_time_display,
            "error_message": self.error_message,
            "include_subtitles": self.include_subtitles,
            "include_audio": self.include_audio,
            "has_watermark": self.has_watermark,
            "has_color_grade": self.has_color_grade,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }
