"""Shot model - represents individual shots within scenes."""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .generation_job import GenerationJob
    from .scene import Scene


class ShotType(str, Enum):
    """Standard cinematographic shot types."""

    ESTABLISHING = "establishing"  # Wide shot establishing location
    WIDE = "wide"  # Full scene coverage
    FULL = "full"  # Full body shot
    MEDIUM = "medium"  # Waist up
    MEDIUM_CLOSE_UP = "medium_close_up"  # Chest up
    CLOSE_UP = "close_up"  # Face/head
    EXTREME_CLOSE_UP = "extreme_close_up"  # Detail shot
    OVER_THE_SHOULDER = "over_the_shoulder"  # OTS shot
    POV = "pov"  # Point of view
    TWO_SHOT = "two_shot"  # Two characters
    GROUP = "group"  # Multiple characters
    INSERT = "insert"  # Detail insert
    CUTAWAY = "cutaway"  # Reaction or environment


class CameraMovement(str, Enum):
    """Camera movement types."""

    STATIC = "static"  # No movement
    PAN = "pan"  # Horizontal rotation
    TILT = "tilt"  # Vertical rotation
    DOLLY = "dolly"  # Move toward/away
    TRUCK = "truck"  # Move left/right
    CRANE = "crane"  # Vertical movement
    HANDHELD = "handheld"  # Natural shake
    STEADICAM = "steadicam"  # Smooth following
    ZOOM = "zoom"  # Lens zoom
    RACK_FOCUS = "rack_focus"  # Focus shift
    TRACKING = "tracking"  # Follow subject


class ShotState(str, Enum):
    """Shot generation workflow states."""

    PLANNED = "planned"  # Shot specified, not generated
    QUEUED = "queued"  # In generation queue
    GENERATING = "generating"  # Currently generating
    GENERATED = "generated"  # Generation complete
    FAILED = "failed"  # Generation failed
    REVIEW = "review"  # Awaiting user review
    APPROVED = "approved"  # User approved
    REJECTED = "rejected"  # User rejected, needs regeneration
    REGENERATING = "regenerating"  # Being regenerated


class Shot(Base, UUIDMixin, TimestampMixin):
    """An individual shot within a scene.

    Shots are the atomic unit of video generation. Each shot is
    generated independently and then assembled into scenes.
    """

    __tablename__ = "shots"

    # Foreign key to scene
    scene_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Shot identification
    shot_number: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Shot specification
    shot_type: Mapped[ShotType] = mapped_column(
        SAEnum(ShotType, name="shot_type"),
        nullable=False,
    )
    camera_movement: Mapped[CameraMovement] = mapped_column(
        SAEnum(CameraMovement, name="camera_movement"),
        default=CameraMovement.STATIC,
        nullable=False,
    )

    # Content description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    dialogue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Characters in shot (UUIDs of Character records)
    character_ids: Mapped[List[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), default=list, nullable=False
    )

    # Visual specification
    composition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lighting_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Generation prompts (computed/refined from description)
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    duration_seconds: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)

    # State
    state: Mapped[ShotState] = mapped_column(
        SAEnum(ShotState, name="shot_state"),
        default=ShotState.PLANNED,
        nullable=False,
    )

    # Generated output paths (relative to project directory)
    output_video_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    output_thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    # Generation metadata
    generation_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "model_used": "model_id",
    #     "model_version": "1.0",
    #     "seed": 12345,
    #     "steps": 50,
    #     "cfg_scale": 7.5,
    #     "generation_time_seconds": 120,
    #     "attempts": 1,
    #     "cost_estimate_usd": 0.05,
    #     "provider": "local",
    #     "resolution": "1920x1080",
    #     "fps": 24
    # }

    # User feedback
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5

    # Timeline editing fields
    timeline_visible: Mapped[bool] = mapped_column(default=True, nullable=False)
    timeline_locked: Mapped[bool] = mapped_column(default=False, nullable=False)
    timeline_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transition_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transition_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ms

    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="shots")
    generation_jobs: Mapped[List["GenerationJob"]] = relationship(
        "GenerationJob",
        back_populates="shot",
        cascade="all, delete-orphan",
        order_by="GenerationJob.created_at.desc()",
    )

    @property
    def is_generated(self) -> bool:
        """Check if shot has been generated."""
        return self.state in (
            ShotState.GENERATED,
            ShotState.REVIEW,
            ShotState.APPROVED,
        )

    @property
    def is_approved(self) -> bool:
        """Check if shot has been approved."""
        return self.state == ShotState.APPROVED

    @property
    def needs_regeneration(self) -> bool:
        """Check if shot needs regeneration."""
        return self.state in (ShotState.FAILED, ShotState.REJECTED)

    @property
    def latest_job(self) -> Optional["GenerationJob"]:
        """Get the most recent generation job."""
        if self.generation_jobs:
            return self.generation_jobs[0]  # Ordered by created_at desc
        return None

    @property
    def attempt_count(self) -> int:
        """Number of generation attempts."""
        return len(self.generation_jobs)

    def __repr__(self) -> str:
        """String representation."""
        return f"<Shot(id={self.id}, number='{self.shot_number}', type={self.shot_type.value})>"
