"""GenerationJob model - tracks video generation tasks."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .shot import Shot


class JobStatus(str, Enum):
    """Generation job status."""

    PENDING = "pending"  # Waiting in queue
    PREPARING = "preparing"  # Preparing inputs
    RUNNING = "running"  # Generation in progress
    POST_PROCESSING = "post_processing"  # Post-processing outputs
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Cancelled by user
    TIMEOUT = "timeout"  # Exceeded time limit


class JobProvider(str, Enum):
    """Generation provider types."""

    LOCAL = "local"  # Local GPU execution
    SCENEMACHINE = "scenemachine"  # SceneMachine cloud
    REPLICATE = "replicate"  # Replicate.com
    RUNPOD = "runpod"  # RunPod
    MODAL = "modal"  # Modal.com
    FAL = "fal"  # Fal.ai
    CUSTOM = "custom"  # User-defined provider


class GenerationJob(Base, UUIDMixin, TimestampMixin):
    """A generation job for producing video content.

    Tracks the lifecycle of a single generation attempt including
    provider, timing, cost, and results.
    """

    __tablename__ = "generation_jobs"

    # Foreign key to shot
    shot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Job identification
    job_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Attempt number

    # Status
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"),
        default=JobStatus.PENDING,
        nullable=False,
    )

    # Provider information
    provider: Mapped[JobProvider] = mapped_column(
        SAEnum(JobProvider, name="job_provider"),
        nullable=False,
    )
    provider_job_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # External job ID

    # Model information
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Generation parameters
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure:
    # {
    #     "prompt": "...",
    #     "negative_prompt": "...",
    #     "seed": 12345,
    #     "steps": 50,
    #     "cfg_scale": 7.5,
    #     "width": 1920,
    #     "height": 1080,
    #     "fps": 24,
    #     "duration_seconds": 3.0,
    #     "character_loras": [...],
    #     "style_preset": "cinematic"
    # }

    # Timing
    queued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Progress tracking
    progress_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    progress_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Results
    output_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost tracking
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Quality metrics (computed after generation)
    quality_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "consistency_score": 0.85,
    #     "motion_quality": 0.90,
    #     "artifact_score": 0.95,
    #     "overall_score": 0.88
    # }

    # Relationships
    shot: Mapped["Shot"] = relationship("Shot", back_populates="generation_jobs")

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status in (
            JobStatus.PREPARING,
            JobStatus.RUNNING,
            JobStatus.POST_PROCESSING,
        )

    @property
    def is_complete(self) -> bool:
        """Check if job has completed (success or failure)."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMEOUT,
        )

    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.COMPLETED

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def wait_time_seconds(self) -> Optional[float]:
        """Calculate time spent waiting in queue."""
        if self.queued_at and self.started_at:
            return (self.started_at - self.queued_at).total_seconds()
        return None

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<GenerationJob(id={self.id}, shot_id={self.shot_id}, "
            f"status={self.status.value})>"
        )
