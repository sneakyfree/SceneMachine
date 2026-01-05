"""
Pydantic schemas for streaming service requests and responses.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HeartbeatRequest(BaseModel):
    """Request for playback heartbeat."""

    session_token: str
    position_seconds: int = Field(..., ge=0)
    quality_level: Optional[str] = None
    buffering_count: int = Field(0, ge=0)
    is_playing: bool = True


class HeartbeatResponse(BaseModel):
    """Response for playback heartbeat."""

    success: bool
    session_id: uuid.UUID
    watch_time_seconds: int


class StartSessionRequest(BaseModel):
    """Request to start a new watch session."""

    video_id: uuid.UUID
    quality_level: Optional[str] = None
    referrer: Optional[str] = None
    traffic_source: Optional[str] = None


class StartSessionResponse(BaseModel):
    """Response with new session token."""

    session_token: str
    session_id: uuid.UUID
    video_id: uuid.UUID
    resume_position: int  # Position to resume from (if any)


class EndSessionRequest(BaseModel):
    """Request to end a watch session."""

    session_token: str
    final_position_seconds: int = Field(..., ge=0)
    completed: bool = False


class EndSessionResponse(BaseModel):
    """Response for ending a session."""

    success: bool
    total_watch_time_seconds: int
    view_counted: bool


class WatchProgressResponse(BaseModel):
    """Response for watch progress."""

    video_id: uuid.UUID
    progress_seconds: int
    duration_seconds: int
    watch_percent: float
    completed: bool
    last_watched_at: datetime


class WatchHistoryResponse(BaseModel):
    """Response for watch history list."""

    items: list[WatchProgressResponse]
    total: int
    page: int
    per_page: int


class ManifestResponse(BaseModel):
    """Response with streaming manifest URL."""

    video_id: uuid.UUID
    manifest_url: str
    format: str  # "hls" or "dash"
    available_qualities: list[str]
    duration_seconds: int
    thumbnail_url: Optional[str]


class StreamingStatsResponse(BaseModel):
    """Response with real-time streaming stats."""

    video_id: uuid.UUID
    concurrent_viewers: int
    total_views_today: int
    average_watch_time_seconds: int
    average_quality: Optional[str]


class QualityInfo(BaseModel):
    """Information about a quality level."""

    name: str  # "1080p", "720p", etc.
    width: int
    height: int
    bitrate_kbps: int
    available: bool
