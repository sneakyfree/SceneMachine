"""
Appeal routes for moderation service.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    Appeal,
    AppealStatus,
    ModerationAction,
    Strike,
    User,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    AppealCreateRequest,
    AppealResponse,
    AppealListResponse,
    AppealReviewRequest,
)

router = APIRouter(prefix="/appeals", tags=["appeals"])


def _require_moderator(user: User) -> None:
    """Verify user is a moderator."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )


@router.post("", response_model=AppealResponse, status_code=status.HTTP_201_CREATED)
async def create_appeal(
    request: AppealCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppealResponse:
    """
    Appeal a moderation action or strike.

    Users can appeal within 30 days of the action.
    """
    # Get the action/strike being appealed
    action = None
    strike = None

    if request.action_id:
        result = await db.execute(
            select(ModerationAction).where(ModerationAction.id == request.action_id)
        )
        action = result.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Moderation action not found",
            )
        if action.target_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot appeal action against another user",
            )

    if request.strike_id:
        result = await db.execute(
            select(Strike).where(Strike.id == request.strike_id)
        )
        strike = result.scalar_one_or_none()
        if not strike:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strike not found",
            )
        if strike.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot appeal strike against another user",
            )

    if not action and not strike:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify action_id or strike_id",
        )

    # Check for existing pending appeal
    existing_query = select(Appeal).where(
        and_(
            Appeal.user_id == current_user.id,
            Appeal.status == AppealStatus.PENDING,
        )
    )
    if request.action_id:
        existing_query = existing_query.where(Appeal.action_id == request.action_id)
    if request.strike_id:
        existing_query = existing_query.where(Appeal.strike_id == request.strike_id)

    result = await db.execute(existing_query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending appeal for this item",
        )

    # Check appeal window (30 days)
    reference_date = (
        action.created_at if action else strike.created_at
    )
    days_elapsed = (datetime.now(timezone.utc) - reference_date).days
    if days_elapsed > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal window has expired (30 days)",
        )

    # Create appeal
    appeal = Appeal(
        user_id=current_user.id,
        action_id=request.action_id,
        strike_id=request.strike_id,
        reason=request.reason,
        evidence=request.evidence,
        status=AppealStatus.PENDING,
    )
    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)

    return AppealResponse.model_validate(appeal)


