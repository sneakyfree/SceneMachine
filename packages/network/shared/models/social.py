"""
Social models for SceneMachine Network.

Includes Follow, Comment, Reaction, Watchlist.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user import User
    from .video import Video


class ReactionType(str, enum.Enum):
    """Types of reactions users can give."""

    LIKE = "like"
    LOVE = "love"
    FIRE = "fire"
    MIND_BLOWN = "mind_blown"
    SAD = "sad"
    LAUGH = "laugh"


class Follow(Base, TimestampMixin):
    """
    Follow relationship between users.
    """

    __tablename__ = "follows"

    # Composite primary key
    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Notification preference
    notify_on_upload: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_follows_follower", "follower_id"),
        Index("ix_follows_following", "following_id"),
    )

    def __repr__(self) -> str:
        return f"<Follow {self.follower_id} -> {self.following_id}>"


class Comment(Base, UUIDMixin, TimestampMixin):
    """
    Comment on a video.

    Supports threaded replies.
    """

    __tablename__ = "comments"

    # References
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Engagement
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Creator interaction
    is_creator_heart: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Moderation
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    hidden_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    # Edit tracking
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_comments_video_created", "video_id", "created_at"),
        Index("ix_comments_user_created", "user_id", "created_at"),
        Index("ix_comments_parent", "parent_id"),
    )

    def __repr__(self) -> str:
        return f"<Comment {self.id} on video={self.video_id}>"


class CommentLike(Base, TimestampMixin):
    """
    Like on a comment.
    """

    __tablename__ = "comment_likes"

    # Composite primary key
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_comment_likes_comment", "comment_id"),
        Index("ix_comment_likes_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<CommentLike comment={self.comment_id} user={self.user_id}>"


class Reaction(Base, TimestampMixin):
    """
    Reaction on a video.
    """

    __tablename__ = "reactions"

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

    # Reaction type
    reaction_type: Mapped[ReactionType] = mapped_column(
        Enum(ReactionType),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_reactions_video", "video_id"),
        Index("ix_reactions_user", "user_id"),
        Index("ix_reactions_video_type", "video_id", "reaction_type"),
    )

    def __repr__(self) -> str:
        return f"<Reaction {self.reaction_type.value} video={self.video_id}>"


class Watchlist(Base, TimestampMixin):
    """
    User's watchlist (save for later).
    """

    __tablename__ = "watchlist"

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

    # Optional note
    note: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_watchlist_user_created", "user_id", "created_at"),
        Index("ix_watchlist_video", "video_id"),
    )

    def __repr__(self) -> str:
        return f"<Watchlist user={self.user_id} video={self.video_id}>"


class Share(Base, UUIDMixin, TimestampMixin):
    """
    Share event for tracking.
    """

    __tablename__ = "shares"

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

    # Share details
    platform: Mapped[Optional[str]] = mapped_column(
        String(50),  # twitter, facebook, reddit, copy_link, embed, etc.
        nullable=True,
    )
    ip_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_shares_video_created", "video_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Share video={self.video_id} platform={self.platform}>"


class Notification(Base, UUIDMixin, TimestampMixin):
    """
    User notifications.
    """

    __tablename__ = "notifications"

    # Recipient
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification type
    notification_type: Mapped[str] = mapped_column(
        String(50),  # new_follower, comment, reply, reaction, upload, etc.
        nullable=False,
    )

    # Actor (who triggered the notification)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Related entities
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=True,
    )
    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Status
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} for user={self.user_id}>"
