"""
GenerationJob Model

Tracks video/image generation jobs and their status.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin, JSONType

if TYPE_CHECKING:
    from scenemachine.models.shot import Shot


class JobType(str, Enum):
    """Types of generation jobs."""

    # Video generation
    SHOT_VIDEO = "shot_video"  # Generate video for a shot
    SCENE_ASSEMBLY = "scene_assembly"  # Assemble shots into scene
    FINAL_EXPORT = "final_export"  # Export final movie

    # Image generation
    CHARACTER_LIKENESS = "character_likeness"  # Generate character images
    CHARACTER_VARIATIONS = "character_variations"  # Generate character variations
    THUMBNAIL = "thumbnail"  # Generate thumbnail

    # Model training
    CHARACTER_LORA = "character_lora"  # Train character LoRA
    CHARACTER_EMBEDDING = "character_embedding"  # Create character embedding

    # Processing
    VIDEO_UPSCALE = "video_upscale"  # Upscale video
    VIDEO_INTERPOLATION = "video_interpolation"  # Frame interpolation
    AUDIO_SYNC = "audio_sync"  # Sync audio to video


class JobStatus(str, Enum):
    """Generation job status."""

    PENDING = "pending"  # Job created, waiting to start
    QUEUED = "queued"  # In queue, waiting for resources
    PREPARING = "preparing"  # Loading models, preparing inputs
    RUNNING = "running"  # Currently generating
    COMPLETING = "completing"  # Post-processing output
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Cancelled by user
    PAUSED = "paused"  # Paused by user or system


class JobProvider(str, Enum):
    """Execution providers for generation jobs."""

    LOCAL = "local"  # Local GPU
    SCENEMACHINE_CLOUD = "scenemachine_cloud"  # SceneMachine cloud
    REPLICATE = "replicate"  # Replicate.com
    RUNPOD = "runpod"  # RunPod
    MODAL = "modal"  # Modal.com
    COMFYUI = "comfyui"  # Local ComfyUI
    CUSTOM = "custom"  # Custom provider
    # ActCore performance-driven generation
    ACTCORE = "actcore"  # ActCore performer motion retargeting
    # GPU Exchange providers
    LAMBDA_LABS = "lambda_labs"  # Lambda Labs
    VAST_AI = "vast_ai"  # Vast.ai
    FLUIDSTACK = "fluidstack"  # FluidStack
    COREWEAVE = "coreweave"  # CoreWeave


class GenerationJob(Base, UUIDMixin, TimestampMixin):
    """
    A generation job for video, image, or model training.

    Generation jobs track the lifecycle of content generation,
    including queue position, progress, costs, and results.

    Attributes:
        project_id: Foreign key to project
        shot_id: Optional foreign key to shot (for shot generation)
        job_type: Type of generation job
        status: Current job status
        provider: Execution provider
        priority: Queue priority (higher = more urgent)
        progress: Completion percentage (0-100)
        input_params: Input parameters for generation (JSON)
        output_info: Output file information (JSON)
        error_info: Error details if failed (JSON)
        cost_info: Cost tracking (JSON)
        timing: Timing information (JSON)
    """

    __tablename__ = "generation_jobs"

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shot_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scene_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    character_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Job classification
    job_type: Mapped[JobType] = mapped_column(
        SAEnum(JobType, name="job_type"),
        nullable=False,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    provider: Mapped[JobProvider] = mapped_column(
        SAEnum(JobProvider, name="job_provider"),
        default=JobProvider.LOCAL,
        nullable=False,
    )

    # Queue management
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0-100
    queue_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100
    progress_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_step_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Input parameters
    input_params: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure varies by job_type:
    #
    # For SHOT_VIDEO:
    # {
    #     "prompt": "...",
    #     "negative_prompt": "...",
    #     "model": "wan2.1",
    #     "seed": 12345,
    #     "steps": 50,
    #     "cfg_scale": 7.5,
    #     "width": 1920,
    #     "height": 1080,
    #     "duration_seconds": 3,
    #     "frame_rate": 24,
    #     "character_embeddings": ["uuid1"],
    #     "reference_images": ["path1"],
    #     "style_preset": "cinematic"
    # }
    #
    # For CHARACTER_LORA:
    # {
    #     "training_images": ["path1", "path2"],
    #     "base_model": "SDXL",
    #     "rank": 32,
    #     "alpha": 16,
    #     "learning_rate": 1e-4,
    #     "training_steps": 1000,
    #     "trigger_word": "ohwx person"
    # }

    # Output information
    output_info: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "output_path": "path/to/output.mp4",
    #     "thumbnail_path": "path/to/thumb.jpg",
    #     "asset_ids": ["uuid1"],
    #     "file_size_bytes": 1234567,
    #     "resolution": "1920x1080",
    #     "duration_seconds": 3.0,
    #     "frame_count": 72
    # }

    # Error information
    error_info: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "error_type": "OutOfMemoryError",
    #     "error_message": "CUDA out of memory",
    #     "error_traceback": "...",
    #     "recoverable": true,
    #     "suggested_action": "Try reducing resolution or batch size",
    #     "occurred_at": "2024-01-15T10:30:00Z"
    # }

    # Cost tracking
    cost_info: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "estimated_cost_usd": 0.05,
    #     "actual_cost_usd": 0.048,
    #     "compute_units": 100,
    #     "gpu_time_seconds": 120,
    #     "provider_job_id": "job_abc123",
    #     "billing_status": "charged"
    # }

    # Timing
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_completion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # External tracking
    external_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # User notes
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    shot: Mapped[Optional["Shot"]] = relationship("Shot", back_populates="generation_jobs")

    @property
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in (
            JobStatus.PENDING,
            JobStatus.QUEUED,
            JobStatus.PREPARING,
            JobStatus.RUNNING,
            JobStatus.COMPLETING,
        )

    @property
    def is_complete(self) -> bool:
        """Check if job is complete (success or failure)."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.COMPLETED

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None

    @property
    def wait_time_seconds(self) -> Optional[float]:
        """Calculate queue wait time in seconds."""
        if self.queued_at and self.started_at:
            delta = self.started_at - self.queued_at
            return delta.total_seconds()
        return None

    @property
    def estimated_cost(self) -> Optional[float]:
        """Get estimated cost in USD."""
        if self.cost_info:
            return self.cost_info.get("estimated_cost_usd")
        return None

    @property
    def actual_cost(self) -> Optional[float]:
        """Get actual cost in USD."""
        if self.cost_info:
            return self.cost_info.get("actual_cost_usd")
        return None

    def can_transition_to(self, new_status: JobStatus) -> bool:
        """Check if transition to new status is valid."""
        valid_transitions: dict[JobStatus, list[JobStatus]] = {
            JobStatus.PENDING: [JobStatus.QUEUED, JobStatus.CANCELLED],
            JobStatus.QUEUED: [
                JobStatus.PREPARING,
                JobStatus.CANCELLED,
                JobStatus.PAUSED,
            ],
            JobStatus.PREPARING: [JobStatus.RUNNING, JobStatus.FAILED, JobStatus.CANCELLED],
            JobStatus.RUNNING: [
                JobStatus.COMPLETING,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.PAUSED,
            ],
            JobStatus.COMPLETING: [JobStatus.COMPLETED, JobStatus.FAILED],
            JobStatus.COMPLETED: [],  # Terminal state
            JobStatus.FAILED: [JobStatus.PENDING],  # Can retry
            JobStatus.CANCELLED: [],  # Terminal state
            JobStatus.PAUSED: [JobStatus.QUEUED, JobStatus.CANCELLED],
        }
        return new_status in valid_transitions.get(self.status, [])

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<GenerationJob(id={self.id}, "
            f"type={self.job_type.value}, "
            f"status={self.status.value}, "
            f"progress={self.progress:.1f}%)>"
        )
