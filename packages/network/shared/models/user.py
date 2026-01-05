"""
User models for SceneMachine Network.

Includes User, CreatorProfile, and UserSettings.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class RevenueTier(enum.IntEnum):
    """Revenue tier for graduated split calculation."""

    TIER_1 = 1  # $0 - $1,000: 50% platform, 50% creator
    TIER_2 = 2  # $1,001 - $10,000: 40% platform, 60% creator
    TIER_3 = 3  # $10,001 - $100,000: 30% platform, 70% creator
    TIER_4 = 4  # $100,001 - $1,000,000: 20% platform, 80% creator
    TIER_5 = 5  # $1,000,001 - $10,000,000: 10% platform, 90% creator
    TIER_6 = 6  # $10,000,001+: 1% platform, 99% creator


def get_platform_cut(tier: RevenueTier) -> Decimal:
    """Get platform cut percentage for a revenue tier."""
    cuts = {
        RevenueTier.TIER_1: Decimal("0.50"),
        RevenueTier.TIER_2: Decimal("0.40"),
        RevenueTier.TIER_3: Decimal("0.30"),
        RevenueTier.TIER_4: Decimal("0.20"),
        RevenueTier.TIER_5: Decimal("0.10"),
        RevenueTier.TIER_6: Decimal("0.01"),
    }
    return cuts.get(tier, Decimal("0.50"))


def calculate_tier(total_earnings: Decimal) -> RevenueTier:
    """Calculate revenue tier based on total earnings."""
    if total_earnings <= 1000:
        return RevenueTier.TIER_1
    elif total_earnings <= 10000:
        return RevenueTier.TIER_2
    elif total_earnings <= 100000:
        return RevenueTier.TIER_3
    elif total_earnings <= 1000000:
        return RevenueTier.TIER_4
    elif total_earnings <= 10000000:
        return RevenueTier.TIER_5
    else:
        return RevenueTier.TIER_6


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model for SceneMachine Network.

    Represents both viewers and creators on the platform.
    """

    __tablename__ = "users"

    # Account information
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
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # Null for OAuth-only users
    )

    # Profile
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Status flags
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_creator: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Email verification
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # OAuth provider data
    oauth_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    oauth_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Last activity
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    creator_profile: Mapped[Optional["CreatorProfile"]] = relationship(
        "CreatorProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    settings: Mapped[Optional["UserSettings"]] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_users_oauth", "oauth_provider", "oauth_id"),
        Index("ix_users_email_lower", func.lower(email)),
        Index("ix_users_username_lower", func.lower(username)),
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"


class CreatorProfile(Base, TimestampMixin):
    """
    Creator profile for users who upload content.

    Contains monetization settings and channel information.
    """

    __tablename__ = "creator_profiles"

    # Primary key is user_id (one-to-one with User)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Channel information
    channel_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    channel_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    channel_banner_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Monetization
    monetization_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    tax_info_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    stripe_account_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    stripe_onboarding_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Earnings
    total_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    pending_payout: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    current_tier: Mapped[int] = mapped_column(
        Integer,
        default=RevenueTier.TIER_1.value,
        nullable=False,
    )

    # Stats
    subscriber_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    video_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationship back to user
    user: Mapped["User"] = relationship(
        "User",
        back_populates="creator_profile",
    )

    @property
    def revenue_tier(self) -> RevenueTier:
        """Get the current revenue tier."""
        return RevenueTier(self.current_tier)

    @property
    def platform_cut(self) -> Decimal:
        """Get the current platform cut percentage."""
        return get_platform_cut(self.revenue_tier)

    @property
    def creator_cut(self) -> Decimal:
        """Get the current creator cut percentage."""
        return Decimal("1.00") - self.platform_cut

    def update_tier(self) -> None:
        """Update the revenue tier based on total earnings."""
        self.current_tier = calculate_tier(self.total_earnings).value

    def __repr__(self) -> str:
        return f"<CreatorProfile {self.channel_name} (user={self.user_id})>"


class UserSettings(Base, TimestampMixin):
    """
    User settings and preferences.

    Includes notification preferences, privacy settings, and Studio integration.
    """

    __tablename__ = "user_settings"

    # Primary key is user_id (one-to-one with User)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Notification preferences
    notification_preferences: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "email_new_follower": True,
            "email_new_comment": True,
            "email_video_processed": True,
            "email_payout_complete": True,
            "email_marketing": False,
            "push_enabled": True,
        },
        nullable=False,
    )

    # Privacy settings
    privacy_settings: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "show_watch_history": False,
            "show_liked_videos": False,
            "allow_comments": True,
            "show_subscriber_count": True,
        },
        nullable=False,
    )

    # Display preferences
    display_preferences: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "theme": "system",  # light, dark, system
            "autoplay": True,
            "default_quality": "auto",
            "captions_enabled": False,
        },
        nullable=False,
    )

    # Studio integration
    studio_linked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    studio_license_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    studio_linked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Two-factor authentication
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    two_factor_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationship back to user
    user: Mapped["User"] = relationship(
        "User",
        back_populates="settings",
    )

    def __repr__(self) -> str:
        return f"<UserSettings (user={self.user_id})>"
