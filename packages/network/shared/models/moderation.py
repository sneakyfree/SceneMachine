"""
Moderation models for SceneMachine Network.

Includes Report, Appeal, Strike, ContentFlag.
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
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user import User
    from .video import Video


class ReportReason(str, enum.Enum):
    """Reasons for reporting content."""

    SPAM = "spam"
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SEXUAL_CONTENT = "sexual_content"
    CHILD_SAFETY = "child_safety"
    MISINFORMATION = "misinformation"
    COPYRIGHT = "copyright"
    PRIVACY = "privacy"
    SELF_HARM = "self_harm"
    TERRORISM = "terrorism"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    """Status of a report."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED_ACTION_TAKEN = "resolved_action_taken"
    RESOLVED_NO_ACTION = "resolved_no_action"
    DISMISSED = "dismissed"


class ReportTargetType(str, enum.Enum):
    """Type of content being reported."""

    VIDEO = "video"
    COMMENT = "comment"
    USER = "user"
    CHANNEL = "channel"


class ActionType(str, enum.Enum):
    """Types of moderation actions."""

    WARNING = "warning"
    CONTENT_REMOVE = "content_remove"
    AGE_RESTRICT = "age_restrict"
    MONETIZATION_SUSPEND = "monetization_suspend"
    CHANNEL_SUSPEND = "channel_suspend"
    TEMP_BAN = "temp_ban"
    PERM_BAN = "perm_ban"


class AppealStatus(str, enum.Enum):
    """Status of an appeal."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    PARTIAL = "partial"


class FlagCategory(str, enum.Enum):
    """Categories for AI content flags."""

    VIOLENCE = "violence"
    NUDITY = "nudity"
    HATE_SPEECH = "hate_speech"
    SELF_HARM = "self_harm"
    CHILD_SAFETY = "child_safety"
    SPAM = "spam"
    SCAM = "scam"
    COPYRIGHT = "copyright"
    MISINFORMATION = "misinformation"
    OTHER = "other"


class FlagSeverity(str, enum.Enum):
    """Severity levels for content flags."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Report(Base, UUIDMixin, TimestampMixin):
    """
    User report of content or user.
    """

    __tablename__ = "reports"

    # Reporter
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Anonymous reports allowed
        index=True,
    )

    # Target
    target_type: Mapped[ReportTargetType] = mapped_column(
        Enum(ReportTargetType),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # The user who owns the reported content
        index=True,
    )

    # Report details
    reason: Mapped[ReportReason] = mapped_column(
        Enum(ReportReason),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    timestamp_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,  # For video reports at specific timestamp
    )

    # Status
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.PENDING,
        nullable=False,
    )

    # Review
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Priority (auto-calculated based on reason and reporter history)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,  # 1-10, higher = more urgent
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_reports_status_priority", "status", "priority"),
        Index("ix_reports_target", "target_type", "target_id"),
        Index("ix_reports_reason", "reason"),
    )

    def __repr__(self) -> str:
        return f"<Report {self.id} {self.reason.value} on {self.target_type.value}>"


class ModerationAction(Base, UUIDMixin, TimestampMixin):
    """
    Record of a moderation action taken.
    """

    __tablename__ = "moderation_actions"

    # Target user (who received the action)
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Moderator
    moderator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Action
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType),
        nullable=False,
    )

    # Related content
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Related report
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Details
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Duration (for temporary actions)
    duration_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Revocation
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_moderation_actions_target", "target_user_id", "action_type"),
    )

    def __repr__(self) -> str:
        return f"<ModerationAction {self.action_type.value} on user={self.target_user_id}>"


class Strike(Base, UUIDMixin, TimestampMixin):
    """
    Strike against a creator account.

    3 strikes = termination.
    """

    __tablename__ = "strikes"

    # User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Related action
    action_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moderation_actions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Details
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,  # Strikes typically expire after 90 days
    )

    # Indexes
    __table_args__ = (
        Index("ix_strikes_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Strike {self.id} user={self.user_id}>"


class Appeal(Base, UUIDMixin, TimestampMixin):
    """
    Appeal of a moderation action.
    """

    __tablename__ = "appeals"

    # Appellant
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What is being appealed
    action_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moderation_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    strike_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strikes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Appeal details
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    status: Mapped[AppealStatus] = mapped_column(
        Enum(AppealStatus),
        default=AppealStatus.PENDING,
        nullable=False,
    )

    # Review
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    decision_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index("ix_appeals_user", "user_id"),
        Index("ix_appeals_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Appeal {self.id} user={self.user_id} status={self.status.value}>"


class ContentFlag(Base, UUIDMixin, TimestampMixin):
    """
    Automated content flag from AI moderation.
    """

    __tablename__ = "content_flags"

    # Content (either video or comment)
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Flag details
    category: Mapped[FlagCategory] = mapped_column(
        Enum(FlagCategory),
        nullable=False,
    )
    severity: Mapped[FlagSeverity] = mapped_column(
        Enum(FlagSeverity),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        nullable=False,
    )
    timestamp_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # AI model info
    detection_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    detection_details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Auto-action taken
    auto_action_taken: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Review
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_accurate: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,  # True = flag was correct, False = false positive
    )

    # Indexes
    __table_args__ = (
        Index("ix_content_flags_video", "video_id"),
        Index("ix_content_flags_severity", "severity"),
        Index("ix_content_flags_reviewed", "reviewed_at"),
    )

    def __repr__(self) -> str:
        return f"<ContentFlag {self.category.value} video={self.video_id} conf={self.confidence_score}>"


# Priority levels for different report reasons
REPORT_PRIORITY = {
    ReportReason.CHILD_SAFETY: 10,
    ReportReason.TERRORISM: 10,
    ReportReason.SELF_HARM: 9,
    ReportReason.VIOLENCE: 8,
    ReportReason.HATE_SPEECH: 7,
    ReportReason.HARASSMENT: 6,
    ReportReason.SEXUAL_CONTENT: 6,
    ReportReason.PRIVACY: 5,
    ReportReason.COPYRIGHT: 4,
    ReportReason.MISINFORMATION: 4,
    ReportReason.SPAM: 2,
    ReportReason.OTHER: 3,
}

# Strike expiration in days
STRIKE_EXPIRATION_DAYS = 90

# Maximum strikes before termination
MAX_STRIKES = 3
