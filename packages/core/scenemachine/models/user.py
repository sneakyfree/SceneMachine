"""
User Model for Authentication

SQLAlchemy model for user accounts with authentication support.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from scenemachine.models.project import Project


class UserRole(str, Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class User(Base, UUIDMixin, TimestampMixin):
    """User account model.

    Stores user authentication and profile information.
    Supports email/password authentication with optional email verification.
    """

    __tablename__ = "users"

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.USER.value,
        nullable=False,
    )

    # Security tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
        lazy="dynamic",
        foreign_keys="Project.owner_id",
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_username_active", "username", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in (UserRole.ADMIN.value, UserRole.SUPERADMIN.value)

    @property
    def is_superadmin(self) -> bool:
        """Check if user is superadmin."""
        return self.role == UserRole.SUPERADMIN.value


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    """Refresh token storage for JWT authentication.

    Stores refresh tokens to enable token rotation and revocation.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    device_info: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked"),
        Index("ix_refresh_tokens_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"
