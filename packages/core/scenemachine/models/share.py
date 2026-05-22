"""Project sharing models."""

import enum
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base


class SharePermission(enum.StrEnum):
    """Permission levels for shared projects."""

    VIEW = "view"  # Can view project, scenes, shots
    COMMENT = "comment"  # Can view and add comments/feedback
    EDIT = "edit"  # Can modify project content
    ADMIN = "admin"  # Full access including sharing


class ShareStatus(enum.StrEnum):
    """Status of a share invitation."""

    PENDING = "pending"  # Invitation sent, not yet accepted
    ACCEPTED = "accepted"  # Share accepted and active
    DECLINED = "declined"  # Share declined by recipient
    REVOKED = "revoked"  # Share revoked by owner
    EXPIRED = "expired"  # Share link expired


class ProjectShare(Base):
    """Model for project share/collaboration records."""

    __tablename__ = "project_shares"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # The project being shared
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )

    # Share details
    share_code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )  # Unique share link code

    # Recipient (optional - can be email or user ID once auth is added)
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Permission level
    permission: Mapped[SharePermission] = mapped_column(
        Enum(SharePermission), default=SharePermission.VIEW
    )

    # Status
    status: Mapped[ShareStatus] = mapped_column(Enum(ShareStatus), default=ShareStatus.PENDING)

    # Optional message from sharer
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Expiration (optional)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Access tracking
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_count: Mapped[int] = mapped_column(default=0)

    # Whether share link is publicly accessible (no auth required)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="shares")

    def is_valid(self) -> bool:
        """Check if share is still valid."""
        if self.status not in (ShareStatus.PENDING, ShareStatus.ACCEPTED):
            return False
        return not (self.expires_at and datetime.now(UTC) > self.expires_at)

    def can_view(self) -> bool:
        """Check if share allows viewing."""
        return self.is_valid() and self.permission in (
            SharePermission.VIEW,
            SharePermission.COMMENT,
            SharePermission.EDIT,
            SharePermission.ADMIN,
        )

    def can_comment(self) -> bool:
        """Check if share allows commenting."""
        return self.is_valid() and self.permission in (
            SharePermission.COMMENT,
            SharePermission.EDIT,
            SharePermission.ADMIN,
        )

    def can_edit(self) -> bool:
        """Check if share allows editing."""
        return self.is_valid() and self.permission in (
            SharePermission.EDIT,
            SharePermission.ADMIN,
        )

    def can_admin(self) -> bool:
        """Check if share allows administration."""
        return self.is_valid() and self.permission == SharePermission.ADMIN


class ProjectComment(Base):
    """Model for comments/feedback on projects and shots."""

    __tablename__ = "project_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Parent project
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )

    # Optional specific shot (for shot-level feedback)
    shot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Optional parent comment (for replies)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_comments.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Author info (from share or local user)
    author_name: Mapped[str] = mapped_column(String(255))
    author_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Comment content
    content: Mapped[str] = mapped_column(Text)

    # Timecode reference (for shot comments)
    timecode_seconds: Mapped[float | None] = mapped_column(nullable=True)

    # Status
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    replies: Mapped[list["ProjectComment"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped[Optional["ProjectComment"]] = relationship(
        back_populates="replies",
        remote_side=[id],
    )


# Import for type hints (at runtime)
from scenemachine.models.project import Project  # noqa: E402
