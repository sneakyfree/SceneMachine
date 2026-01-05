"""
Video models for SceneMachine Network.

Includes Video, Series, and VideoStats.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user import User


class ContentType(enum.Enum):
    """Type of video content."""

    FILM = "film"  # Feature-length film
    SERIES = "series"  # Episode of a series
    SHORT = "short"  # Short film (< 40 min)
    ANIMATION = "animation"  # Animated content
    MUSIC_VIDEO = "music_video"  # Music video
    CLIP = "clip"  # Clip/excerpt
    OTHER = "other"  # Other content


class MonetizationType(enum.Enum):
    """How the video is monetized."""

    FREE_AD = "free_ad"  # Free with ads
    FREE_NO_AD = "free_no_ad"  # Free without ads
    PAID = "paid"  # Pay-per-view
    SUBSCRIBER_ONLY = "subscriber_only"  # Channel subscribers only


class VideoStatus(enum.Enum):
    """Status of the video."""

    UPLOADING = "uploading"  # Upload in progress
    PROCESSING = "processing"  # Transcoding in progress
    READY = "ready"  # Ready but not published
    PUBLISHED = "published"  # Publicly visible
    UNLISTED = "unlisted"  # Accessible via link only
    PRIVATE = "private"  # Only creator can see
    REMOVED = "removed"  # Removed by creator or moderation
    FAILED = "failed"  # Processing failed


class TranscodingStatus(enum.Enum):
    """Status of video transcoding."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Series(Base, UUIDMixin, TimestampMixin):
    """
    Series model for episodic content.

    A series contains multiple video episodes.
    """

    __tablename__ = "series"

    # Owner
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Series info
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Stats (denormalized)
    episode_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Status
    is_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
        lazy="selectin",
    )
    episodes: Mapped[list["Video"]] = relationship(
        "Video",
        back_populates="series",
        order_by="Video.episode_number",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Series {self.title} ({self.episode_count} episodes)>"


class Video(Base, UUIDMixin, TimestampMixin):
    """
    Video model for SceneMachine Network.

    Represents a single video on the platform.
    """

    __tablename__ = "videos"

    # Owner
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic info
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Content type
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType),
        default=ContentType.OTHER,
        nullable=False,
    )

    # Series (optional)
    series_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("series.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    episode_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Source tracking
    made_with_studio: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    studio_project_id: Mapped[Optional[str]] = mapped_column(
        String(36),  # UUID as string
        nullable=True,
    )

    # Video files
    source_file_key: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    transcoded_versions: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    # Transcoding
    transcoding_status: Mapped[TranscodingStatus] = mapped_column(
        Enum(TranscodingStatus),
        default=TranscodingStatus.PENDING,
        nullable=False,
    )
    transcoding_progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    transcoding_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Monetization
    monetization_type: Mapped[MonetizationType] = mapped_column(
        Enum(MonetizationType),
        default=MonetizationType.FREE_AD,
        nullable=False,
    )
    ticket_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    # Status
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus),
        default=VideoStatus.UPLOADING,
        nullable=False,
        index=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduled_publish_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Engagement metrics (denormalized for speed)
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    dislike_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    comment_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    share_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Discovery
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Moderation
    is_age_restricted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    moderation_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
        lazy="selectin",
    )
    series: Mapped[Optional["Series"]] = relationship(
        "Series",
        back_populates="episodes",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_videos_creator_status", "creator_id", "status"),
        Index("ix_videos_published_at", "published_at", postgresql_using="btree"),
        Index("ix_videos_quality_score", "quality_score", postgresql_using="btree"),
        Index("ix_videos_view_count", "view_count", postgresql_using="btree"),
    )

    @property
    def is_public(self) -> bool:
        """Check if the video is publicly visible."""
        return self.status == VideoStatus.PUBLISHED

    @property
    def is_ready_to_publish(self) -> bool:
        """Check if the video can be published."""
        return (
            self.transcoding_status == TranscodingStatus.COMPLETED
            and self.status in (VideoStatus.READY, VideoStatus.PRIVATE)
        )

    def __repr__(self) -> str:
        return f"<Video {self.title} ({self.status.value})>"


class VideoStats(Base, TimestampMixin):
    """
    Daily statistics for a video.

    Used for analytics and revenue tracking.
    """

    __tablename__ = "video_stats"

    # Composite primary key
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )

    # View stats
    views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    unique_viewers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    watch_time_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    average_watch_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Engagement
    likes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    dislikes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    comments: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    shares: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Revenue
    ad_impressions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    ad_revenue: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    ticket_sales: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    ticket_revenue: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    tip_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tip_revenue: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Traffic sources (JSON)
    traffic_sources: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Geographic distribution (JSON)
    geography: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_video_stats_date", "date"),
        Index("ix_video_stats_video_date", "video_id", "date"),
    )

    @property
    def total_revenue(self) -> Decimal:
        """Calculate total revenue for the day."""
        return self.ad_revenue + self.ticket_revenue + self.tip_revenue

    def __repr__(self) -> str:
        return f"<VideoStats video={self.video_id} date={self.date}>"


class CostTracking(Base, TimestampMixin):
    """
    Monthly cost tracking per video.

    Tracks storage and bandwidth costs for transparency.
    """

    __tablename__ = "cost_tracking"

    # Composite primary key
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    month: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )

    # Storage
    storage_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    storage_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )

    # Bandwidth
    bandwidth_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    bandwidth_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )

    # Processing
    processing_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost for the month."""
        return self.storage_cost + self.bandwidth_cost + self.processing_cost

    def __repr__(self) -> str:
        return f"<CostTracking video={self.video_id} month={self.month}>"
