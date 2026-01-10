"""
Report routes for moderation service.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    Comment,
    Report,
    ReportReason,
    ReportStatus,
    ReportTargetType,
    User,
    Video,
    VideoStatus,
    REPORT_PRIORITY,
)
from ...auth.dependencies import get_current_user, get_optional_user
from ..schemas import (
    ReportCreateRequest,
    ReportResponse,
    ReportListResponse,
    ReportReviewRequest,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _require_moderator(user: User) -> None:
    """Verify user is a moderator."""
    # Check user role for moderator access
    if not (user.is_verified or getattr(user, "role", None) in ("moderator", "admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )


async def calculate_reporter_credibility(
    user_id: uuid.UUID, db: AsyncSession
) -> float:
    """
    Calculate a reporter's credibility score based on their report history.

    Returns a score between 0.0 (low credibility) and 1.0 (high credibility).
    Used to prioritize reports and detect abuse of the reporting system.
    """
    # Get user's report history
    result = await db.execute(
        select(Report).where(Report.reporter_id == user_id)
    )
    reports = result.scalars().all()

    if not reports:
        # New reporter - neutral credibility
        return 0.5

    total_reports = len(reports)
    resolved_reports = [r for r in reports if r.status != ReportStatus.PENDING]

    if not resolved_reports:
        # All reports still pending - slightly lower credibility
        return 0.4

    # Count outcome types
    upheld = sum(1 for r in resolved_reports if r.status == ReportStatus.ACTION_TAKEN)
    dismissed = sum(1 for r in resolved_reports if r.status == ReportStatus.DISMISSED)
    resolved_count = len(resolved_reports)

    # Calculate base credibility from upheld/dismissed ratio
    upheld_ratio = upheld / resolved_count if resolved_count > 0 else 0
    dismissed_ratio = dismissed / resolved_count if resolved_count > 0 else 0

    base_score = 0.5 + (upheld_ratio * 0.4) - (dismissed_ratio * 0.3)

    # Apply volume factors
    # Bonus for consistent, accurate reporters (many upheld reports)
    if upheld >= 5 and upheld_ratio > 0.7:
        base_score += 0.1

    # Penalty for high volume of dismissed reports (potential abuse)
    if dismissed >= 5 and dismissed_ratio > 0.5:
        base_score -= 0.2

    # Penalty for excessive reporting (more than 50 reports)
    if total_reports > 50:
        base_score -= 0.1

    # Check for recent false reports (last 30 days)
    recent_dismissed = sum(
        1 for r in resolved_reports
        if r.status == ReportStatus.DISMISSED
        and r.reviewed_at
        and (datetime.now(timezone.utc) - r.reviewed_at).days <= 30
    )
    if recent_dismissed >= 3:
        base_score -= 0.15

    # Clamp to valid range
    return max(0.0, min(1.0, base_score))


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: ReportCreateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """
    Report content or a user.

    Can be submitted anonymously.
    """
    # Validate target exists
    target_user_id = None

    if request.target_type == ReportTargetType.VIDEO:
        result = await db.execute(
            select(Video).where(Video.id == request.target_id)
        )
        video = result.scalar_one_or_none()
        if not video or video.status == VideoStatus.REMOVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )
        target_user_id = video.creator_id

    elif request.target_type == ReportTargetType.COMMENT:
        result = await db.execute(
            select(Comment).where(Comment.id == request.target_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )
        target_user_id = comment.user_id

    elif request.target_type in (ReportTargetType.USER, ReportTargetType.CHANNEL):
        result = await db.execute(
            select(User).where(User.id == request.target_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        target_user_id = user.id

    # Check for duplicate recent report
    if current_user:
        result = await db.execute(
            select(Report).where(
                and_(
                    Report.reporter_id == current_user.id,
                    Report.target_type == request.target_type,
                    Report.target_id == request.target_id,
                    Report.status == ReportStatus.PENDING,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reported this content",
            )

    # Calculate base priority from report reason
    base_priority = REPORT_PRIORITY.get(request.reason, 5)

    # Adjust priority based on reporter credibility
    credibility = 0.5  # Default for anonymous
    if current_user:
        credibility = await calculate_reporter_credibility(current_user.id, db)

    # High credibility reporters get priority boost, low credibility gets reduced priority
    priority_adjustment = int((credibility - 0.5) * 4)  # -2 to +2 adjustment
    priority = max(1, min(10, base_priority + priority_adjustment))

    # Create report with calculated priority
    report = Report(
        reporter_id=current_user.id if current_user else None,
        target_type=request.target_type,
        target_id=request.target_id,
        target_user_id=target_user_id,
        reason=request.reason,
        description=request.description,
        timestamp_seconds=request.timestamp_seconds,
        priority=priority,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return ReportResponse.model_validate(report)


@router.get("/my-reports", response_model=ReportListResponse)
async def get_my_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """Get reports submitted by current user."""
    # Count total
    result = await db.execute(
        select(func.count()).where(Report.reporter_id == current_user.id)
    )
    total = result.scalar() or 0

    # Get reports
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Report)
        .where(Report.reporter_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        pending_count=sum(1 for r in reports if r.status == ReportStatus.PENDING),
        page=page,
        per_page=per_page,
    )


# Admin/Moderator routes
@router.get("", response_model=ReportListResponse)
async def get_reports(
    status_filter: Optional[ReportStatus] = Query(None),
    reason_filter: Optional[ReportReason] = Query(None),
    target_type: Optional[ReportTargetType] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """Get all reports (moderator only)."""
    _require_moderator(current_user)

    # Build query
    query = select(Report)

    if status_filter:
        query = query.where(Report.status == status_filter)
    if reason_filter:
        query = query.where(Report.reason == reason_filter)
    if target_type:
        query = query.where(Report.target_type == target_type)

    # Count total and pending
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    pending_query = select(func.count()).where(Report.status == ReportStatus.PENDING)
    result = await db.execute(pending_query)
    pending_count = result.scalar() or 0

    # Get reports
    offset = (page - 1) * per_page
    query = query.order_by(Report.priority.desc(), Report.created_at.asc())
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        pending_count=pending_count,
        page=page,
        per_page=per_page,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Get a specific report (moderator only)."""
    _require_moderator(current_user)

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportResponse.model_validate(report)


