"""
Pydantic schemas for discovery service requests and responses.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ...shared.models import ContentType


class VideoSearchResult(BaseModel):
    """Video result from search."""

    id: uuid.UUID
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: int
    creator_id: uuid.UUID
    creator_name: str
    creator_avatar: Optional[str]
    content_type: ContentType
    view_count: int
    like_count: int
    quality_score: float
    published_at: datetime
    made_with_studio: bool

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Response for search query."""

    results: list[VideoSearchResult]
    total: int
    page: int
    per_page: int
    has_more: bool
    query: str
    filters_applied: dict


class CreatorSearchResult(BaseModel):
    """Creator result from search."""

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    is_verified: bool
    subscriber_count: int
    video_count: int
    total_views: int

    class Config:
        from_attributes = True


class CreatorSearchResponse(BaseModel):
    """Response for creator search."""

    results: list[CreatorSearchResult]
    total: int
    page: int
    per_page: int
    has_more: bool


class CategoryResponse(BaseModel):
    """Response for a content category."""

    content_type: ContentType
    display_name: str
    video_count: int
    recent_videos: list[VideoSearchResult]


class CategoryListResponse(BaseModel):
    """Response for category listing."""

    categories: list[CategoryResponse]


class TrendingTagResponse(BaseModel):
    """Trending tag info."""

    tag: str
    video_count: int
    view_count: int
    trend_score: float


class TrendingTagsResponse(BaseModel):
    """Response for trending tags."""

    tags: list[TrendingTagResponse]


class RecommendationResponse(BaseModel):
    """Response for video recommendations."""

    videos: list[VideoSearchResult]
    reason: str  # "similar_to", "because_you_watched", "trending_in_genre"


class AutocompleteResponse(BaseModel):
    """Response for search autocomplete."""

    suggestions: list[str]
    videos: list[VideoSearchResult]
    creators: list[CreatorSearchResult]
