"""
Pydantic schemas for Studio integration service.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from ...shared.models import ContentType, MonetizationType, VideoStatus


class StudioPublishRequest(BaseModel):
    """Request to publish from Studio."""

    # Project info
    project_id: str = Field(..., description="Studio project ID")
    project_title: str = Field(..., description="Original project title")

    # Video metadata
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    content_type: ContentType = ContentType.FILM
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_age_restricted: bool = False

    # Monetization
    monetization_type: MonetizationType = MonetizationType.FREE_AD
    ticket_price: Optional[Decimal] = Field(None, ge=0, le=1000)

    # Video file info
    file_size_bytes: int = Field(..., gt=0)
    duration_seconds: int = Field(..., gt=0)
    resolution_width: int = Field(..., ge=320)
    resolution_height: int = Field(..., ge=180)
    fps: float = Field(..., ge=1, le=120)
    codec: str = Field(default="h264")

    # Thumbnail
    has_thumbnail: bool = False

    # Auto-publish
    publish_immediately: bool = True
    scheduled_publish_at: Optional[datetime] = None


class StudioPublishResponse(BaseModel):
    """Response for Studio publish request."""

    video_id: uuid.UUID
    upload_url: str
    thumbnail_upload_url: Optional[str]
    upload_expires_at: datetime
    status: str

    class Config:
        from_attributes = True


class StudioUploadCompleteRequest(BaseModel):
    """Request to complete Studio upload."""

    video_id: uuid.UUID
    upload_successful: bool
    thumbnail_uploaded: bool = False


class StudioVideoStatusResponse(BaseModel):
    """Response for Studio video status check."""

    video_id: uuid.UUID
    status: VideoStatus
    transcoding_progress: int
    transcoding_status: str
    is_published: bool
    published_at: Optional[datetime]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    view_count: int
    like_count: int

    class Config:
        from_attributes = True


class StudioMyVideosResponse(BaseModel):
    """Response for listing Studio-created videos."""

    videos: list["StudioVideoSummary"]
    total: int
    page: int
    per_page: int


class StudioVideoSummary(BaseModel):
    """Summary of a Studio-created video."""

    video_id: uuid.UUID
    project_id: str
    title: str
    status: VideoStatus
    is_published: bool
    published_at: Optional[datetime]
    view_count: int
    like_count: int
    revenue: Decimal
    thumbnail_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StudioAnalyticsSummary(BaseModel):
    """Analytics summary for Studio users."""

    total_videos: int
    total_views: int
    total_watch_hours: float
    total_revenue: Decimal
    total_subscribers: int

    # Recent activity
    views_7d: int
    revenue_7d: Decimal
    new_subscribers_7d: int

    # Top performing
    top_video_title: Optional[str]
    top_video_views: int


class StudioAccountStatus(BaseModel):
    """Account status for Studio user."""

    user_id: uuid.UUID
    username: str
    email: str
    is_creator: bool
    is_verified: bool

    # Studio link status
    studio_linked: bool
    studio_license_key: Optional[str]
    studio_linked_at: Optional[datetime]

    # Monetization status
    monetization_enabled: bool
    stripe_connected: bool
    current_tier: int
    total_earnings: Decimal
    available_for_payout: Decimal


# Update forward references
StudioMyVideosResponse.model_rebuild()
