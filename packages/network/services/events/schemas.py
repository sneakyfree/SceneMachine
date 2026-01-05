"""Schemas for events service."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# CoreCast Event Schemas
# ============================================================================


class CoreCastEventCreate(BaseModel):
    """Create a CoreCast event."""

    name: str
    description: Optional[str] = None
    theme: Optional[str] = None
    banner_url: Optional[str] = None

    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2024)

    submissions_start: datetime
    submissions_end: datetime
    voting_start: datetime
    voting_end: datetime
    results_announcement: datetime

    total_prize_pool: Decimal = Decimal("100000.00")
    prize_distribution: dict = Field(default_factory=dict)

    max_submissions_per_user: int = 3
    min_duration_seconds: int = 30
    max_duration_seconds: int = 600
    requires_studio_content: bool = True

    sponsors: list[dict] = Field(default_factory=list)


class CoreCastEventResponse(BaseModel):
    """CoreCast event response."""

    id: UUID
    name: str
    description: Optional[str]
    theme: Optional[str]
    banner_url: Optional[str]

    month: int
    year: int
    status: str

    submissions_start: datetime
    submissions_end: datetime
    voting_start: datetime
    voting_end: datetime
    results_announcement: datetime

    total_prize_pool: Decimal
    prize_distribution: dict

    max_submissions_per_user: int
    min_duration_seconds: int
    max_duration_seconds: int
    requires_studio_content: bool

    submission_count: int
    vote_count: int
    unique_voters: int

    sponsors: list[dict]

    created_at: datetime

    class Config:
        from_attributes = True


class CoreCastSubmissionCreate(BaseModel):
    """Create a submission to CoreCast."""

    event_id: UUID
    video_id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class CoreCastSubmissionResponse(BaseModel):
    """CoreCast submission response."""

    id: UUID
    event_id: UUID
    video_id: UUID
    creator_id: UUID
    title: str
    description: Optional[str]
    category: Optional[str]

    phase: str
    is_qualified: bool
    disqualification_reason: Optional[str]

    public_votes: int
    judge_score: Optional[float]
    peer_votes: int
    combined_score: float

    final_rank: Optional[int]
    prize_amount: Decimal
    prize_paid: bool
    special_badges: list[str]

    created_at: datetime

    class Config:
        from_attributes = True


class VoteRequest(BaseModel):
    """Request to vote on a submission."""

    submission_id: UUID
    score: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = None


class VoteResponse(BaseModel):
    """Vote response."""

    id: UUID
    submission_id: UUID
    voter_id: UUID
    vote_type: str
    score: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Badge Schemas
# ============================================================================


class BadgeInfo(BaseModel):
    """Badge display information."""

    badge_type: str
    emoji: str
    name: str
    color: str
    event_id: Optional[UUID] = None
    awarded_at: datetime
    is_featured: bool
    award_reason: Optional[str] = None


class UserBadgeResponse(BaseModel):
    """User badge response."""

    id: UUID
    user_id: UUID
    badge_type: str
    event_id: Optional[UUID]
    awarded_at: datetime
    is_featured: bool
    award_reason: Optional[str]
    display_info: dict

    created_at: datetime

    class Config:
        from_attributes = True


class BadgeAwardRequest(BaseModel):
    """Award a badge to a user (admin)."""

    user_id: UUID
    badge_type: str
    event_id: Optional[UUID] = None
    award_reason: Optional[str] = None


# ============================================================================
# Prize Distribution Schemas
# ============================================================================


class PrizeDistributionResponse(BaseModel):
    """Prize distribution response."""

    id: UUID
    event_id: UUID
    submission_id: UUID
    recipient_id: UUID
    amount: Decimal
    currency: str
    final_rank: int
    badge_awarded: str
    status: str
    paid_at: Optional[datetime]
    payment_reference: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Performers Association Schemas
# ============================================================================


class PerformersAssociationResponse(BaseModel):
    """Performers Association membership response."""

    id: UUID
    user_id: UUID
    tier: str
    total_videos: int
    total_views: int
    total_earnings: Decimal
    corecast_wins: int
    corecast_participations: int
    tier_achieved_at: datetime
    previous_tier: Optional[str]
    is_active: bool
    fee_reduction: int
    benefits: list[str]

    created_at: datetime

    class Config:
        from_attributes = True


class TierRequirements(BaseModel):
    """Tier requirements."""

    tier: str
    min_videos: int
    min_views: int
    min_earnings: Decimal
    min_corecast_wins: int


class TierProgress(BaseModel):
    """Progress towards next tier."""

    current_tier: str
    next_tier: Optional[str]
    videos_progress: float  # 0-100%
    views_progress: float
    earnings_progress: float
    wins_progress: float
    overall_progress: float


# ============================================================================
# Leaderboard Schemas
# ============================================================================


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""

    rank: int
    submission_id: UUID
    creator_id: UUID
    creator_name: str
    title: str
    public_votes: int
    judge_score: Optional[float]
    combined_score: float
    badges: list[str]


class LeaderboardResponse(BaseModel):
    """Leaderboard response."""

    event_id: UUID
    event_name: str
    phase: str
    entries: list[LeaderboardEntry]
    total_entries: int
    last_updated: datetime
