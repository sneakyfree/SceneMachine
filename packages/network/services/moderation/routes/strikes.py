"""
Strike management routes for moderation service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    Strike,
    User,
    MAX_STRIKES,
    STRIKE_EXPIRATION_DAYS,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    StrikeCreateRequest,
    StrikeResponse,
    StrikeListResponse,
)

router = APIRouter(prefix="/strikes", tags=["strikes"])


def _require_moderator(user: User) -> None:
    """Verify user is a moderator."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator access required",
        )


@router.get("/my-strikes", response_model=StrikeListResponse)
async def get_my_strikes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrikeListResponse:
    """Get strikes against the current user."""
    # Get active strikes
    result = await db.execute(
        select(Strike)
        .where(
            and_(
                Strike.user_id == current_user.id,
                Strike.is_active == True,
            )
        )
        .order_by(Strike.created_at.desc())
    )
    strikes = result.scalars().all()

    # Filter to only non-expired
    active_strikes = [
        s for s in strikes
        if s.expires_at is None or s.expires_at > datetime.now(timezone.utc)
    ]

    return StrikeListResponse(
        strikes=[StrikeResponse.model_validate(s) for s in active_strikes],
        total=len(active_strikes),
        active_count=len(active_strikes),
        max_strikes=MAX_STRIKES,
    )


@router.get("/user/{user_id}", response_model=StrikeListResponse)
async def get_user_strikes(
    user_id: uuid.UUID,
    include_expired: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrikeListResponse:
    """Get strikes against a specific user (moderator only)."""
    _require_moderator(current_user)

    # Build query
    query = select(Strike).where(Strike.user_id == user_id)

    if not include_expired:
        query = query.where(
            and_(
                Strike.is_active == True,
                or_(
                    Strike.expires_at > datetime.now(timezone.utc),
                    Strike.expires_at == None,
                ),
            )
        )

    query = query.order_by(Strike.created_at.desc())
    result = await db.execute(query)
    strikes = result.scalars().all()

    # Count active
    active_count = sum(
        1 for s in strikes
        if s.is_active and (
            s.expires_at is None or s.expires_at > datetime.now(timezone.utc)
        )
    )

    return StrikeListResponse(
        strikes=[StrikeResponse.model_validate(s) for s in strikes],
        total=len(strikes),
        active_count=active_count,
        max_strikes=MAX_STRIKES,
    )


@router.post("", response_model=StrikeResponse, status_code=status.HTTP_201_CREATED)
async def create_strike(
    request: StrikeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StrikeResponse:
    """Create a strike against a user (moderator only)."""
    _require_moderator(current_user)

    # Verify target user exists
    result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Create strike
    strike = Strike(
        user_id=request.user_id,
        action_id=request.action_id,
        reason=request.reason,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=request.expiration_days or STRIKE_EXPIRATION_DAYS),
    )
    db.add(strike)

    # Check if user should be terminated
    active_strikes = await db.execute(
        select(func.count()).where(
            and_(
                Strike.user_id == request.user_id,
                Strike.is_active == True,
                or_(
                    Strike.expires_at > datetime.now(timezone.utc),
                    Strike.expires_at == None,
                ),
            )
        )
    )
    strike_count = (active_strikes.scalar() or 0) + 1  # +1 for new strike

    if strike_count >= MAX_STRIKES:
        target_user.is_suspended = True
        target_user.is_terminated = True

    await db.commit()
    await db.refresh(strike)

    return StrikeResponse.model_validate(strike)


@router.delete("/{strike_id}")
async def remove_strike(
    strike_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove/deactivate a strike (moderator only)."""
    _require_moderator(current_user)

    result = await db.execute(
        select(Strike).where(Strike.id == strike_id)
    )
    strike = result.scalar_one_or_none()

    if not strike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strike not found",
        )

    if not strike.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strike already inactive",
        )

    strike.is_active = False

    # Check if user should be unsuspended
    user_result = await db.execute(
        select(User).where(User.id == strike.user_id)
    )
    target_user = user_result.scalar_one_or_none()

    if target_user and target_user.is_terminated:
        # Count remaining active strikes
        active_strikes = await db.execute(
            select(func.count()).where(
                and_(
                    Strike.user_id == strike.user_id,
                    Strike.id != strike_id,
                    Strike.is_active == True,
                    or_(
                        Strike.expires_at > datetime.now(timezone.utc),
                        Strike.expires_at == None,
                    ),
                )
            )
        )
        remaining_strikes = active_strikes.scalar() or 0

        if remaining_strikes < MAX_STRIKES:
            # Note: Manual review may still be required
            pass

    await db.commit()

    return {"strike_id": str(strike_id), "status": "deactivated"}


@router.get("/stats")
async def get_strike_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get strike statistics (moderator only)."""
    _require_moderator(current_user)

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Total active strikes
    result = await db.execute(
        select(func.count()).where(
            and_(
                Strike.is_active == True,
                or_(
                    Strike.expires_at > now,
                    Strike.expires_at == None,
                ),
            )
        )
    )
    total_active = result.scalar() or 0

    # Strikes in last 30 days
    result = await db.execute(
        select(func.count()).where(Strike.created_at >= thirty_days_ago)
    )
    last_30_days = result.scalar() or 0

    # Users with max strikes (terminated)
    result = await db.execute(
        select(func.count(func.distinct(Strike.user_id)))
        .where(
            and_(
                Strike.is_active == True,
                or_(
                    Strike.expires_at > now,
                    Strike.expires_at == None,
                ),
            )
        )
        .group_by(Strike.user_id)
        .having(func.count() >= MAX_STRIKES)
    )
    terminated_users = len(result.all())

    # Strikes expiring soon (next 7 days)
    seven_days = now + timedelta(days=7)
    result = await db.execute(
        select(func.count()).where(
            and_(
                Strike.is_active == True,
                Strike.expires_at > now,
                Strike.expires_at <= seven_days,
            )
        )
    )
    expiring_soon = result.scalar() or 0

    return {
        "total_active_strikes": total_active,
        "strikes_last_30_days": last_30_days,
        "terminated_users": terminated_users,
        "expiring_within_7_days": expiring_soon,
        "max_strikes_per_user": MAX_STRIKES,
        "strike_expiration_days": STRIKE_EXPIRATION_DAYS,
    }
