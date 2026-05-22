"""Lip Sync Job Model for tracking lip sync processing jobs."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class LipsyncJobStatus(StrEnum):
    """Status of a lip sync job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LipsyncJob(Base, UUIDMixin, TimestampMixin):
    """
    A lip sync processing job.

    Tracks the status and progress of lip sync operations, allowing
    asynchronous processing with progress updates.

    Attributes:
        shot_id: Optional foreign key to the shot being processed
        video_asset_id: Foreign key to the video asset
        audio_asset_id: Foreign key to the audio asset
        output_asset_id: Foreign key to the generated output (when complete)
        status: Current job status
        progress_percent: Progress from 0.0 to 100.0
        progress_message: Human-readable progress message
        error_message: Error details if failed
        provider: Lip sync provider used (mock, rhubarb, wav2lip, etc.)
        completed_at: Timestamp when job completed or failed
    """

    __tablename__ = "lipsync_jobs"

    # Optional shot association
    shot_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Required asset associations
    video_asset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audio_asset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Output asset (created when job completes)
    output_asset_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Job status and progress
    status: Mapped[LipsyncJobStatus] = mapped_column(
        SAEnum(LipsyncJobStatus, name="lipsync_job_status"),
        default=LipsyncJobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    progress_message: Mapped[str] = mapped_column(
        String(255),
        default="Job queued",
        nullable=False,
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provider information
    provider: Mapped[str] = mapped_column(
        String(50),
        default="mock",
        nullable=False,
    )

    # Output path (temporary until asset is created)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Completion timestamp
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    @property
    def is_finished(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (
            LipsyncJobStatus.COMPLETED,
            LipsyncJobStatus.FAILED,
            LipsyncJobStatus.CANCELLED,
        )

    @property
    def is_active(self) -> bool:
        """Check if job is currently processing."""
        return self.status in (
            LipsyncJobStatus.QUEUED,
            LipsyncJobStatus.PROCESSING,
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<LipsyncJob(id={self.id}, "
            f"status={self.status.value}, "
            f"progress={self.progress_percent}%)>"
        )