@router.get("/my-appeals", response_model=AppealListResponse)
async def get_my_appeals(
    status_filter: Optional[AppealStatus] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppealListResponse:
    """Get appeals submitted by current user."""
    query = select(Appeal).where(Appeal.user_id == current_user.id)

    if status_filter:
        query = query.where(Appeal.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Count pending
    pending_query = select(func.count()).where(
        and_(
            Appeal.user_id == current_user.id,
            Appeal.status == AppealStatus.PENDING,
        )
    )
    result = await db.execute(pending_query)
    pending_count = result.scalar() or 0

    # Get appeals
    offset = (page - 1) * per_page
    query = query.order_by(Appeal.created_at.desc())
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    appeals = result.scalars().all()

    return AppealListResponse(
        appeals=[AppealResponse.model_validate(a) for a in appeals],
        total=total,
        pending_count=pending_count,
        page=page,
        per_page=per_page,
    )


@router.get("", response_model=AppealListResponse)
async def get_appeals(
    status_filter: Optional[AppealStatus] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppealListResponse:
    """Get all appeals (moderator only)."""
    _require_moderator(current_user)

    query = select(Appeal)

    if status_filter:
        query = query.where(Appeal.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Count pending
    pending_query = select(func.count()).where(Appeal.status == AppealStatus.PENDING)
    result = await db.execute(pending_query)
    pending_count = result.scalar() or 0

    # Get appeals (oldest pending first)
    offset = (page - 1) * per_page
    query = query.order_by(
        # Pending first, then by date
        (Appeal.status == AppealStatus.PENDING).desc(),
        Appeal.created_at.asc(),
    )
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    appeals = result.scalars().all()

    return AppealListResponse(
        appeals=[AppealResponse.model_validate(a) for a in appeals],
        total=total,
        pending_count=pending_count,
        page=page,
        per_page=per_page,
    )


@router.get("/{appeal_id}", response_model=AppealResponse)
async def get_appeal(
    appeal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppealResponse:
    """Get a specific appeal."""
    result = await db.execute(
        select(Appeal).where(Appeal.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()

    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appeal not found",
        )

    # Check access
    is_owner = appeal.user_id == current_user.id
    is_moderator = current_user.is_verified

    if not is_owner and not is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return AppealResponse.model_validate(appeal)


@router.post("/{appeal_id}/review")
async def review_appeal(
    appeal_id: uuid.UUID,
    request: AppealReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Review and resolve an appeal (moderator only).

    Can approve, deny, or partially approve the appeal.
    """
    _require_moderator(current_user)

    result = await db.execute(
        select(Appeal).where(Appeal.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()

    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appeal not found",
        )

    if appeal.status != AppealStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal already reviewed",
        )

    # Update appeal
    appeal.status = request.status
    appeal.reviewer_id = current_user.id
    appeal.reviewed_at = datetime.now(timezone.utc)
    appeal.reviewer_notes = request.reviewer_notes

    action_result = None

    # If approved, reverse the action/strike
    if request.status == AppealStatus.APPROVED:
        if appeal.action_id:
            action_result = await db.execute(
                select(ModerationAction).where(ModerationAction.id == appeal.action_id)
            )
            action = action_result.scalar_one_or_none()
            if action and not action.revoked_at:
                action.revoked_at = datetime.now(timezone.utc)
                action.revoked_by = current_user.id

        if appeal.strike_id:
            strike_result = await db.execute(
                select(Strike).where(Strike.id == appeal.strike_id)
            )
            strike = strike_result.scalar_one_or_none()
            if strike:
                strike.is_active = False

        # Potentially unsuspend user
        user_result = await db.execute(
            select(User).where(User.id == appeal.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user and user.is_suspended:
            # Check if there are other active reasons for suspension
            other_active = await db.execute(
                select(func.count()).where(
                    and_(
                        ModerationAction.target_user_id == user.id,
                        ModerationAction.revoked_at == None,
                        or_(
                            ModerationAction.expires_at > datetime.now(timezone.utc),
                            ModerationAction.expires_at == None,
                        ),
                    )
                )
            )
            if (other_active.scalar() or 0) == 0:
                user.is_suspended = False

    await db.commit()

    return {
        "appeal_id": str(appeal_id),
        "status": appeal.status.value,
        "reviewed_by": str(current_user.id),
        "action_reversed": request.status == AppealStatus.APPROVED,
    }


@router.get("/stats/summary")
async def get_appeal_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get appeal statistics (moderator only)."""
    _require_moderator(current_user)

    # Total by status
    result = await db.execute(
        select(Appeal.status, func.count())
        .group_by(Appeal.status)
    )
    status_counts = {row[0].value: row[1] for row in result.all()}

    # Approval rate
    total_reviewed = (
        status_counts.get(AppealStatus.APPROVED.value, 0) +
        status_counts.get(AppealStatus.DENIED.value, 0) +
        status_counts.get(AppealStatus.PARTIAL.value, 0)
    )
    approval_rate = 0.0
    if total_reviewed > 0:
        approved = status_counts.get(AppealStatus.APPROVED.value, 0)
        approval_rate = approved / total_reviewed * 100

    # Average response time (for reviewed appeals)
    # Would need to calculate from reviewed_at - created_at

    return {
        "pending": status_counts.get(AppealStatus.PENDING.value, 0),
        "approved": status_counts.get(AppealStatus.APPROVED.value, 0),
        "denied": status_counts.get(AppealStatus.DENIED.value, 0),
        "partial": status_counts.get(AppealStatus.PARTIAL.value, 0),
        "total_reviewed": total_reviewed,
        "approval_rate_percent": round(approval_rate, 1),
    }
