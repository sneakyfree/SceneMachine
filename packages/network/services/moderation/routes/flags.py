"""
Content flag routes for moderation service.

Handles AI-detected content flags that require human review.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    ContentFlag,
    FlagCategory,
    FlagSeverity,
    User,
    Video,
    VideoStatus,
    Comment,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    ContentFlagCreateRequest,
    ContentFlagResponse,
    ContentFlagListResponse,
    ContentFlagReviewRequest,
)

router = APIRouter(prefix="/flags", tags=["content-flags"])


def _require_moderator(user: User) -> None:
    """Verify user is a moderator."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )


@router.post("", response_model=ContentFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    request: ContentFlagCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ContentFlagResponse:
    """
    Create a content flag (internal API for AI moderation).

    This endpoint is called by the AI content scanning pipeline
    when potentially problematic content is detected.
    """
    # Note: In production, this would require internal API key auth
    # For now, it's open for development

    # Validate target exists
    if request.video_id:
        result = await db.execute(
            select(Video).where(Video.id == request.video_id)
        )
        video = result.scalar_one_or_none()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

    if request.comment_id:
        result = await db.execute(
            select(Comment).where(Comment.id == request.comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )

    # Check for existing flag
    existing_query = select(ContentFlag).where(
        and_(
            ContentFlag.category == request.category,
            ContentFlag.reviewed_at == None,
        )
    )
    if request.video_id:
        existing_query = existing_query.where(ContentFlag.video_id == request.video_id)
    if request.comment_id:
        existing_query = existing_query.where(ContentFlag.comment_id == request.comment_id)

    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()
    if existing:
        # Update confidence if higher
        if request.confidence_score > existing.confidence_score:
            existing.confidence_score = request.confidence_score
            existing.detection_details = request.detection_details
            await db.commit()
            await db.refresh(existing)
        return ContentFlagResponse.model_validate(existing)

    # Create flag
    flag = ContentFlag(
        video_id=request.video_id,
        comment_id=request.comment_id,
        category=request.category,
        severity=request.severity,
        confidence_score=request.confidence_score,
        detection_model=request.detection_model,
        detection_details=request.detection_details,
        timestamp_seconds=request.timestamp_seconds,
        auto_action_taken=request.auto_action_taken,
    )
    db.add(flag)

    # Auto-action for high-confidence severe content
    if (
        request.severity in (FlagSeverity.CRITICAL, FlagSeverity.HIGH)
        and request.confidence_score >= 0.95
        and request.auto_action_taken
    ):
        if request.video_id:
            video_result = await db.execute(
                select(Video).where(Video.id == request.video_id)
            )
            video = video_result.scalar_one_or_none()
            if video:
                video.status = VideoStatus.REMOVED
                flag.auto_action_taken = "video_removed"

    await db.commit()
    await db.refresh(flag)

    return ContentFlagResponse.model_validate(flag)


@router.get("", response_model=ContentFlagListResponse)
async def get_flags(
    reviewed: Optional[bool] = Query(None),
    category: Optional[FlagCategory] = Query(None),
    severity: Optional[FlagSeverity] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentFlagListResponse:
    """Get content flags (moderator only)."""
    _require_moderator(current_user)

    query = select(ContentFlag)

    if reviewed is not None:
        if reviewed:
            query = query.where(ContentFlag.reviewed_at != None)
        else:
            query = query.where(ContentFlag.reviewed_at == None)

    if category:
        query = query.where(ContentFlag.category == category)

    if severity:
        query = query.where(ContentFlag.severity == severity)

    if min_confidence > 0:
        query = query.where(ContentFlag.confidence_score >= min_confidence)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Count pending
    pending_query = select(func.count()).where(ContentFlag.reviewed_at == None)
    result = await db.execute(pending_query)
    pending_count = result.scalar() or 0

    # Get flags (highest severity/confidence first)
    offset = (page - 1) * per_page
    query = query.order_by(
        ContentFlag.severity.desc(),
        ContentFlag.confidence_score.desc(),
        ContentFlag.created_at.asc(),
    )
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    flags = result.scalars().all()

    return ContentFlagListResponse(
        flags=[ContentFlagResponse.model_validate(f) for f in flags],
        total=total,
        pending_count=pending_count,
        page=page,
        per_page=per_page,
    )


@router.get("/queue")
async def get_review_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get prioritized review queue (moderator only)."""
    _require_moderator(current_user)

    # Critical flags (immediate attention)
    critical_result = await db.execute(
        select(ContentFlag)
        .where(
            and_(
                ContentFlag.reviewed_at == None,
                ContentFlag.severity == FlagSeverity.CRITICAL,
            )
        )
        .order_by(ContentFlag.confidence_score.desc())
        .limit(10)
    )
    critical_flags = critical_result.scalars().all()

    # High severity flags
    high_result = await db.execute(
        select(ContentFlag)
        .where(
            and_(
                ContentFlag.reviewed_at == None,
                ContentFlag.severity == FlagSeverity.HIGH,
            )
        )
        .order_by(ContentFlag.confidence_score.desc())
        .limit(10)
    )
    high_flags = high_result.scalars().all()

    # Counts by severity
    severity_counts = {}
    for severity in FlagSeverity:
        result = await db.execute(
            select(func.count()).where(
                and_(
                    ContentFlag.reviewed_at == None,
                    ContentFlag.severity == severity,
                )
            )
        )
        severity_counts[severity.value] = result.scalar() or 0

    return {
        "critical_flags": [ContentFlagResponse.model_validate(f) for f in critical_flags],
        "high_flags": [ContentFlagResponse.model_validate(f) for f in high_flags],
        "pending_by_severity": severity_counts,
        "total_pending": sum(severity_counts.values()),
    }


@router.get("/{flag_id}", response_model=ContentFlagResponse)
async def get_flag(
    flag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentFlagResponse:
    """Get a specific content flag (moderator only)."""
    _require_moderator(current_user)

    result = await db.execute(
        select(ContentFlag).where(ContentFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flag not found",
        )

    return ContentFlagResponse.model_validate(flag)


@router.post("/{flag_id}/review")
async def review_flag(
    flag_id: uuid.UUID,
    request: ContentFlagReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Review a content flag (moderator only).

    Determines if the AI detection was accurate and takes appropriate action.
    """
    _require_moderator(current_user)

    result = await db.execute(
        select(ContentFlag).where(ContentFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flag not found",
        )

    if flag.reviewed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flag already reviewed",
        )

    # Update flag
    flag.reviewed_at = datetime.now(timezone.utc)
    flag.reviewed_by = current_user.id
    flag.review_notes = request.review_notes
    flag.is_accurate = request.is_accurate

    action_taken = None

    # Take action if flag is accurate
    if request.is_accurate and request.take_action:
        if flag.video_id:
            video_result = await db.execute(
                select(Video).where(Video.id == flag.video_id)
            )
            video = video_result.scalar_one_or_none()
            if video and video.status != VideoStatus.REMOVED:
                video.status = VideoStatus.REMOVED
                action_taken = "video_removed"

        if flag.comment_id:
            comment_result = await db.execute(
                select(Comment).where(Comment.id == flag.comment_id)
            )
            comment = comment_result.scalar_one_or_none()
            if comment:
                comment.is_deleted = True
                action_taken = "comment_removed"

    await db.commit()

    return {
        "flag_id": str(flag_id),
        "is_accurate": request.is_accurate,
        "action_taken": action_taken,
        "reviewed_by": str(current_user.id),
    }


@router.get("/stats/accuracy")
async def get_accuracy_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get AI detection accuracy statistics (moderator only)."""
    _require_moderator(current_user)

    # Overall accuracy
    result = await db.execute(
        select(
            func.count().filter(ContentFlag.is_accurate == True),
            func.count().filter(ContentFlag.is_accurate == False),
            func.count().filter(ContentFlag.reviewed_at != None),
        )
    )
    row = result.one()
    accurate, inaccurate, total_reviewed = row

    overall_accuracy = 0.0
    if total_reviewed > 0:
        overall_accuracy = accurate / total_reviewed * 100

    # Accuracy by category
    category_stats = {}
    for category in FlagCategory:
        cat_result = await db.execute(
            select(
                func.count().filter(ContentFlag.is_accurate == True),
                func.count().filter(ContentFlag.reviewed_at != None),
            ).where(ContentFlag.category == category)
        )
        cat_row = cat_result.one()
        cat_accurate, cat_total = cat_row

        cat_accuracy = 0.0
        if cat_total > 0:
            cat_accuracy = cat_accurate / cat_total * 100

        category_stats[category.value] = {
            "total_reviewed": cat_total,
            "accurate": cat_accurate,
            "accuracy_percent": round(cat_accuracy, 1),
        }

    # Accuracy by detection model
    model_stats = {}
    result = await db.execute(
        select(ContentFlag.detection_model)
        .distinct()
        .where(ContentFlag.detection_model != None)
    )
    models = [row[0] for row in result.all()]

    for model in models:
        model_result = await db.execute(
            select(
                func.count().filter(ContentFlag.is_accurate == True),
                func.count().filter(ContentFlag.reviewed_at != None),
            ).where(ContentFlag.detection_model == model)
        )
        model_row = model_result.one()
        model_accurate, model_total = model_row

        model_accuracy = 0.0
        if model_total > 0:
            model_accuracy = model_accurate / model_total * 100

        model_stats[model] = {
            "total_reviewed": model_total,
            "accurate": model_accurate,
            "accuracy_percent": round(model_accuracy, 1),
        }

    return {
        "overall": {
            "total_reviewed": total_reviewed,
            "accurate": accurate,
            "inaccurate": inaccurate,
            "accuracy_percent": round(overall_accuracy, 1),
        },
        "by_category": category_stats,
        "by_model": model_stats,
    }
