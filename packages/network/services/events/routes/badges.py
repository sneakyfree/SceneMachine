"""Badge management routes."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.events import (
    BADGE_DISPLAY,
    BadgeType,
    UserBadge,
)
from ....shared.models.user import User
from ...auth.dependencies import get_current_user
from ..schemas import BadgeAwardRequest, BadgeInfo, UserBadgeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/badges", tags=["Badges"])


@router.get("/types", response_model=list[dict])
async def list_badge_types() -> list[dict]:
    """List all available badge types."""
    badges = []
    for badge_type in BadgeType:
        display = BADGE_DISPLAY.get(
            badge_type, {"emoji": "🏅", "name": badge_type.value, "color": "#808080"}
        )
        badges.append({
            "type": badge_type.value,
            "emoji": display["emoji"],
            "name": display["name"],
            "color": display["color"],
            "category": _get_badge_category(badge_type),
        })
    return badges


def _get_badge_category(badge_type: BadgeType) -> str:
    """Get category for a badge type."""
    competition = {
        BadgeType.GOLD, BadgeType.SILVER, BadgeType.BRONZE,
        BadgeType.FINALIST, BadgeType.TOP_25, BadgeType.TOP_50,
        BadgeType.TOP_100, BadgeType.PARTICIPANT,
    }
    special = {
        BadgeType.PEOPLES_CHOICE, BadgeType.RISING_STAR,
        BadgeType.INNOVATION, BadgeType.TECHNICAL,
        BadgeType.STORYTELLING, BadgeType.VISUAL,
    }
    association = {
        BadgeType.EMERGING, BadgeType.ESTABLISHED,
        BadgeType.PROFESSIONAL, BadgeType.ELITE, BadgeType.LEGEND,
    }

    if badge_type in competition:
        return "competition"
    elif badge_type in special:
        return "special"
    elif badge_type in association:
        return "association"
    return "other"


@router.get("/mine", response_model=list[UserBadgeResponse])
async def get_my_badges(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[UserBadge]:
    """Get current user's badges."""
    query = (
        select(UserBadge)
        .where(UserBadge.user_id == current_user.id)
        .order_by(desc(UserBadge.awarded_at))
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/user/{user_id}", response_model=list[UserBadgeResponse])
async def get_user_badges(
    user_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[UserBadge]:
    """Get a user's badges."""
    query = (
        select(UserBadge)
        .where(UserBadge.user_id == user_id)
        .order_by(desc(UserBadge.awarded_at))
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/user/{user_id}/featured", response_model=list[UserBadgeResponse])
async def get_user_featured_badges(
    user_id: UUID,
    limit: int = Query(default=5, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
) -> list[UserBadge]:
    """Get a user's featured badges."""
    query = (
        select(UserBadge)
        .where(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.is_featured == True,
            )
        )
        .order_by(desc(UserBadge.awarded_at))
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.patch("/{badge_id}/feature")
async def toggle_featured_badge(
    badge_id: UUID,
    featured: bool = True,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserBadgeResponse:
    """Toggle whether a badge is featured on profile."""
    badge = await session.get(UserBadge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    if badge.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Limit to 5 featured badges
    if featured:
        featured_count = await session.execute(
            select(UserBadge).where(
                and_(
                    UserBadge.user_id == current_user.id,
                    UserBadge.is_featured == True,
                    UserBadge.id != badge_id,
                )
            )
        )
        if len(list(featured_count.scalars().all())) >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 featured badges")

    badge.is_featured = featured
    await session.commit()
    await session.refresh(badge)

    return badge


@router.post("/award", response_model=UserBadgeResponse, status_code=status.HTTP_201_CREATED)
async def award_badge(
    data: BadgeAwardRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserBadge:
    """Award a badge to a user (admin only)."""
    # TODO: Add admin role check

    try:
        badge_type = BadgeType(data.badge_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid badge type")

    # Check if user exists
    user = await session.get(User, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for duplicate badge (for competition badges with event)
    if data.event_id:
        existing = await session.execute(
            select(UserBadge).where(
                and_(
                    UserBadge.user_id == data.user_id,
                    UserBadge.badge_type == badge_type,
                    UserBadge.event_id == data.event_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Badge already awarded for this event")

    badge = UserBadge(
        user_id=data.user_id,
        badge_type=badge_type,
        event_id=data.event_id,
        award_reason=data.award_reason,
    )

    session.add(badge)
    await session.commit()
    await session.refresh(badge)

    logger.info(f"Awarded badge {badge_type.value} to user {data.user_id}")
    return badge


@router.delete("/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_badge(
    badge_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke a badge (admin only)."""
    # TODO: Add admin role check

    badge = await session.get(UserBadge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    await session.delete(badge)
    await session.commit()

    logger.info(f"Revoked badge {badge_id}")


@router.get("/stats/{user_id}")
async def get_badge_stats(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get badge statistics for a user."""
    badges = await session.execute(
        select(UserBadge).where(UserBadge.user_id == user_id)
    )
    all_badges = list(badges.scalars().all())

    # Count by category
    competition_count = sum(
        1 for b in all_badges if _get_badge_category(b.badge_type) == "competition"
    )
    special_count = sum(
        1 for b in all_badges if _get_badge_category(b.badge_type) == "special"
    )
    association_count = sum(
        1 for b in all_badges if _get_badge_category(b.badge_type) == "association"
    )

    # Count specific achievements
    gold_count = sum(1 for b in all_badges if b.badge_type == BadgeType.GOLD)
    silver_count = sum(1 for b in all_badges if b.badge_type == BadgeType.SILVER)
    bronze_count = sum(1 for b in all_badges if b.badge_type == BadgeType.BRONZE)

    # Get highest tier
    tiers = [BadgeType.LEGEND, BadgeType.ELITE, BadgeType.PROFESSIONAL, BadgeType.ESTABLISHED, BadgeType.EMERGING]
    highest_tier = None
    for tier in tiers:
        if any(b.badge_type == tier for b in all_badges):
            highest_tier = tier.value
            break

    return {
        "user_id": str(user_id),
        "total_badges": len(all_badges),
        "competition_badges": competition_count,
        "special_badges": special_count,
        "association_badges": association_count,
        "gold_medals": gold_count,
        "silver_medals": silver_count,
        "bronze_medals": bronze_count,
        "total_medals": gold_count + silver_count + bronze_count,
        "highest_tier": highest_tier,
        "featured_count": sum(1 for b in all_badges if b.is_featured),
    }