@router.post("/{report_id}/review")
async def review_report(
    report_id: uuid.UUID,
    request: ReportReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Review and resolve a report (moderator only).

    Can optionally take action against the content/user.
    """
    _require_moderator(current_user)

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.status not in (ReportStatus.PENDING, ReportStatus.UNDER_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report already resolved",
        )

    # Update report
    report.status = request.status
    report.reviewed_by = current_user.id
    report.reviewed_at = datetime.now(timezone.utc)
    report.review_notes = request.review_notes

    # Take action if requested
    action_taken = None
    if request.take_action and request.action_type and report.target_user_id:
        from ....shared.models import ModerationAction

        action = ModerationAction(
            target_user_id=report.target_user_id,
            moderator_id=current_user.id,
            action_type=request.action_type,
            reason=request.action_reason or f"Reported for: {report.reason.value}",
            report_id=report.id,
        )

        # Set video/comment if applicable
        if report.target_type == ReportTargetType.VIDEO:
            action.video_id = report.target_id
        elif report.target_type == ReportTargetType.COMMENT:
            action.comment_id = report.target_id

        db.add(action)
        action_taken = request.action_type.value

    await db.commit()

    return {
        "report_id": str(report_id),
        "status": report.status.value,
        "action_taken": action_taken,
    }


@router.post("/{report_id}/escalate")
async def escalate_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Escalate a report to higher priority (moderator only)."""
    _require_moderator(current_user)

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Increase priority
    report.priority = min(10, report.priority + 2)
    report.status = ReportStatus.UNDER_REVIEW

    await db.commit()

    return {"report_id": str(report_id), "new_priority": report.priority}
