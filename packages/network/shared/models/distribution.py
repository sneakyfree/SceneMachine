"""
Distribution models for SceneMachine Network.

Includes StoryHeaven (short-form) and MovieHeaven (long-form) distribution channels.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
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
    from .video import Video


class DistributionChannel(enum.Enum):
    """Distribution channel for content."""

    STORY_HEAVEN = "story_heaven"  # Short-form (<10 min)
    MOVIE_HEAVEN = "movie_heaven"  # Long-form (10+ min)


class ContentFormat(enum.Enum):
    """Video format/aspect ratio."""

    VERTICAL_916 = "9:16"  # Vertical (mobile-first)
    SQUARE_11 = "1:1"  # Square
    HORIZONTAL_169 = "16:9"  # Traditional widescreen
    CINEMATIC_235 = "2.35:1"  # Cinematic widescreen
    IMAX_143 = "1.43:1"  # IMAX format


class PPVStatus(enum.Enum):
    """Pay-per-view purchase status."""

    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class SubscriptionTier(enum.Enum):
    """MovieHeaven subscription tiers."""

    BASIC = "basic"  # $9.99/mo - 720p, ads
    PREMIUM = "premium"  # $14.99/mo - 1080p, no ads
    ULTIMATE = "ultimate"  # $19.99/mo - 4K, downloads, early access


class FestivalStatus(enum.Enum):
    """Film festival status."""

    UPCOMING = "upcoming"
    SUBMISSIONS_OPEN = "submissions_open"
    SUBMISSIONS_CLOSED = "submissions_closed"
    JUDGING = "judging"
    COMPLETED = "completed"


class SubmissionStatus(enum.Enum):
    """Festival submission status."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SELECTED = "selected"
    FINALIST = "finalist"
    WINNER = "winner"
    REJECTED = "rejected"


class PremiereType(enum.Enum):
    """Premiere event type."""

    WORLD_PREMIERE = "world_premiere"
    EXCLUSIVE_PREVIEW = "exclusive_preview"
    LIVE_PREMIERE = "live_premiere"
    FESTIVAL_PREMIERE = "festival_premiere"


# ============================================================================
# StoryHeaven Models (Short-form)
# ============================================================================


class StoryHeavenPost(Base, UUIDMixin, TimestampMixin):
    """
    StoryHeaven short-form content post.

    Optimized for mobile consumption (<10 min).
    """

    __tablename__ = "story_heaven_posts"

    # Link to main video
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Creator
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Format optimization
    format: Mapped[ContentFormat] = mapped_column(
        Enum(ContentFormat),
        default=ContentFormat.VERTICAL_916,
        nullable=False,
    )
    optimized_for_mobile: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Audio/Sound
    original_sound_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_heaven_sounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    uses_trending_sound: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Engagement metrics (denormalized)
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
    share_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    comment_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    duet_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    save_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Discovery
    hashtags: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
    )
    trending_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    featured_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Virality tracking
    viral_threshold_reached: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    viral_reached_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Settings
    allow_duets: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    allow_sound_reuse: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    allow_comments: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_story_heaven_posts_trending", "trending_score", postgresql_using="btree"),
        Index("ix_story_heaven_posts_created", "created_at", postgresql_using="btree"),
        Index("ix_story_heaven_posts_viral", "viral_threshold_reached", "viral_reached_at"),
    )

    def __repr__(self) -> str:
        return f"<StoryHeavenPost {self.id} ({self.view_count} views)>"


class StoryHeavenSound(Base, UUIDMixin, TimestampMixin):
    """
    Reusable sound/audio track for StoryHeaven.

    Enables sound reuse and trending audio discovery.
    """

    __tablename__ = "story_heaven_sounds"

    # Source
    original_video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sound info
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    artist: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    audio_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Usage stats
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_trending: Mapped[bool] = mapped_column(
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

    __table_args__ = (
        Index("ix_story_heaven_sounds_trending", "is_trending", "usage_count"),
    )

    def __repr__(self) -> str:
        return f"<StoryHeavenSound {self.title} ({self.usage_count} uses)>"


class StoryHeavenDuet(Base, UUIDMixin, TimestampMixin):
    """
    Duet/Response video relationship.

    Links response videos to original content.
    """

    __tablename__ = "story_heaven_duets"

    original_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_heaven_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_heaven_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_story_heaven_duets_original", "original_post_id"),
    )


# ============================================================================
# MovieHeaven Models (Long-form)
# ============================================================================


