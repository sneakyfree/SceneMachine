"""
Pydantic schemas for content service requests and responses.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ...shared.models import ContentType, MonetizationType, TranscodingStatus, VideoStatus


class VideoCreateRequest(BaseModel):
    """Request schema for creating a video."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    content_type: ContentType = ContentType.OTHER
    monetization_type: MonetizationType = MonetizationType.FREE_AD
    ticket_price: Optional[Decimal] = Field(None, ge=0, le=1000)
    series_id: Optional[uuid.UUID] = None
    episode_number: Optional[int] = Field(None, ge=1)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_age_restricted: bool = False

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return [tag.lower().strip()[:50] for tag in v if tag.strip()][:20]

    @field_validator("ticket_price")
    @classmethod
    def validate_ticket_price(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        data = info.data
        if data.get("monetization_type") == MonetizationType.PAID and v is None:
            raise ValueError("Ticket price required for paid content")
        return v


class VideoUpdateRequest(BaseModel):
    """Request schema for updating a video."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    monetization_type: Optional[MonetizationType] = None
    ticket_price: Optional[Decimal] = Field(None, ge=0, le=1000)
    tags: Optional[list[str]] = None
    is_age_restricted: Optional[bool] = None
    scheduled_publish_at: Optional[datetime] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        return [tag.lower().strip()[:50] for tag in v if tag.strip()][:20]


class VideoResponse(BaseModel):
    """Response schema for video data."""

    id: uuid.UUID
    creator_id: uuid.UUID
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: int
    content_type: ContentType
    series_id: Optional[uuid.UUID]
    episode_number: Optional[int]
    made_with_studio: bool
    monetization_type: MonetizationType
    ticket_price: Optional[Decimal]
    status: VideoStatus
    transcoding_status: TranscodingStatus
    transcoding_progress: int
    published_at: Optional[datetime]
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    tags: list[str]
    quality_score: float
    is_age_restricted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Response schema for video list."""

    videos: list[VideoResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class UploadInitResponse(BaseModel):
    """Response for upload initialization."""

    video_id: uuid.UUID
    upload_url: str
    upload_key: str
    expires_at: datetime


class UploadCompleteRequest(BaseModel):
    """Request to mark upload as complete."""

    video_id: uuid.UUID
    file_size: int
    content_type: str


class TranscodingStatusResponse(BaseModel):
    """Response for transcoding status."""

    video_id: uuid.UUID
    status: TranscodingStatus
    progress: int
    error: Optional[str]
    variants: dict  # {quality: {width, height, ready}}


class PublishRequest(BaseModel):
    """Request to publish a video."""

    scheduled_at: Optional[datetime] = None


class SeriesCreateRequest(BaseModel):
    """Request schema for creating a series."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)


class SeriesUpdateRequest(BaseModel):
    """Request schema for updating a series."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    is_complete: Optional[bool] = None


class SeriesResponse(BaseModel):
    """Response schema for series data."""

    id: uuid.UUID
    creator_id: uuid.UUID
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    episode_count: int
    total_views: int
    is_complete: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudioUploadRequest(BaseModel):
    """Request for uploading from Studio."""

    project_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    content_type: ContentType = ContentType.FILM
    monetization_type: MonetizationType = MonetizationType.FREE_AD
    ticket_price: Optional[Decimal] = Field(None, ge=0, le=1000)
    tags: list[str] = Field(default_factory=list)


class VideoStatsResponse(BaseModel):
    """Response for video analytics."""

    video_id: uuid.UUID
    period: str  # "day", "week", "month", "all"
    views: int
    unique_viewers: int
    watch_time_minutes: int
    average_watch_percent: float
    likes: int
    comments: int
    shares: int
    ad_revenue: Decimal
    ticket_revenue: Decimal
    tip_revenue: Decimal
    total_revenue: Decimal


class CostBreakdownResponse(BaseModel):
    """Response for video cost breakdown."""

    video_id: uuid.UUID
    month: str
    storage_gb: float
    storage_cost: Decimal
    bandwidth_gb: float
    bandwidth_cost: Decimal
    processing_cost: Decimal
    total_cost: Decimal
    revenue: Decimal
    net_profit: Decimal
