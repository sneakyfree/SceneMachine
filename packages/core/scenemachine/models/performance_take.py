"""
PerformanceTake Model

Represents a recorded performance "take" with motion/emotion data
that can be used for performance-driven retargeting.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin, JSONType, ArrayType


if TYPE_CHECKING:
    from scenemachine.models.performer import Performer
    from scenemachine.models.booking import Booking


class TakeMode(str, Enum):
    """Booking mode the take was created for."""
    BLINK = "blink"  # 10-second quick take
    DEEP = "deep"  # 120-second method acting
    EPIC = "epic"  # 5-20 minute continuous take
    DEMO = "demo"  # Demo reel take


class TakeStatus(str, Enum):
    """Status of the performance take."""
    UPLOADING = "uploading"  # Being uploaded
    PROCESSING = "processing"  # Processing motion data
    AVAILABLE = "available"  # Ready for use
    ARCHIVED = "archived"  # Archived (still usable)
    FLAGGED = "flagged"  # Flagged for review
    DELETED = "deleted"  # Soft deleted


class PerformanceTake(Base, UUIDMixin, TimestampMixin):
    """
    A recorded performance take with motion/emotion data.

    Takes contain the raw motion capture data (LivePortrait vectors,
    Roop-GS-Anim data) that can be retargeted onto AI characters.

    Attributes:
        performer_id: Foreign key to performer
        take_name: Display name for the take
        mode: Booking mode (blink, deep, epic, demo)
        duration_seconds: Length of the take
        emotion_tags: List of emotion descriptors
        motion_profile: JSON with motion data paths
        quality_metrics: JSON with quality scores
        status: Current take status
    """

    __tablename__ = "performance_takes"

    # Foreign keys
    performer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("performers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Take identification
    take_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[TakeMode] = mapped_column(
        SAEnum(TakeMode, name="take_mode"),
        default=TakeMode.BLINK,
        nullable=False,
        index=True,
    )

    # Duration and timing
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    recording_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Content classification
    emotion_tags: Mapped[Optional[list]] = mapped_column(ArrayType(String), nullable=True)
    # Example: ["grief", "anger", "subtle", "intense"]

    scene_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Brief description of the scene context for this take

    # Motion data paths
    motion_profile: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "liveportrait_vectors_path": "takes/uuid/vectors.npy",
    #     "roop_gs_anim_path": "takes/uuid/roop_motion.json",
    #     "face_embedding_path": "takes/uuid/face_embed.pkl",
    #     "landmark_data_path": "takes/uuid/landmarks.json",
    #     "audio_sync_data_path": "takes/uuid/audio_sync.json",
    #     "face_mesh_path": "takes/uuid/mesh.pkl",
    #     "metadata_path": "takes/uuid/metadata.json"
    # }

    # Quality metrics (used for ACI MotionScore)
    quality_metrics: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "motion_score": 85.5,  # Overall motion quality 0-100
    #     "emotion_clarity": 92.0,  # How clear the emotion reads
    #     "sync_accuracy": 88.0,  # Audio sync accuracy
    #     "frame_consistency": 90.0,  # Frame-to-frame consistency
    #     "face_tracking_confidence": 95.0,  # Face detection confidence
    #     "expression_range": 78.0,  # Dynamic range of expressions
    #     "jitter_score": 96.0  # Lower is worse (inverse of jitter)
    # }

    # Status
    status: Mapped[TakeStatus] = mapped_column(
        SAEnum(TakeStatus, name="take_status"),
        default=TakeStatus.PROCESSING,
        nullable=False,
        index=True,
    )

    # Demo reel flag
    is_demo_reel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Demo reel takes are shown on performer profile

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Storage
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Processing info
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    performer: Mapped["Performer"] = relationship(
        "Performer",
        back_populates="takes",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="take",
        foreign_keys="Booking.take_id",
    )

    @property
    def motion_score(self) -> float:
        """Get the overall motion score for ACI calculation."""
        if self.quality_metrics:
            return self.quality_metrics.get("motion_score", 50.0)
        return 50.0

    @property
    def is_available(self) -> bool:
        """Check if take is available for use."""
        return self.status == TakeStatus.AVAILABLE

    @property
    def has_motion_data(self) -> bool:
        """Check if take has valid motion data."""
        if not self.motion_profile:
            return False
        required_keys = ["liveportrait_vectors_path", "roop_gs_anim_path"]
        return all(key in self.motion_profile for key in required_keys)

    def increment_usage(self) -> None:
        """Increment usage counter."""
        from datetime import datetime, timezone
        self.usage_count += 1
        self.last_used_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<PerformanceTake(id={self.id}, "
            f"name={self.take_name}, "
            f"mode={self.mode.value}, "
            f"duration={self.duration_seconds:.1f}s, "
            f"status={self.status.value})>"
        )
