"""
Pydantic schemas for social service requests and responses.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ...shared.models import ReactionType


# Follow schemas
class FollowRequest(BaseModel):
    """Request to follow a user."""

    notify_on_upload: bool = True


class FollowResponse(BaseModel):
    """Response for follow status."""

    follower_id: uuid.UUID
    following_id: uuid.UUID
    notify_on_upload: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FollowerListResponse(BaseModel):
    """Response for follower/following list."""

    users: list["UserSummary"]
    total: int
    page: int
    per_page: int
    has_more: bool


class UserSummary(BaseModel):
    """Summary of a user for lists."""

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: Optional[str]
    is_verified: bool
    is_creator: bool
    follower_count: Optional[int] = None
    is_following: Optional[bool] = None

    class Config:
        from_attributes = True


# Comment schemas
class CommentCreateRequest(BaseModel):
    """Request to create a comment."""

    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[uuid.UUID] = None


class CommentUpdateRequest(BaseModel):
    """Request to update a comment."""

    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    """Response for a single comment."""

    id: uuid.UUID
    video_id: uuid.UUID
    user_id: uuid.UUID
    parent_id: Optional[uuid.UUID]
    content: str
    like_count: int
    is_creator_heart: bool
    is_pinned: bool
    is_edited: bool
    edited_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # Joined data
    user: Optional[UserSummary] = None
    reply_count: Optional[int] = None
    is_liked: Optional[bool] = None

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    """Response for comment list."""

    comments: list[CommentResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class CommentThreadResponse(BaseModel):
    """Response for a comment thread (with replies)."""

    comment: CommentResponse
    replies: list[CommentResponse]
    total_replies: int
    has_more_replies: bool


# Reaction schemas
class ReactionRequest(BaseModel):
    """Request to react to a video."""

    reaction_type: ReactionType


class ReactionResponse(BaseModel):
    """Response for a reaction."""

    user_id: uuid.UUID
    video_id: uuid.UUID
    reaction_type: ReactionType
    created_at: datetime

    class Config:
        from_attributes = True


class ReactionSummaryResponse(BaseModel):
    """Summary of reactions on a video."""

    video_id: uuid.UUID
    total_reactions: int
    like_count: int
    love_count: int
    fire_count: int
    mind_blown_count: int
    sad_count: int
    laugh_count: int
    user_reaction: Optional[ReactionType] = None


# Watchlist schemas
class WatchlistAddRequest(BaseModel):
    """Request to add to watchlist."""

    note: Optional[str] = Field(None, max_length=500)


class WatchlistItemResponse(BaseModel):
    """Response for a watchlist item."""

    video_id: uuid.UUID
    user_id: uuid.UUID
    note: Optional[str]
    created_at: datetime
    # Joined video data
    video: Optional["VideoSummary"] = None

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    """Response for user's watchlist."""

    items: list[WatchlistItemResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class VideoSummary(BaseModel):
    """Summary of a video for lists."""

    id: uuid.UUID
    title: str
    thumbnail_url: Optional[str]
    duration_seconds: int
    creator_id: uuid.UUID
    creator_name: Optional[str] = None
    view_count: int
    like_count: int

    class Config:
        from_attributes = True


# Share schemas
class ShareRequest(BaseModel):
    """Request to share a video."""

    platform: Optional[str] = Field(None, max_length=50)


class ShareResponse(BaseModel):
    """Response for share event."""

    id: uuid.UUID
    video_id: uuid.UUID
    platform: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Notification schemas
class NotificationResponse(BaseModel):
    """Response for a notification."""

    id: uuid.UUID
    notification_type: str
    title: str
    message: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    # Related entities
    actor: Optional[UserSummary] = None
    video_id: Optional[uuid.UUID] = None
    comment_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response for notification list."""

    notifications: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    per_page: int
    has_more: bool


class NotificationMarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: list[uuid.UUID]


# Feed schemas
class FeedResponse(BaseModel):
    """Response for social feed."""

    videos: list[VideoSummary]
    page: int
    per_page: int
    has_more: bool


# Update forward references
FollowerListResponse.model_rebuild()
WatchlistResponse.model_rebuild()
