"""
Streaming models for SceneMachine Network.

Includes WatchHistory, ViewEvent, and WatchSession.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user import User
    from .video import Video


class WatchHistory(Base, TimestampMixin):
    """
    Watch history for a user-video pair.

    Tracks the user's watch progress and completion status.
    """

    __tablename__ = "watch_history"

    # Composite primary key
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Progress
    progress_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    watch_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Timestamps
    last_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    first_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Watch count
    watch_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_watch_history_user_last", "user_id", "last_watched_at"),
        Index("ix_watch_history_video", "video_id"),
    )

    def __repr__(self) -> str:
        return f"<WatchHistory user={self.user_id} video={self.video_id} progress={self.watch_percent:.1f}%>"


class WatchSession(Base, UUIDMixin, TimestampMixin):
    """
    Active watch session for real-time tracking.

    Used to track concurrent viewers and session-level analytics.
    """

    __tablename__ = "watch_sessions"

    # References
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Anonymous viewers
        index=True,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Session info
    session_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Device/client info
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),  # desktop, mobile, tablet, tv
        nullable=True,
    )
    browser: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    os: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Progress
    current_position_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    quality_level: Mapped[Optional[str]] = mapped_column(
        String(20),  # 360p, 480p, 720p, 1080p, 4k
        nullable=True,
    )

    # Session state
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Watch time in this session
    watch_time_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Traffic source
    referrer: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    traffic_source: Mapped[Optional[str]] = mapped_column(
        String(50),  # direct, search, social, embed, recommendation
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_watch_sessions_active", "video_id", "is_active"),
        Index("ix_watch_sessions_heartbeat", "last_heartbeat_at"),
    )

    def __repr__(self) -> str:
        return f"<WatchSession {self.session_token[:8]}... video={self.video_id}>"


class ViewEvent(Base, UUIDMixin):
    """
    Individual view event for analytics.

    Used for deduplicated view counting and detailed analytics.
    """

    __tablename__ = "view_events"

    # References
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watch_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # View info
    ip_hash: Mapped[str] = mapped_column(
        String(64),  # Hashed IP for deduplication
        nullable=False,
        index=True,
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Watch metrics
    watch_time_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    watch_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Quality tracking
    average_quality: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    quality_changes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    buffering_events: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Geographic
    country_code: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Device
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Is this a valid view? (for counting)
    is_valid_view: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_view_events_video_date", "video_id", "viewed_at"),
        Index("ix_view_events_dedup", "video_id", "ip_hash", "viewed_at"),
    )

    def __repr__(self) -> str:
        return f"<ViewEvent video={self.video_id} valid={self.is_valid_view}>"


# View counting thresholds
VIEW_MINIMUM_WATCH_SECONDS = 30  # Minimum watch time for a valid view
VIEW_MINIMUM_WATCH_PERCENT = 10  # Or minimum percentage
VIEW_DEDUP_WINDOW_HOURS = 24  # Deduplicate views within this window
