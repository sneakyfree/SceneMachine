"""Schemas for distribution service."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# StoryHeaven Schemas
# ============================================================================


class StoryHeavenPostCreate(BaseModel):
    """Create a StoryHeaven post from a video."""

    video_id: UUID
    format: str = "9:16"
    hashtags: list[str] = Field(default_factory=list)
    allow_duets: bool = True
    allow_sound_reuse: bool = True
    allow_comments: bool = True


class StoryHeavenPostResponse(BaseModel):
    """StoryHeaven post response."""

    id: UUID
    video_id: UUID
    creator_id: UUID
    format: str
    hashtags: list[str]
    view_count: int
    like_count: int
    share_count: int
    comment_count: int
    duet_count: int
    save_count: int
    trending_score: float
    viral_threshold_reached: bool
    allow_duets: bool
    allow_sound_reuse: bool
    allow_comments: bool
    created_at: datetime
    featured_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StoryHeavenSoundResponse(BaseModel):
    """StoryHeaven sound response."""

    id: UUID
    title: str
    artist: Optional[str]
    duration_seconds: int
    audio_url: str
    usage_count: int
    is_trending: bool
    creator_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TrendingFeedParams(BaseModel):
    """Parameters for trending feed."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    hashtag: Optional[str] = None
    sound_id: Optional[UUID] = None


class DuetCreate(BaseModel):
    """Create a duet response."""

    original_post_id: UUID
    response_video_id: UUID


# ============================================================================
# MovieHeaven Schemas
# ============================================================================


class MovieHeavenContentCreate(BaseModel):
    """Create MovieHeaven content from a video."""

    video_id: UUID
    format: str = "16:9"
    runtime_minutes: int
    is_feature_film: bool = False

    # Pricing
    ppv_price: Optional[Decimal] = None
    rental_price: Optional[Decimal] = None
    rental_duration_hours: int = 48
    minimum_tier: Optional[str] = None
    is_free: bool = False

    # Premiere
    premiere_type: Optional[str] = None
    premiere_date: Optional[datetime] = None

    # Metadata
    genres: list[str] = Field(default_factory=list)
    cast_names: list[str] = Field(default_factory=list)
    crew_credits: dict = Field(default_factory=dict)


class MovieHeavenContentResponse(BaseModel):
    """MovieHeaven content response."""

    id: UUID
    video_id: UUID
    creator_id: UUID
    format: str
    is_feature_film: bool
    runtime_minutes: int

    ppv_price: Optional[Decimal]
    rental_price: Optional[Decimal]
    rental_duration_hours: int
    minimum_tier: Optional[str]
    is_free: bool

    premiere_type: Optional[str]
    premiere_date: Optional[datetime]
    premiere_ended: bool

    festival_circuit_enabled: bool
    festival_wins: int
    festival_nominations: int

    total_ppv_revenue: Decimal
    total_rental_revenue: Decimal
    total_purchases: int
    total_rentals: int

    available_qualities: list[str]
    has_4k: bool
    has_hdr: bool
    has_dolby_atmos: bool

    critic_score: Optional[float]
    audience_score: Optional[float]
    review_count: int

    genres: list[str]
    cast_names: list[str]
    crew_credits: dict

    created_at: datetime

    class Config:
        from_attributes = True


class PPVPurchaseCreate(BaseModel):
    """Create a PPV purchase."""

    content_id: UUID
    is_rental: bool = False


class PPVPurchaseResponse(BaseModel):
    """PPV purchase response."""

    id: UUID
    user_id: UUID
    content_id: UUID
    is_rental: bool
    price_paid: Decimal
    currency: str
    status: str
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Create a subscription."""

    tier: str  # basic, premium, ultimate


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: UUID
    user_id: UUID
    tier: str
    is_active: bool
    monthly_price: Decimal
    billing_cycle_start: datetime
    next_billing_date: datetime
    cancelled_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ContentBrowseParams(BaseModel):
    """Parameters for browsing content."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    genre: Optional[str] = None
    is_feature_film: Optional[bool] = None
    min_rating: Optional[float] = None
    has_premiere: Optional[bool] = None
    is_free: Optional[bool] = None
    sort_by: str = "newest"  # newest, popular, rating, premiere


# ============================================================================
# Festival Schemas
# ============================================================================


class FilmFestivalCreate(BaseModel):
    """Create a film festival (admin only)."""

    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None

    submission_start: datetime
    submission_end: datetime
    event_start: datetime
    event_end: datetime

    submission_fee: Decimal = Decimal("0.00")
    max_runtime_minutes: Optional[int] = None
    min_runtime_minutes: Optional[int] = None
    accepted_genres: list[str] = Field(default_factory=list)
    requires_studio_content: bool = False

    grand_prize_amount: Decimal = Decimal("0.00")
    total_prize_pool: Decimal = Decimal("0.00")
    prize_breakdown: dict = Field(default_factory=dict)


class FilmFestivalResponse(BaseModel):
    """Film festival response."""

    id: UUID
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    website_url: Optional[str]
    status: str

    submission_start: datetime
    submission_end: datetime
    event_start: datetime
    event_end: datetime

    submission_fee: Decimal
    max_runtime_minutes: Optional[int]
    min_runtime_minutes: Optional[int]
    accepted_genres: list[str]
    requires_studio_content: bool

    grand_prize_amount: Decimal
    total_prize_pool: Decimal
    prize_breakdown: dict
    submission_count: int

    created_at: datetime

    class Config:
        from_attributes = True


class FestivalSubmissionCreate(BaseModel):
    """Submit content to a festival."""

    festival_id: UUID
    content_id: UUID
    director_statement: Optional[str] = None
    category: Optional[str] = None


class FestivalSubmissionResponse(BaseModel):
    """Festival submission response."""

    id: UUID
    festival_id: UUID
    content_id: UUID
    submitter_id: UUID
    status: str
    fee_paid: Decimal
    director_statement: Optional[str]
    category: Optional[str]
    average_score: Optional[float]
    award_received: Optional[str]
    prize_amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Export Schemas
# ============================================================================


class StudioExportCreate(BaseModel):
    """Create an export from Scene Machine Studio."""

    studio_project_id: str
    studio_user_id: str
    channel: str  # story_heaven, movie_heaven
    original_format: str
    duration_seconds: int
    file_size_bytes: int

    # Auto-formatting options
    auto_format: bool = True
    target_formats: list[str] = Field(default_factory=list)


class StudioExportResponse(BaseModel):
    """Studio export response."""

    id: UUID
    studio_project_id: str
    studio_user_id: str
    video_id: Optional[UUID]
    creator_id: UUID
    channel: str

    original_format: str
    exported_formats: list[str]
    duration_seconds: int
    file_size_bytes: int

    auto_formatted: bool
    format_adjustments: dict
    export_completed: bool
    published: bool

    created_at: datetime

    class Config:
        from_attributes = True


class FormatOptimizationRequest(BaseModel):
    """Request format optimization for a video."""

    video_id: UUID
    target_channel: str  # story_heaven, movie_heaven
    target_formats: list[str] = Field(default_factory=list)


class FormatOptimizationResponse(BaseModel):
    """Format optimization result."""

    original_format: str
    recommended_format: str
    adjustments_needed: dict
    estimated_processing_time_seconds: int
    quality_impact: str  # none, minimal, moderate, significant
