"""MovieHeaven (long-form) distribution routes."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.distribution import (
    ContentFormat,
    MovieHeavenContent,
    MovieHeavenSubscription,
    PPVPurchase,
    PPVStatus,
    PremiereType,
    SubscriptionTier,
)
from ....shared.models.user import User
from ....shared.models.video import Video
from ...auth.dependencies import get_current_user
from ..schemas import (
    ContentBrowseParams,
    MovieHeavenContentCreate,
    MovieHeavenContentResponse,
    PPVPurchaseCreate,
    PPVPurchaseResponse,
    SubscriptionCreate,
    SubscriptionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/movie-heaven", tags=["MovieHeaven"])

# Subscription pricing
SUBSCRIPTION_PRICES = {
    SubscriptionTier.BASIC: Decimal("9.99"),
    SubscriptionTier.PREMIUM: Decimal("14.99"),
    SubscriptionTier.ULTIMATE: Decimal("19.99"),
}


@router.post(
    "/content", response_model=MovieHeavenContentResponse, status_code=status.HTTP_201_CREATED
)
async def create_content(
    data: MovieHeavenContentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MovieHeavenContent:
    """Create MovieHeaven content from a video."""
    # Verify video exists and belongs to user
    video = await session.get(Video, data.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to publish this video")

    # Check minimum duration (10 minutes for MovieHeaven)
    if video.duration_seconds < 600:
        raise HTTPException(
            status_code=400,
            detail="Video too short for MovieHeaven (min 10 minutes)",
        )

    # Check if already posted
    existing = await session.execute(
        select(MovieHeavenContent).where(MovieHeavenContent.video_id == data.video_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Video already published to MovieHeaven")

    # Parse format
    try:
        content_format = ContentFormat(data.format)
    except ValueError:
        content_format = ContentFormat.HORIZONTAL_169

    # Parse premiere type
    premiere_type = None
    if data.premiere_type:
        try:
            premiere_type = PremiereType(data.premiere_type)
        except ValueError:
            pass

    # Parse subscription tier
    minimum_tier = None
    if data.minimum_tier:
        try:
            minimum_tier = SubscriptionTier(data.minimum_tier)
        except ValueError:
            pass

    content = MovieHeavenContent(
        video_id=data.video_id,
        creator_id=current_user.id,
        format=content_format,
        runtime_minutes=data.runtime_minutes,
        is_feature_film=data.is_feature_film,
        ppv_price=data.ppv_price,
        rental_price=data.rental_price,
        rental_duration_hours=data.rental_duration_hours,
        minimum_tier=minimum_tier,
        is_free=data.is_free,
        premiere_type=premiere_type,
        premiere_date=data.premiere_date,
        genres=data.genres[:10],  # Max 10 genres
        cast_names=data.cast_names[:50],  # Max 50 cast members
        crew_credits=data.crew_credits,
        available_qualities=["720p", "1080p"],  # Default qualities
    )

    session.add(content)
    await session.commit()
    await session.refresh(content)

    logger.info(f"Created MovieHeaven content {content.id} for video {data.video_id}")
    return content


@router.get("/content/{content_id}", response_model=MovieHeavenContentResponse)
async def get_content(
    content_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> MovieHeavenContent:
    """Get MovieHeaven content by ID."""
    content = await session.get(MovieHeavenContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.get("/browse", response_model=list[MovieHeavenContentResponse])
async def browse_content(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    genre: Optional[str] = None,
    is_feature_film: Optional[bool] = None,
    min_rating: Optional[float] = None,
    has_premiere: Optional[bool] = None,
    is_free: Optional[bool] = None,
    sort_by: str = Query(default="newest"),
    session: AsyncSession = Depends(get_session),
) -> list[MovieHeavenContent]:
    """Browse MovieHeaven content with filters."""
    query = select(MovieHeavenContent)

    # Apply filters
    if genre:
        query = query.where(MovieHeavenContent.genres.contains([genre]))
    if is_feature_film is not None:
        query = query.where(MovieHeavenContent.is_feature_film == is_feature_film)
    if min_rating is not None:
        query = query.where(MovieHeavenContent.audience_score >= min_rating)
    if has_premiere:
        query = query.where(MovieHeavenContent.premiere_date.isnot(None))
    if is_free is not None:
        query = query.where(MovieHeavenContent.is_free == is_free)

    # Apply sorting
    if sort_by == "popular":
        query = query.order_by(desc(MovieHeavenContent.total_purchases + MovieHeavenContent.total_rentals))
    elif sort_by == "rating":
        query = query.order_by(desc(MovieHeavenContent.audience_score))
    elif sort_by == "premiere":
        query = query.where(MovieHeavenContent.premiere_date.isnot(None))
        query = query.order_by(desc(MovieHeavenContent.premiere_date))
    else:  # newest
        query = query.order_by(desc(MovieHeavenContent.created_at))

    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/premieres", response_model=list[MovieHeavenContentResponse])
async def get_premieres(
    limit: int = Query(default=10, ge=1, le=50),
    upcoming_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[MovieHeavenContent]:
    """Get premiere content."""
    query = select(MovieHeavenContent).where(MovieHeavenContent.premiere_type.isnot(None))

    if upcoming_only:
        query = query.where(
            and_(
                MovieHeavenContent.premiere_date > datetime.utcnow(),
                MovieHeavenContent.premiere_ended == False,
            )
        )
    else:
        query = query.where(MovieHeavenContent.premiere_ended == False)

    query = query.order_by(MovieHeavenContent.premiere_date).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/featured", response_model=list[MovieHeavenContentResponse])
async def get_featured(
    limit: int = Query(default=10, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> list[MovieHeavenContent]:
    """Get featured/staff pick content."""
    # Feature films with good ratings and festival recognition
    query = (
        select(MovieHeavenContent)
        .where(
            or_(
                MovieHeavenContent.festival_wins > 0,
                MovieHeavenContent.audience_score >= 8.0,
            )
        )
        .order_by(
            desc(MovieHeavenContent.festival_wins),
            desc(MovieHeavenContent.audience_score),
        )
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())


# ============================================================================
# PPV Purchase Endpoints
# ============================================================================


@router.post("/purchase", response_model=PPVPurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_content(
    data: PPVPurchaseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PPVPurchase:
    """Purchase or rent MovieHeaven content."""
    content = await session.get(MovieHeavenContent, data.content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Check if free
    if content.is_free:
        raise HTTPException(status_code=400, detail="This content is free")

    # Check existing purchase
    existing = await session.execute(
        select(PPVPurchase).where(
            and_(
                PPVPurchase.user_id == current_user.id,
                PPVPurchase.content_id == data.content_id,
                or_(
                    PPVPurchase.is_rental == False,  # Permanent purchase
                    and_(
                        PPVPurchase.is_rental == True,
                        PPVPurchase.expires_at > datetime.utcnow(),
                    ),  # Active rental
                ),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have access to this content")

    # Determine price
    if data.is_rental:
        if not content.rental_price:
            raise HTTPException(status_code=400, detail="Rental not available for this content")
        price = content.rental_price
        expires_at = datetime.utcnow() + timedelta(hours=content.rental_duration_hours)
    else:
        if not content.ppv_price:
            raise HTTPException(status_code=400, detail="Purchase not available for this content")
        price = content.ppv_price
        expires_at = None

    # TODO: Integrate with Stripe for actual payment
    # For now, create the purchase record directly

    purchase = PPVPurchase(
        user_id=current_user.id,
        content_id=data.content_id,
        is_rental=data.is_rental,
        price_paid=price,
        currency="USD",
        status=PPVStatus.COMPLETED,
        expires_at=expires_at,
    )
    session.add(purchase)

    # Update content revenue
    if data.is_rental:
        content.total_rental_revenue += price
        content.total_rentals += 1
    else:
        content.total_ppv_revenue += price
        content.total_purchases += 1

    await session.commit()
    await session.refresh(purchase)

    logger.info(
        f"User {current_user.id} {'rented' if data.is_rental else 'purchased'} content {data.content_id}"
    )
    return purchase


@router.get("/purchases", response_model=list[PPVPurchaseResponse])
async def get_my_purchases(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_expired: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[PPVPurchase]:
    """Get user's PPV purchases."""
    query = select(PPVPurchase).where(PPVPurchase.user_id == current_user.id)

    if not include_expired:
        query = query.where(
            or_(
                PPVPurchase.expires_at.is_(None),
                PPVPurchase.expires_at > datetime.utcnow(),
            )
        )

    query = query.order_by(desc(PPVPurchase.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/access/{content_id}")
async def check_access(
    content_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Check if user has access to content."""
    content = await session.get(MovieHeavenContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Free content
    if content.is_free:
        return {"has_access": True, "access_type": "free"}

    # Check subscription
    if content.minimum_tier:
        sub = await session.execute(
            select(MovieHeavenSubscription).where(
                and_(
                    MovieHeavenSubscription.user_id == current_user.id,
                    MovieHeavenSubscription.is_active == True,
                )
            )
        )
        subscription = sub.scalar_one_or_none()
        if subscription:
            # Check tier hierarchy
            tier_order = [SubscriptionTier.BASIC, SubscriptionTier.PREMIUM, SubscriptionTier.ULTIMATE]
            if tier_order.index(subscription.tier) >= tier_order.index(content.minimum_tier):
                return {"has_access": True, "access_type": "subscription", "tier": subscription.tier.value}

    # Check PPV purchase
    purchase = await session.execute(
        select(PPVPurchase).where(
            and_(
                PPVPurchase.user_id == current_user.id,
                PPVPurchase.content_id == content_id,
                PPVPurchase.status == PPVStatus.COMPLETED,
                or_(
                    PPVPurchase.expires_at.is_(None),
                    PPVPurchase.expires_at > datetime.utcnow(),
                ),
            )
        )
    )
    ppv = purchase.scalar_one_or_none()
    if ppv:
        access_type = "rental" if ppv.is_rental else "purchase"
        return {
            "has_access": True,
            "access_type": access_type,
            "expires_at": ppv.expires_at.isoformat() if ppv.expires_at else None,
        }

    # No access
    return {
        "has_access": False,
        "ppv_price": float(content.ppv_price) if content.ppv_price else None,
        "rental_price": float(content.rental_price) if content.rental_price else None,
        "minimum_tier": content.minimum_tier.value if content.minimum_tier else None,
    }


# ============================================================================
# Subscription Endpoints
# ============================================================================


@router.post(
    "/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    data: SubscriptionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MovieHeavenSubscription:
    """Create or upgrade a subscription."""
    try:
        tier = SubscriptionTier(data.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")

    # Check existing subscription
    existing = await session.execute(
        select(MovieHeavenSubscription).where(
            MovieHeavenSubscription.user_id == current_user.id
        )
    )
    subscription = existing.scalar_one_or_none()

    price = SUBSCRIPTION_PRICES[tier]

    if subscription:
        # Upgrade/change subscription
        subscription.tier = tier
        subscription.monthly_price = price
        subscription.cancelled_at = None
        subscription.cancellation_reason = None
        subscription.is_active = True
    else:
        # New subscription
        subscription = MovieHeavenSubscription(
            user_id=current_user.id,
            tier=tier,
            monthly_price=price,
            billing_cycle_start=datetime.utcnow(),
            next_billing_date=datetime.utcnow() + timedelta(days=30),
        )
        session.add(subscription)

    # TODO: Integrate with Stripe for actual billing

    await session.commit()
    await session.refresh(subscription)

    logger.info(f"User {current_user.id} subscribed to {tier.value}")
    return subscription


@router.get("/subscriptions/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MovieHeavenSubscription:
    """Get current user's subscription."""
    result = await session.execute(
        select(MovieHeavenSubscription).where(
            MovieHeavenSubscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    return subscription


@router.delete("/subscriptions/me", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_subscription(
    reason: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Cancel subscription."""
    result = await session.execute(
        select(MovieHeavenSubscription).where(
            MovieHeavenSubscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    subscription.cancelled_at = datetime.utcnow()
    subscription.cancellation_reason = reason
    # Subscription remains active until next billing date
    # is_active will be set to False by a scheduled task

    await session.commit()
    logger.info(f"User {current_user.id} cancelled subscription")


# ============================================================================
# Reviews & Ratings
# ============================================================================


@router.post("/content/{content_id}/rate")
async def rate_content(
    content_id: UUID,
    rating: float = Query(ge=0, le=10),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Rate MovieHeaven content (0-10 scale)."""
    content = await session.get(MovieHeavenContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Simple average for now (should use weighted average with review records)
    if content.audience_score is None:
        content.audience_score = rating
        content.review_count = 1
    else:
        # Running average
        content.audience_score = (
            (content.audience_score * content.review_count) + rating
        ) / (content.review_count + 1)
        content.review_count += 1

    await session.commit()

    return {
        "audience_score": content.audience_score,
        "review_count": content.review_count,
    }


@router.patch("/content/{content_id}")
async def update_content(
    content_id: UUID,
    ppv_price: Optional[Decimal] = None,
    rental_price: Optional[Decimal] = None,
    is_free: Optional[bool] = None,
    genres: Optional[list[str]] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MovieHeavenContentResponse:
    """Update MovieHeaven content settings."""
    content = await session.get(MovieHeavenContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if ppv_price is not None:
        content.ppv_price = ppv_price
    if rental_price is not None:
        content.rental_price = rental_price
    if is_free is not None:
        content.is_free = is_free
    if genres is not None:
        content.genres = genres[:10]

    await session.commit()
    await session.refresh(content)

    return content


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete MovieHeaven content."""
    content = await session.get(MovieHeavenContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await session.delete(content)
    await session.commit()
    logger.info(f"Deleted MovieHeaven content {content_id}")
