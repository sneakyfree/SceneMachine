"""
Pydantic schemas for moderation service.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ...shared.models import (
    ReportReason,
    ReportStatus,
    ReportTargetType,
    ActionType,
    AppealStatus,
    FlagCategory,
    FlagSeverity,
)


# Report schemas
class ReportCreateRequest(BaseModel):
    """Request to create a report."""

    target_type: ReportTargetType
    target_id: uuid.UUID
    reason: ReportReason
    description: Optional[str] = Field(None, max_length=2000)
    timestamp_seconds: Optional[int] = Field(None, ge=0)


class ReportResponse(BaseModel):
    """Response for a report."""

    id: uuid.UUID
    reporter_id: Optional[uuid.UUID]
    target_type: ReportTargetType
    target_id: uuid.UUID
    reason: ReportReason
    description: Optional[str]
    status: ReportStatus
    priority: int
    created_at: datetime
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Response for report list (admin view)."""

    reports: list[ReportResponse]
    total: int
    pending_count: int
    page: int
    per_page: int


class ReportReviewRequest(BaseModel):
    """Request to review a report."""

    status: ReportStatus
    review_notes: Optional[str] = Field(None, max_length=2000)
    take_action: bool = False
    action_type: Optional[ActionType] = None
    action_reason: Optional[str] = None


# Moderation action schemas
class ModerationActionResponse(BaseModel):
    """Response for a moderation action."""

    id: uuid.UUID
    target_user_id: uuid.UUID
    moderator_id: Optional[uuid.UUID]
    action_type: ActionType
    reason: str
    video_id: Optional[uuid.UUID]
    comment_id: Optional[uuid.UUID]
    duration_days: Optional[int]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ModerationActionListResponse(BaseModel):
    """Response for moderation action list."""

    actions: list[ModerationActionResponse]
    total: int
    page: int
    per_page: int


class ModerationActionRequest(BaseModel):
    """Request to create a moderation action."""

    target_user_id: uuid.UUID
    action_type: ActionType
    reason: str = Field(..., min_length=10, max_length=500)
    video_id: Optional[uuid.UUID] = None
    comment_id: Optional[uuid.UUID] = None
    report_id: Optional[uuid.UUID] = None
    duration_hours: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None
    add_strike: bool = False


# Strike schemas
class StrikeResponse(BaseModel):
    """Response for a strike."""

    id: uuid.UUID
    user_id: uuid.UUID
    action_id: Optional[uuid.UUID]
    reason: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class StrikeListResponse(BaseModel):
    """Response for strike list."""

    strikes: list[StrikeResponse]
    total: int
    active_count: int
    max_strikes: int


class StrikeCreateRequest(BaseModel):
    """Request to create a strike."""

    user_id: uuid.UUID
    action_id: Optional[uuid.UUID] = None
    reason: str = Field(..., min_length=10, max_length=500)
    expiration_days: Optional[int] = Field(None, ge=1, le=365)


# Appeal schemas
class AppealCreateRequest(BaseModel):
    """Request to create an appeal."""

    action_id: Optional[uuid.UUID] = None
    strike_id: Optional[uuid.UUID] = None
    reason: str = Field(..., min_length=50, max_length=5000)
    evidence: Optional[str] = Field(None, max_length=5000)


class AppealResponse(BaseModel):
    """Response for an appeal."""

    id: uuid.UUID
    user_id: uuid.UUID
    action_id: Optional[uuid.UUID]
    strike_id: Optional[uuid.UUID]
    reason: str
    evidence: Optional[str]
    status: AppealStatus
    reviewed_at: Optional[datetime]
    decision_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AppealListResponse(BaseModel):
    """Response for appeal list."""

    appeals: list[AppealResponse]
    total: int
    pending_count: int
    page: int
    per_page: int


class AppealReviewRequest(BaseModel):
    """Request to review an appeal."""

    status: AppealStatus
    decision_reason: str = Field(..., min_length=20, max_length=2000)
    review_notes: Optional[str] = None


# Content flag schemas
class ContentFlagCreateRequest(BaseModel):
    """Request to create a content flag (from AI pipeline)."""

    video_id: Optional[uuid.UUID] = None
    comment_id: Optional[uuid.UUID] = None
    category: FlagCategory
    severity: FlagSeverity
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    detection_model: Optional[str] = None
    detection_details: Optional[dict] = None
    timestamp_seconds: Optional[int] = None
    auto_action_taken: Optional[str] = None


class ContentFlagResponse(BaseModel):
    """Response for a content flag."""

    id: uuid.UUID
    video_id: Optional[uuid.UUID]
    comment_id: Optional[uuid.UUID]
    category: FlagCategory
    severity: FlagSeverity
    confidence_score: float
    detection_model: Optional[str]
    detection_details: Optional[dict]
    timestamp_seconds: Optional[int]
    auto_action_taken: Optional[str]
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[uuid.UUID]
    review_notes: Optional[str]
    is_accurate: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True


class ContentFlagListResponse(BaseModel):
    """Response for content flag list."""

    flags: list[ContentFlagResponse]
    total: int
    pending_count: int
    page: int
    per_page: int


class ContentFlagReviewRequest(BaseModel):
    """Request to review a content flag."""

    is_accurate: bool
    take_action: bool = False
    review_notes: Optional[str] = Field(None, max_length=2000)


# Moderation stats
class ModerationStatsResponse(BaseModel):
    """Moderation statistics for admin dashboard."""

    # Reports
    pending_reports: int
    reports_today: int
    reports_this_week: int
    avg_resolution_hours: float

    # Actions
    actions_today: int
    actions_this_week: int
    content_removed_today: int
    accounts_suspended_today: int

    # Appeals
    pending_appeals: int
    appeals_approved_rate: float

    # Content flags
    pending_flags: int
    false_positive_rate: float

    # Strikes
    strikes_issued_today: int
    accounts_terminated_today: int
