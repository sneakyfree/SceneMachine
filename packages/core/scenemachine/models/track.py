"""
Track Model

Timeline tracks for organizing clips in the video editor.
"""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin


class TrackType(str, Enum):
    """Types of timeline tracks."""

    VIDEO = "video"
    AUDIO = "audio"
    DIALOGUE = "dialogue"
    MUSIC = "music"
    SFX = "sfx"
    VOICEOVER = "voiceover"
    TEXT = "text"
    EFFECTS = "effects"


class Track(Base, UUIDMixin, TimestampMixin):
    """
    A timeline track for organizing clips.

    Tracks are ordered layers in the timeline. Each track has a type
    (video, audio, dialogue, etc.) and can contain multiple clips.

    Attributes:
        project_id: Foreign key to project
        name: Display name of track
        track_type: Type of content this track holds
        order: Vertical position in timeline (0 = top)
        color: Optional color for visual distinction
        is_visible: Whether track is visible in preview
        is_locked: Whether track is locked for editing
        is_solo: Whether track is soloed (mutes others)
        is_muted: Whether track is muted
        volume: Volume level for audio tracks (0.0 to 1.0)
        pan: Stereo pan for audio tracks (-1.0 to 1.0)
    """

    __tablename__ = "tracks"

    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    track_type: Mapped[TrackType] = mapped_column(
        SAEnum(TrackType, name="track_type"),
        nullable=False,
        index=True,
    )

    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color

    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_solo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Audio mixing
    volume: Mapped[float] = mapped_column(default=1.0, nullable=False)
    pan: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Relationships
    clips: Mapped[List["TimelineClip"]] = relationship(
        "TimelineClip",
        back_populates="track",
        order_by="TimelineClip.start_time",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Track(id={self.id}, name='{self.name}', type={self.track_type.value})>"


class TimelineClip(Base, UUIDMixin, TimestampMixin):
    """
    A clip placed on the timeline.

    Represents a segment of media (video, audio, etc.) placed at a
    specific position on a track with trimming and z-index support.

    Attributes:
        track_id: Foreign key to track
        source_id: ID of source asset/shot/audio
        source_type: Type of source (shot, audio, text, etc.)
        start_time: Start position in timeline (seconds)
        duration: Duration on timeline (seconds)
        trim_start: Amount trimmed from source start (seconds)
        trim_end: Amount trimmed from source end (seconds)
        z_index: Stack order for overlapping clips
    """

    __tablename__ = "timeline_clips"

    track_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source reference
    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # shot, audio, text

    # Timeline position
    start_time: Mapped[float] = mapped_column(default=0.0, nullable=False)
    duration: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Trimming
    trim_start: Mapped[float] = mapped_column(default=0.0, nullable=False)
    trim_end: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Layer stacking
    z_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Display
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Audio properties (for audio clips)
    volume: Mapped[float] = mapped_column(default=1.0, nullable=False)
    fade_in: Mapped[float] = mapped_column(default=0.0, nullable=False)
    fade_out: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Relationships
    track: Mapped["Track"] = relationship("Track", back_populates="clips")

    @property
    def end_time(self) -> float:
        """Calculate end time on timeline."""
        return self.start_time + self.duration

    @property
    def source_duration(self) -> float:
        """Calculate original source duration before trimming."""
        return self.duration + self.trim_start + self.trim_end

    def __repr__(self) -> str:
        return (
            f"<TimelineClip(id={self.id}, "
            f"start={self.start_time:.2f}, "
            f"duration={self.duration:.2f})>"
        )
