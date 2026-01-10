"""
CoreCast events and badge system models.

CoreCast is a monthly competition with $100k prize pool.
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .user import User
    from .video import Video


class EventStatus(enum.Enum):
    """CoreCast event status."""

    UPCOMING = "upcoming"
    SUBMISSIONS_OPEN = "submissions_open"
    VOTING = "voting"
    JUDGING = "judging"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SubmissionPhase(enum.Enum):
    """Submission phase in competition."""

    SUBMITTED = "submitted"
    QUALIFIED = "qualified"
    TOP_100 = "top_100"
    TOP_50 = "top_50"
    TOP_25 = "top_25"
    TOP_10 = "top_10"
    FINALIST = "finalist"
    WINNER = "winner"
    ELIMINATED = "eliminated"


class BadgeType(enum.Enum):
    """Badge types awarded in CoreCast."""

    # Competition badges
    GOLD = "gold"  # 1st place
    SILVER = "silver"  # 2nd place
    BRONZE = "bronze"  # 3rd place
    FINALIST = "finalist"  # Top 10
    TOP_25 = "top_25"
    TOP_50 = "top_50"
    TOP_100 = "top_100"
    PARTICIPANT = "participant"  # Submitted

    # Special recognition
    PEOPLES_CHOICE = "peoples_choice"  # Most public votes
    RISING_STAR = "rising_star"  # Best new creator
    INNOVATION = "innovation"  # Most innovative entry
    TECHNICAL = "technical"  # Best technical achievement
    STORYTELLING = "storytelling"  # Best storytelling
    VISUAL = "visual"  # Best visual design

    # Performers Association tiers
    EMERGING = "emerging"
    ESTABLISHED = "established"
    PROFESSIONAL = "professional"
    ELITE = "elite"
    LEGEND = "legend"


class VoteType(enum.Enum):
    """Type of vote cast."""

    PUBLIC = "public"  # General audience vote
    JUDGE = "judge"  # Official judge vote
    PEER = "peer"  # Creator peer vote


# Badge display metadata
BADGE_DISPLAY = {
    BadgeType.GOLD: {"emoji": "🥇", "name": "Gold", "color": "#FFD700"},
    BadgeType.SILVER: {"emoji": "🥈", "name": "Silver", "color": "#C0C0C0"},
    BadgeType.BRONZE: {"emoji": "🥉", "name": "Bronze", "color": "#CD7F32"},
    BadgeType.FINALIST: {"emoji": "🏅", "name": "Finalist", "color": "#4169E1"},
    BadgeType.TOP_25: {"emoji": "🎯", "name": "Top 25", "color": "#32CD32"},
    BadgeType.TOP_50: {"emoji": "✨", "name": "Top 50", "color": "#9370DB"},
    BadgeType.TOP_100: {"emoji": "⭐", "name": "Top 100", "color": "#87CEEB"},
    BadgeType.PARTICIPANT: {"emoji": "🎬", "name": "Participant", "color": "#808080"},
    BadgeType.PEOPLES_CHOICE: {"emoji": "💫", "name": "People's Choice", "color": "#FF69B4"},
    BadgeType.RISING_STAR: {"emoji": "🌟", "name": "Rising Star", "color": "#FFB6C1"},
    BadgeType.INNOVATION: {"emoji": "💡", "name": "Innovation", "color": "#00CED1"},
    BadgeType.TECHNICAL: {"emoji": "⚙️", "name": "Technical Excellence", "color": "#708090"},
    BadgeType.STORYTELLING: {"emoji": "📖", "name": "Best Storytelling", "color": "#8B4513"},
    BadgeType.VISUAL: {"emoji": "🎨", "name": "Visual Excellence", "color": "#FF6347"},
    BadgeType.EMERGING: {"emoji": "🌱", "name": "Emerging", "color": "#90EE90"},
    BadgeType.ESTABLISHED: {"emoji": "🌿", "name": "Established", "color": "#3CB371"},
    BadgeType.PROFESSIONAL: {"emoji": "🌳", "name": "Professional", "color": "#228B22"},
    BadgeType.ELITE: {"emoji": "👑", "name": "Elite", "color": "#9932CC"},
    BadgeType.LEGEND: {"emoji": "🏆", "name": "Legend", "color": "#FFD700"},
}

# Prize distribution ($100k pool)
PRIZE_DISTRIBUTION = {
    1: Decimal("50000.00"),  # 1st: 50%
    2: Decimal("25000.00"),  # 2nd: 25%
    3: Decimal("10000.00"),  # 3rd: 10%
    4: Decimal("3750.00"),  # 4th-10th split remaining 15%
    5: Decimal("2500.00"),
    6: Decimal("1875.00"),
    7: Decimal("1500.00"),
    8: Decimal("1250.00"),
    9: Decimal("1125.00"),
    10: Decimal("1000.00"),
}


class CoreCastEvent(Base, UUIDMixin, TimestampMixin):
    """
    CoreCast monthly competition.

    $100k prize pool distributed to top 10 finishers.
    """

    __tablename__ = "corecast_events"

    # Event info
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    theme: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    banner_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Month/Year identifier
    month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Status
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus),
        default=EventStatus.UPCOMING,
        nullable=False,
    )

    # Dates
    submissions_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    submissions_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    voting_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    voting_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    results_announcement: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Prize pool
    total_prize_pool: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("100000.00"),
        nullable=False,
    )
    prize_distribution: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Rules
    max_submissions_per_user: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    min_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )
    max_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=600,  # 10 minutes
        nullable=False,
    )
    requires_studio_content: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Stats
    submission_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    vote_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    unique_voters: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Sponsors
    sponsors: Mapped[list[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Judges (list of user UUIDs who can cast judge votes)
    judge_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String(36)),
        default=list,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_corecast_month_year"),
        Index("ix_corecast_events_status", "status"),
        Index("ix_corecast_events_dates", "submissions_start", "voting_end"),
    )

    def __repr__(self) -> str:
        return f"<CoreCastEvent {self.name} ({self.month}/{self.year})>"


class CoreCastSubmission(Base, UUIDMixin, TimestampMixin):
    """
    Submission to a CoreCast competition.

    Links a video to an event with tracking for votes and prizes.
    """

    __tablename__ = "corecast_submissions"

    # Event & Content
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corecast_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Submission details
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Phase & Status
    phase: Mapped[SubmissionPhase] = mapped_column(
        Enum(SubmissionPhase),
        default=SubmissionPhase.SUBMITTED,
        nullable=False,
    )
    is_qualified: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    disqualification_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Voting scores
    public_votes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    judge_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    peer_votes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Combined score (calculated)
    # Formula: public_votes_normalized * 0.3 + judge_score * 0.5 + peer_votes_normalized * 0.2
    combined_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Final placement
    final_rank: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Prize
    prize_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    prize_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Special recognition
    special_badges: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("event_id", "video_id", name="uq_corecast_event_video"),
        Index("ix_corecast_submissions_scores", "combined_score", "public_votes"),
        Index("ix_corecast_submissions_phase", "event_id", "phase"),
    )

    def __repr__(self) -> str:
        return f"<CoreCastSubmission {self.title} (rank: {self.final_rank})>"


class CoreCastVote(Base, UUIDMixin, TimestampMixin):
    """
    Vote cast in a CoreCast competition.

    Tracks public, judge, and peer votes.
    """

    __tablename__ = "corecast_votes"

    # Vote target
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corecast_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Vote type
    vote_type: Mapped[VoteType] = mapped_column(
        Enum(VoteType),
        default=VoteType.PUBLIC,
        nullable=False,
    )

    # Score (for judge votes)
    score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "submission_id", "voter_id", "vote_type", name="uq_corecast_vote_unique"
        ),
        Index("ix_corecast_votes_submission", "submission_id"),
    )

    def __repr__(self) -> str:
        return f"<CoreCastVote {self.vote_type.value} on {self.submission_id}>"


class UserBadge(Base, UUIDMixin, TimestampMixin):
    """
    Badge awarded to a user.

    Badges are earned through CoreCast participation and Performers Association status.
    """

    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Badge info
    badge_type: Mapped[BadgeType] = mapped_column(
        Enum(BadgeType),
        nullable=False,
    )

    # Context (which event, if applicable)
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corecast_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Display
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Metadata
    award_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_user_badges_user", "user_id", "badge_type"),
    )

    @property
    def display_info(self) -> dict:
        """Get badge display information."""
        return BADGE_DISPLAY.get(
            self.badge_type,
            {"emoji": "🏅", "name": self.badge_type.value, "color": "#808080"},
        )

    def __repr__(self) -> str:
        return f"<UserBadge {self.badge_type.value} for user {self.user_id}>"


class PrizeDistribution(Base, UUIDMixin, TimestampMixin):
    """
    Prize payout record.

    Tracks distribution of prize money to winners.
    """

    __tablename__ = "prize_distributions"

    # Context
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corecast_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("corecast_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )

    # Placement
    final_rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    badge_awarded: Mapped[BadgeType] = mapped_column(
        Enum(BadgeType),
        nullable=False,
    )

    # Payment status
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_prize_distributions_event", "event_id", "final_rank"),
    )

    def __repr__(self) -> str:
        return f"<PrizeDistribution ${self.amount} to {self.recipient_id}>"


# ============================================================================
# Performers Association Models
# ============================================================================


class PerformersAssociationTier(enum.Enum):
    """Performers Association membership tiers."""

    EMERGING = "emerging"
    ESTABLISHED = "established"
    PROFESSIONAL = "professional"
    ELITE = "elite"
    LEGEND = "legend"


# Tier requirements and benefits
TIER_REQUIREMENTS = {
    PerformersAssociationTier.EMERGING: {
        "min_videos": 1,
        "min_views": 0,
        "min_earnings": Decimal("0.00"),
        "min_corecast_wins": 0,
    },
    PerformersAssociationTier.ESTABLISHED: {
        "min_videos": 5,
        "min_views": 10000,
        "min_earnings": Decimal("100.00"),
        "min_corecast_wins": 0,
    },
    PerformersAssociationTier.PROFESSIONAL: {
        "min_videos": 20,
        "min_views": 100000,
        "min_earnings": Decimal("5000.00"),
        "min_corecast_wins": 0,
    },
    PerformersAssociationTier.ELITE: {
        "min_videos": 50,
        "min_views": 1000000,
        "min_earnings": Decimal("50000.00"),
        "min_corecast_wins": 1,
    },
    PerformersAssociationTier.LEGEND: {
        "min_videos": 100,
        "min_views": 10000000,
        "min_earnings": Decimal("500000.00"),
        "min_corecast_wins": 3,
    },
}

TIER_BENEFITS = {
    PerformersAssociationTier.EMERGING: {
        "fee_reduction_percent": 0,
        "badge": BadgeType.EMERGING,
        "benefits": ["Basic badge", "Community access"],
    },
    PerformersAssociationTier.ESTABLISHED: {
        "fee_reduction_percent": 2,
        "badge": BadgeType.ESTABLISHED,
        "benefits": ["-2% platform fee", "Featured placement", "Priority support"],
    },
    PerformersAssociationTier.PROFESSIONAL: {
        "fee_reduction_percent": 5,
        "badge": BadgeType.PROFESSIONAL,
        "benefits": ["-5% platform fee", "Legal templates", "Mentorship access"],
    },
    PerformersAssociationTier.ELITE: {
        "fee_reduction_percent": 10,
        "badge": BadgeType.ELITE,
        "benefits": ["-10% platform fee", "Health insurance subsidy", "Revenue advances"],
    },
    PerformersAssociationTier.LEGEND: {
        "fee_reduction_percent": 15,
        "badge": BadgeType.LEGEND,
        "benefits": ["-15% platform fee", "Revenue guarantees", "Executive producer credits"],
    },
}


class PerformersAssociationMembership(Base, UUIDMixin, TimestampMixin):
    """
    Performers Association membership.

    Tracks creator's tier status and benefits.
    """

    __tablename__ = "performers_association_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Current tier
    tier: Mapped[PerformersAssociationTier] = mapped_column(
        Enum(PerformersAssociationTier),
        default=PerformersAssociationTier.EMERGING,
        nullable=False,
    )

    # Stats (cached for quick tier checks)
    total_videos: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_views: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    total_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    corecast_wins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    corecast_participations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Tier history
    tier_achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    previous_tier: Mapped[Optional[PerformersAssociationTier]] = mapped_column(
        Enum(PerformersAssociationTier),
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    suspended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    suspension_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_performers_association_tier", "tier", "is_active"),
    )

    @property
    def fee_reduction(self) -> int:
        """Get fee reduction percentage for current tier."""
        return TIER_BENEFITS.get(self.tier, {}).get("fee_reduction_percent", 0)

    @property
    def benefits(self) -> list[str]:
        """Get benefits for current tier."""
        return TIER_BENEFITS.get(self.tier, {}).get("benefits", [])

    def __repr__(self) -> str:
        return f"<PerformersAssociationMembership {self.tier.value} for user {self.user_id}>"