class MovieHeavenContent(Base, UUIDMixin, TimestampMixin):
    """
    MovieHeaven long-form content (films, series).

    Supports PPV, subscriptions, and festival circuit.
    """

    __tablename__ = "movie_heaven_content"

    # Link to main video
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Creator
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content classification
    format: Mapped[ContentFormat] = mapped_column(
        Enum(ContentFormat),
        default=ContentFormat.HORIZONTAL_169,
        nullable=False,
    )
    is_feature_film: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    runtime_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Pricing & Access
    ppv_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    rental_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    rental_duration_hours: Mapped[int] = mapped_column(
        Integer,
        default=48,
        nullable=False,
    )
    minimum_tier: Mapped[Optional[SubscriptionTier]] = mapped_column(
        Enum(SubscriptionTier),
        nullable=True,
    )
    is_free: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Premiere
    premiere_type: Mapped[Optional[PremiereType]] = mapped_column(
        Enum(PremiereType),
        nullable=True,
    )
    premiere_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    premiere_ended: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Festival circuit
    festival_circuit_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    festival_wins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    festival_nominations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Revenue tracking
    total_ppv_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    total_rental_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    total_purchases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_rentals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Quality tiers available
    available_qualities: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        default=list,
        nullable=False,
    )
    has_4k: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    has_hdr: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    has_dolby_atmos: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Critic/Audience scores
    critic_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    audience_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Metadata
    genres: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
    )
    cast_names: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
    )
    crew_credits: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_movie_heaven_content_premiere", "premiere_date"),
        Index("ix_movie_heaven_content_revenue", "total_ppv_revenue"),
        Index("ix_movie_heaven_content_scores", "audience_score", "critic_score"),
    )

    def __repr__(self) -> str:
        return f"<MovieHeavenContent {self.id} ({self.runtime_minutes} min)>"


class PPVPurchase(Base, UUIDMixin, TimestampMixin):
    """
    Pay-per-view purchase record.

    Tracks purchases and rentals of MovieHeaven content.
    """

    __tablename__ = "ppv_purchases"

    # Buyer
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("movie_heaven_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Purchase details
    is_rental: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    price_paid: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )

    # Status
    status: Mapped[PPVStatus] = mapped_column(
        Enum(PPVStatus),
        default=PPVStatus.COMPLETED,
        nullable=False,
    )

    # Rental expiry
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Payment
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_ppv_purchases_user_content", "user_id", "content_id"),
        Index("ix_ppv_purchases_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<PPVPurchase {self.id} {'rental' if self.is_rental else 'purchase'}>"


class MovieHeavenSubscription(Base, UUIDMixin, TimestampMixin):
    """
    MovieHeaven subscription record.

    Tracks user subscriptions and access levels.
    """

    __tablename__ = "movie_heaven_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Billing
    monthly_price: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
    )
    billing_cycle_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    next_billing_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Stripe
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_movie_heaven_subs_active", "is_active", "tier"),
    )

    def __repr__(self) -> str:
        return f"<MovieHeavenSubscription {self.tier.value} ({'active' if self.is_active else 'inactive'})>"


# ============================================================================
# Film Festival Models
# ============================================================================


class FilmFestival(Base, UUIDMixin, TimestampMixin):
    """
    Partner film festival.

    Enables content submission to virtual film festivals.
    """

    __tablename__ = "film_festivals"

    # Festival info
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    website_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Status
    status: Mapped[FestivalStatus] = mapped_column(
        Enum(FestivalStatus),
        default=FestivalStatus.UPCOMING,
        nullable=False,
    )

    # Dates
    submission_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    submission_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    event_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    event_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Submission rules
    submission_fee: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    max_runtime_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    min_runtime_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    accepted_genres: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
    )
    requires_studio_content: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Prizes
    grand_prize_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    total_prize_pool: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    prize_breakdown: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Stats
    submission_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_film_festivals_status", "status", "event_start"),
    )

    def __repr__(self) -> str:
        return f"<FilmFestival {self.name} ({self.status.value})>"


class FestivalSubmission(Base, UUIDMixin, TimestampMixin):
    """
    Film festival submission.

    Tracks content submitted to festivals.
    """

    __tablename__ = "festival_submissions"

    # Festival & Content
    festival_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("film_festivals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("movie_heaven_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.SUBMITTED,
        nullable=False,
    )

    # Submission details
    fee_paid: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    director_statement: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Judging
    judge_scores: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    average_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    judge_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Award
    award_received: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    prize_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_festival_submissions_festival_status", "festival_id", "status"),
        Index("ix_festival_submissions_content", "content_id"),
    )

    def __repr__(self) -> str:
        return f"<FestivalSubmission {self.id} ({self.status.value})>"


# ============================================================================
# Export Helper
# ============================================================================


class StudioExport(Base, UUIDMixin, TimestampMixin):
    """
    Track exports from Scene Machine Studio to distribution channels.

    Links desktop studio projects to network distribution.
    """

    __tablename__ = "studio_exports"

    # Studio project reference
    studio_project_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    studio_user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    # Network content reference
    video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Distribution channel
    channel: Mapped[DistributionChannel] = mapped_column(
        Enum(DistributionChannel),
        nullable=False,
    )

    # Export details
    original_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    exported_formats: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        default=list,
        nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Optimization
    auto_formatted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    format_adjustments: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Status
    export_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_studio_exports_project", "studio_project_id"),
        Index("ix_studio_exports_channel", "channel", "published"),
    )

    def __repr__(self) -> str:
        return f"<StudioExport {self.studio_project_id} -> {self.channel.value}>"
