"""
Earnings routes for monetization service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    CreatorProfile,
    Transaction,
    TransactionType,
    TransactionStatus,
    User,
    Video,
    CostTracking,
    REVENUE_TIERS,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    TransactionResponse,
    TransactionListResponse,
    EarningsSummaryResponse,
    EarningsBreakdownResponse,
    CostBreakdownResponse,
    CreatorCostSummaryResponse,
)

router = APIRouter(prefix="/earnings", tags=["earnings"])


def get_tier_info(total_earnings: Decimal) -> tuple[int, float, float]:
    """Get tier number and cut percentages for given earnings."""
    for i, (tier_min, tier_max, platform_cut) in enumerate(REVENUE_TIERS, 1):
        if tier_min <= total_earnings <= tier_max:
            platform_pct = float(platform_cut) * 100
            return i, platform_pct, 100 - platform_pct
    return 6, 1.0, 99.0


@router.get("/summary", response_model=EarningsSummaryResponse)
async def get_earnings_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EarningsSummaryResponse:
    """Get earnings summary for current user."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Get creator profile
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    total_all_time = profile.total_earnings if profile else Decimal("0")

    # This month earnings by type
    result = await db.execute(
        select(Transaction.transaction_type, func.sum(Transaction.amount_net))
        .where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= month_start,
            )
        )
        .group_by(Transaction.transaction_type)
    )
    this_month = dict(result.all())

    ad_revenue = this_month.get(TransactionType.AD_REVENUE, Decimal("0"))
    ticket_revenue = this_month.get(TransactionType.TICKET_SALE, Decimal("0"))
    tip_revenue = this_month.get(TransactionType.TIP, Decimal("0"))
    total_this_month = ad_revenue + ticket_revenue + tip_revenue

    # Last month total
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= last_month_start,
                Transaction.created_at < month_start,
            )
        )
    )
    total_last_month = result.scalar() or Decimal("0")

    # Calculate tier info
    tier, platform_cut, creator_cut = get_tier_info(total_all_time)

    # Available for payout (completed but not paid out)
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                # Add logic to exclude already paid out transactions
            )
        )
    )
    available = result.scalar() or Decimal("0")

    return EarningsSummaryResponse(
        creator_id=current_user.id,
        current_tier=tier,
        platform_cut_percent=platform_cut,
        creator_cut_percent=creator_cut,
        total_earnings_all_time=total_all_time,
        total_earnings_this_month=total_this_month,
        total_earnings_last_month=total_last_month,
        ad_revenue_this_month=ad_revenue,
        ticket_revenue_this_month=ticket_revenue,
        tip_revenue_this_month=tip_revenue,
        available_for_payout=available,
        pending_payout=Decimal("0"),  # TODO: Sum pending payouts
        period_start=month_start,
        period_end=now,
    )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    transaction_type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """Get transaction history."""
    # Base query
    query = select(Transaction).where(
        and_(
            Transaction.creator_id == current_user.id,
            Transaction.status == TransactionStatus.COMPLETED,
        )
    )

    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    if start_date:
        query = query.where(Transaction.created_at >= start_date)
    if end_date:
        query = query.where(Transaction.created_at <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Sum total earnings
    sum_query = select(func.sum(Transaction.amount_net)).select_from(query.subquery())
    result = await db.execute(sum_query)
    total_earnings = result.scalar() or Decimal("0")

    # Get transactions
    offset = (page - 1) * per_page
    query = query.order_by(Transaction.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    transactions = result.scalars().all()

    return TransactionListResponse(
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        total_earnings=total_earnings,
        page=page,
        per_page=per_page,
        has_more=(offset + len(transactions)) < total,
    )


@router.get("/breakdown", response_model=EarningsBreakdownResponse)
async def get_earnings_breakdown(
    period: str = Query("month", regex="^(day|week|month)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EarningsBreakdownResponse:
    """Get detailed earnings breakdown for a period."""
    now = datetime.now(timezone.utc)

    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    else:  # month
        since = now - timedelta(days=30)

    # Get earnings by type
    result = await db.execute(
        select(
            Transaction.transaction_type,
            func.sum(Transaction.amount_gross),
            func.sum(Transaction.platform_fee),
            func.sum(Transaction.processing_fee),
            func.sum(Transaction.amount_net),
        )
        .where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= since,
            )
        )
        .group_by(Transaction.transaction_type)
    )
    rows = result.all()

    ad_revenue = Decimal("0")
    ticket_revenue = Decimal("0")
    tip_revenue = Decimal("0")
    total_gross = Decimal("0")
    platform_fees = Decimal("0")
    processing_fees = Decimal("0")
    total_net = Decimal("0")

    for tx_type, gross, platform, processing, net in rows:
        if tx_type == TransactionType.AD_REVENUE:
            ad_revenue = net or Decimal("0")
        elif tx_type == TransactionType.TICKET_SALE:
            ticket_revenue = net or Decimal("0")
        elif tx_type == TransactionType.TIP:
            tip_revenue = net or Decimal("0")

        total_gross += gross or Decimal("0")
        platform_fees += platform or Decimal("0")
        processing_fees += processing or Decimal("0")
        total_net += net or Decimal("0")

    # Get video and view counts
    result = await db.execute(
        select(func.count(func.distinct(Transaction.video_id))).where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.created_at >= since,
            )
        )
    )
    video_count = result.scalar() or 0

    # View count would come from ViewEvent, simplified here
    view_count = 0

    return EarningsBreakdownResponse(
        period=period,
        ad_revenue=ad_revenue,
        ticket_revenue=ticket_revenue,
        tip_revenue=tip_revenue,
        total_gross=total_gross,
        platform_fees=platform_fees,
        processing_fees=processing_fees,
        total_net=total_net,
        video_count=video_count,
        view_count=view_count,
    )


