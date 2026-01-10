"""Performers Association routes."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.events import (
    BadgeType,
    PerformersAssociationMembership,
    PerformersAssociationTier,
    TIER_BENEFITS,
    TIER_REQUIREMENTS,
    UserBadge,
)
from ....shared.models.user import User
from ...auth.dependencies import get_current_user, get_current_admin
from ..schemas import (
    PerformersAssociationResponse,
    TierProgress,
    TierRequirements,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performers-association", tags=["Performers Association"])


@router.get("/tiers", response_model=list[dict])
async def list_tiers() -> list[dict]:
    """List all Performers Association tiers with requirements and benefits."""
    tiers = []
    for tier in PerformersAssociationTier:
        requirements = TIER_REQUIREMENTS.get(tier, {})
        benefits = TIER_BENEFITS.get(tier, {})

        tiers.append({
            "tier": tier.value,
            "requirements": {
                "min_videos": requirements.get("min_videos", 0),
                "min_views": requirements.get("min_views", 0),
                "min_earnings": float(requirements.get("min_earnings", Decimal("0.00"))),
                "min_corecast_wins": requirements.get("min_corecast_wins", 0),
            },
            "benefits": {
                "fee_reduction_percent": benefits.get("fee_reduction_percent", 0),
                "badge": benefits.get("badge", BadgeType.EMERGING).value,
                "perks": benefits.get("benefits", []),
            },
        })

    return tiers


@router.get("/membership", response_model=PerformersAssociationResponse)
async def get_my_membership(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PerformersAssociationMembership:
    """Get current user's Performers Association membership."""
    result = await session.execute(
        select(PerformersAssociationMembership).where(
            PerformersAssociationMembership.user_id == current_user.id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        # Auto-create membership at Emerging level
        membership = PerformersAssociationMembership(
            user_id=current_user.id,
            tier=PerformersAssociationTier.EMERGING,
        )
        session.add(membership)

        # Award Emerging badge
        badge = UserBadge(
            user_id=current_user.id,
            badge_type=BadgeType.EMERGING,
            award_reason="Joined Performers Association",
        )
        session.add(badge)

        await session.commit()
        await session.refresh(membership)

    return membership


@router.get("/membership/{user_id}", response_model=PerformersAssociationResponse)
async def get_user_membership(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PerformersAssociationMembership:
    """Get a user's Performers Association membership."""
    result = await session.execute(
        select(PerformersAssociationMembership).where(
            PerformersAssociationMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    return membership


@router.get("/progress", response_model=TierProgress)
async def get_tier_progress(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TierProgress:
    """Get progress towards next tier."""
    result = await session.execute(
        select(PerformersAssociationMembership).where(
            PerformersAssociationMembership.user_id == current_user.id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        # Create default membership
        membership = PerformersAssociationMembership(
            user_id=current_user.id,
            tier=PerformersAssociationTier.EMERGING,
        )
        session.add(membership)
        await session.commit()
        await session.refresh(membership)

    # Determine next tier
    tier_order = list(PerformersAssociationTier)
    current_index = tier_order.index(membership.tier)

    if current_index >= len(tier_order) - 1:
        # Already at Legend tier
        return TierProgress(
            current_tier=membership.tier.value,
            next_tier=None,
            videos_progress=100.0,
            views_progress=100.0,
            earnings_progress=100.0,
            wins_progress=100.0,
            overall_progress=100.0,
        )

    next_tier = tier_order[current_index + 1]
    requirements = TIER_REQUIREMENTS.get(next_tier, {})

    # Calculate progress percentages
    min_videos = requirements.get("min_videos", 1)
    min_views = requirements.get("min_views", 1)
    min_earnings = requirements.get("min_earnings", Decimal("1.00"))
    min_wins = requirements.get("min_corecast_wins", 0)

    videos_progress = min(100.0, (membership.total_videos / min_videos) * 100) if min_videos > 0 else 100.0
    views_progress = min(100.0, (membership.total_views / min_views) * 100) if min_views > 0 else 100.0
    earnings_progress = min(100.0, float(membership.total_earnings / min_earnings) * 100) if min_earnings > 0 else 100.0
    wins_progress = min(100.0, (membership.corecast_wins / min_wins) * 100) if min_wins > 0 else 100.0

    # Overall is the minimum (all requirements must be met)
    overall_progress = min(videos_progress, views_progress, earnings_progress, wins_progress)

    return TierProgress(
        current_tier=membership.tier.value,
        next_tier=next_tier.value,
        videos_progress=videos_progress,
        views_progress=views_progress,
        earnings_progress=earnings_progress,
        wins_progress=wins_progress,
        overall_progress=overall_progress,
    )


@router.post("/refresh-stats")
async def refresh_membership_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PerformersAssociationResponse:
    """Refresh membership stats and check for tier upgrade."""
    from ....shared.models.video import Video
    from ....shared.models.monetization import Transaction, TransactionType

    result = await session.execute(
        select(PerformersAssociationMembership).where(
            PerformersAssociationMembership.user_id == current_user.id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        membership = PerformersAssociationMembership(
            user_id=current_user.id,
            tier=PerformersAssociationTier.EMERGING,
        )
        session.add(membership)

    # Count videos
    video_count = await session.execute(
        select(func.count(Video.id)).where(Video.creator_id == current_user.id)
    )
    membership.total_videos = video_count.scalar() or 0

    # Sum views
    view_sum = await session.execute(
        select(func.sum(Video.view_count)).where(Video.creator_id == current_user.id)
    )
    membership.total_views = view_sum.scalar() or 0

    # Sum earnings
    earnings_sum = await session.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == TransactionType.EARNING,
            )
        )
    )
    membership.total_earnings = earnings_sum.scalar() or Decimal("0.00")

    # Check for tier upgrade
    old_tier = membership.tier
    for tier in reversed(list(PerformersAssociationTier)):
        requirements = TIER_REQUIREMENTS.get(tier, {})
        if (
            membership.total_videos >= requirements.get("min_videos", 0)
            and membership.total_views >= requirements.get("min_views", 0)
            and membership.total_earnings >= requirements.get("min_earnings", Decimal("0.00"))
            and membership.corecast_wins >= requirements.get("min_corecast_wins", 0)
        ):
            if tier != membership.tier:
                membership.previous_tier = membership.tier
                membership.tier = tier
                membership.tier_achieved_at = datetime.utcnow()

                # Award new tier badge
                new_badge = TIER_BENEFITS.get(tier, {}).get("badge")
                if new_badge:
                    badge = UserBadge(
                        user_id=current_user.id,
                        badge_type=new_badge,
                        award_reason=f"Achieved {tier.value} tier in Performers Association",
                    )
                    session.add(badge)

                logger.info(
                    f"User {current_user.id} upgraded from {old_tier.value} to {tier.value}"
                )
            break

    await session.commit()
    await session.refresh(membership)

    return membership


@router.get("/leaderboard", response_model=list[dict])
async def get_association_leaderboard(
    tier: Optional[str] = None,
    sort_by: str = Query(default="earnings"),  # earnings, views, wins
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get Performers Association leaderboard."""
    query = select(PerformersAssociationMembership).where(
        PerformersAssociationMembership.is_active == True
    )

    if tier:
        try:
            tier_enum = PerformersAssociationTier(tier)
            query = query.where(PerformersAssociationMembership.tier == tier_enum)
        except ValueError:
            pass

    # Apply sorting
    if sort_by == "views":
        query = query.order_by(desc(PerformersAssociationMembership.total_views))
    elif sort_by == "wins":
        query = query.order_by(desc(PerformersAssociationMembership.corecast_wins))
    else:  # earnings
        query = query.order_by(desc(PerformersAssociationMembership.total_earnings))

    query = query.limit(limit)

    result = await session.execute(query)
    memberships = list(result.scalars().all())

    leaderboard = []
    for rank, membership in enumerate(memberships, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": str(membership.user_id),
            "tier": membership.tier.value,
            "total_videos": membership.total_videos,
            "total_views": membership.total_views,
            "total_earnings": float(membership.total_earnings),
            "corecast_wins": membership.corecast_wins,
            "corecast_participations": membership.corecast_participations,
            "fee_reduction": membership.fee_reduction,
        })

    return leaderboard


@router.post("/suspend/{user_id}", status_code=status.HTTP_200_OK)
async def suspend_membership(
    user_id: UUID,
    reason: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """Suspend a user's membership (admin only)."""
    result = await session.execute(
        select(PerformersAssociationMembership).where(
            PerformersAssociationMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    membership.is_active = False
    membership.suspended_at = datetime.utcnow()
    membership.suspension_reason = reason

    await session.commit()

    logger.info(f"Suspended membership for user {user_id}: {reason}")
    return {"status": "suspended", "user_id": str(user_id)}


@router.post("/reinstate/{user_id}", status_code=status.HTTP_200_OK)
async def reinstate_membership(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_admin),
) -> PerformersAssociationResponse:
    """Reinstate a suspended membership (admin only)."""
    result = await session.execute(
        select(PerformersAssociationMembership).where(
            PerformersAssociationMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    membership.is_active = True
    membership.suspended_at = None
    membership.suspension_reason = None

    await session.commit()
    await session.refresh(membership)

    logger.info(f"Reinstated membership for user {user_id}")
    return membership