@router.get("/costs", response_model=CreatorCostSummaryResponse)
async def get_cost_summary(
    month: Optional[str] = Query(None, regex="^\\d{4}-\\d{2}$"),  # YYYY-MM
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreatorCostSummaryResponse:
    """Get cost summary for creator."""
    if not month:
        now = datetime.now(timezone.utc)
        month = now.strftime("%Y-%m")

    # Parse month
    year, month_num = map(int, month.split("-"))
    month_start = datetime(year, month_num, 1, tzinfo=timezone.utc)

    # Get cost tracking data
    result = await db.execute(
        select(CostTracking)
        .join(Video, Video.id == CostTracking.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                CostTracking.month == month_start.date(),
            )
        )
    )
    costs = result.scalars().all()

    total_storage_gb = sum(c.storage_bytes / (1024**3) for c in costs)
    total_storage_cost = sum(c.storage_cost for c in costs)
    total_bandwidth_gb = sum(c.bandwidth_bytes / (1024**3) for c in costs)
    total_bandwidth_cost = sum(c.bandwidth_cost for c in costs)
    total_cost = sum(c.total_cost for c in costs)

    # Get revenue for the month
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= month_start,
                Transaction.created_at < month_start + timedelta(days=32),
            )
        )
    )
    total_revenue = result.scalar() or Decimal("0")

    # Count unprofitable videos
    unprofitable = sum(1 for c in costs if c.total_cost > (c.storage_cost * 0 + total_revenue / max(len(costs), 1)))

    return CreatorCostSummaryResponse(
        creator_id=current_user.id,
        month=month,
        total_storage_gb=round(total_storage_gb, 2),
        total_storage_cost=total_storage_cost,
        total_bandwidth_gb=round(total_bandwidth_gb, 2),
        total_bandwidth_cost=total_bandwidth_cost,
        total_processing_cost=Decimal("0"),  # Not tracked separately
        total_cost=total_cost,
        total_revenue=total_revenue,
        net_profit=total_revenue - total_cost,
        video_count=len(costs),
        unprofitable_videos=unprofitable,
    )


@router.get("/costs/{video_id}", response_model=CostBreakdownResponse)
async def get_video_cost_breakdown(
    video_id: uuid.UUID,
    month: Optional[str] = Query(None, regex="^\\d{4}-\\d{2}$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostBreakdownResponse:
    """Get cost breakdown for a specific video."""
    if not month:
        now = datetime.now(timezone.utc)
        month = now.strftime("%Y-%m")

    year, month_num = map(int, month.split("-"))
    month_start = datetime(year, month_num, 1, tzinfo=timezone.utc)

    # Verify ownership
    result = await db.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()
    if not video:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Get cost tracking
    result = await db.execute(
        select(CostTracking).where(
            and_(
                CostTracking.video_id == video_id,
                CostTracking.month == month_start.date(),
            )
        )
    )
    cost = result.scalar_one_or_none()

    if not cost:
        # No cost data for this month
        return CostBreakdownResponse(
            video_id=video_id,
            month=month,
            storage_gb=0,
            storage_cost=Decimal("0"),
            bandwidth_gb=0,
            bandwidth_cost=Decimal("0"),
            processing_cost=Decimal("0"),
            total_cost=Decimal("0"),
            revenue=Decimal("0"),
            net_profit=Decimal("0"),
            is_profitable=True,
        )

    # Get revenue for video this month
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.video_id == video_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= month_start,
                Transaction.created_at < month_start + timedelta(days=32),
            )
        )
    )
    revenue = result.scalar() or Decimal("0")

    return CostBreakdownResponse(
        video_id=video_id,
        month=month,
        storage_gb=round(cost.storage_bytes / (1024**3), 2),
        storage_cost=cost.storage_cost,
        bandwidth_gb=round(cost.bandwidth_bytes / (1024**3), 2),
        bandwidth_cost=cost.bandwidth_cost,
        processing_cost=Decimal("0"),
        total_cost=cost.total_cost,
        revenue=revenue,
        net_profit=revenue - cost.total_cost,
        is_profitable=revenue >= cost.total_cost,
    )
