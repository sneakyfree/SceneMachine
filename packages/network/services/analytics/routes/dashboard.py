"""
Creator dashboard routes for analytics service.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    CreatorProfile,
    Follow,
    Transaction,
    TransactionType,
    TransactionStatus,
    User,
    Video,
    VideoStatus,
    ViewEvent,
    WatchSession,
)
from ...auth.dependencies import get_current_user
from ..schemas import (
    DashboardSummary,
    VideoAnalytics,
    VideoAnalyticsListResponse,
    TimeSeriesResponse,
    TimeSeriesDataPoint,
    AudienceInsights,
    RealTimeMetrics,
    ContentPerformanceResponse,
    RevenueAnalytics,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    """Get creator dashboard summary."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    # Get total videos
    result = await db.execute(
        select(func.count()).where(
            and_(
                Video.creator_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
    )
    total_videos = result.scalar() or 0

    # Get total views and watch time
    result = await db.execute(
        select(func.sum(Video.view_count)).where(
            and_(
                Video.creator_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
    )
    total_views = result.scalar() or 0

    # Get watch time from sessions
    result = await db.execute(
        select(func.sum(WatchSession.watch_time_seconds))
        .join(Video, Video.id == WatchSession.video_id)
        .where(Video.creator_id == current_user.id)
    )
    total_watch_seconds = result.scalar() or 0
    total_watch_time_hours = total_watch_seconds / 3600

    # Get subscriber count
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    total_subscribers = profile.subscriber_count if profile else 0

    # Subscriber change in 30 days
    result = await db.execute(
        select(func.count()).where(
            and_(
                Follow.following_id == current_user.id,
                Follow.created_at >= thirty_days_ago,
            )
        )
    )
    subscriber_change_30d = result.scalar() or 0

    # Revenue last 30 days
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= thirty_days_ago,
            )
        )
    )
    revenue_30d = result.scalar() or Decimal("0")

    # Revenue previous 30 days for comparison
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.creator_id == current_user.id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= sixty_days_ago,
                Transaction.created_at < thirty_days_ago,
            )
        )
    )
    revenue_prev_30d = result.scalar() or Decimal("0")

    if revenue_prev_30d > 0:
        revenue_change = float((revenue_30d - revenue_prev_30d) / revenue_prev_30d * 100)
    else:
        revenue_change = 100.0 if revenue_30d > 0 else 0.0

    # Estimated MTD revenue
    days_in_month = now.day
    daily_avg = revenue_30d / 30 if revenue_30d > 0 else Decimal("0")
    estimated_mtd = daily_avg * days_in_month

    # Average watch percent
    result = await db.execute(
        select(func.avg(ViewEvent.watch_percent))
        .join(Video, Video.id == ViewEvent.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                ViewEvent.is_valid_view == True,
            )
        )
    )
    avg_watch_percent = result.scalar() or 0.0

    # Like rate
    result = await db.execute(
        select(func.sum(Video.like_count), func.sum(Video.view_count)).where(
            and_(
                Video.creator_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
    )
    row = result.first()
    total_likes = row[0] or 0
    total_video_views = row[1] or 1
    like_rate = (total_likes / total_video_views) * 100 if total_video_views > 0 else 0

    # Top performing video
    result = await db.execute(
        select(Video)
        .where(
            and_(
                Video.creator_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
        .order_by(Video.view_count.desc())
        .limit(1)
    )
    top_video = result.scalar_one_or_none()

    # Get top video views in last 30 days
    top_video_views_30d = 0
    if top_video:
        result = await db.execute(
            select(func.count()).where(
                and_(
                    ViewEvent.video_id == top_video.id,
                    ViewEvent.viewed_at >= thirty_days_ago,
                    ViewEvent.is_valid_view == True,
                )
            )
        )
        top_video_views_30d = result.scalar() or 0

    return DashboardSummary(
        total_videos=total_videos,
        total_views=total_views,
        total_watch_time_hours=round(total_watch_time_hours, 1),
        total_subscribers=total_subscribers,
        subscriber_change_30d=subscriber_change_30d,
        total_revenue_30d=revenue_30d,
        revenue_change_percent=round(revenue_change, 1),
        estimated_revenue_mtd=estimated_mtd,
        average_watch_percent=round(avg_watch_percent, 1),
        average_ctr=0.0,  # Would need impression data
        like_rate=round(like_rate, 2),
        top_video_id=top_video.id if top_video else None,
        top_video_title=top_video.title if top_video else None,
        top_video_views_30d=top_video_views_30d,
    )


@router.get("/videos", response_model=VideoAnalyticsListResponse)
async def get_video_analytics_list(
    sort: str = Query("views", regex="^(views|revenue|date|engagement)$"),
    period: str = Query("30d", regex="^(7d|30d|90d|all)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoAnalyticsListResponse:
    """Get analytics for all videos."""
    now = datetime.now(timezone.utc)

    if period == "7d":
        since = now - timedelta(days=7)
    elif period == "30d":
        since = now - timedelta(days=30)
    elif period == "90d":
        since = now - timedelta(days=90)
    else:
        since = None

    # Get videos
    query = select(Video).where(
        and_(
            Video.creator_id == current_user.id,
            Video.status == VideoStatus.PUBLISHED,
        )
    )

    if sort == "views":
        query = query.order_by(Video.view_count.desc())
    elif sort == "revenue":
        # Would need subquery for revenue
        query = query.order_by(Video.view_count.desc())
    elif sort == "date":
        query = query.order_by(Video.published_at.desc())
    elif sort == "engagement":
        query = query.order_by(Video.quality_score.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    videos = result.scalars().all()

    # Build analytics for each video
    analytics_list = []
    for video in videos:
        # Get period views
        view_query = select(func.count()).where(
            and_(
                ViewEvent.video_id == video.id,
                ViewEvent.is_valid_view == True,
            )
        )
        if since:
            view_query = view_query.where(ViewEvent.viewed_at >= since)

        result = await db.execute(view_query)
        period_views = result.scalar() or 0

        # Get watch time
        result = await db.execute(
            select(func.sum(WatchSession.watch_time_seconds)).where(
                WatchSession.video_id == video.id
            )
        )
        watch_time = result.scalar() or 0

        # Get revenue
        revenue_query = select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.video_id == video.id,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        if since:
            revenue_query = revenue_query.where(Transaction.created_at >= since)
        result = await db.execute(revenue_query)
        revenue = result.scalar() or Decimal("0")

        analytics_list.append(
            VideoAnalytics(
                video_id=video.id,
                title=video.title,
                thumbnail_url=video.thumbnail_url,
                total_views=video.view_count,
                views_30d=period_views if period == "30d" else 0,
                views_7d=0,  # Would need separate query
                views_today=0,
                total_watch_time_hours=watch_time / 3600,
                average_view_duration_seconds=watch_time / max(video.view_count, 1),
                average_view_percent=0,
                like_count=video.like_count,
                dislike_count=0,
                comment_count=video.comment_count,
                share_count=video.share_count,
                like_rate=(video.like_count / max(video.view_count, 1)) * 100,
                retention_curve=[100, 90, 80, 70, 60, 50, 45, 40, 35, 30],
                traffic_sources={
                    "direct": 40.0,
                    "search": 30.0,
                    "suggested": 20.0,
                    "external": 10.0,
                },
                age_distribution={},
                gender_distribution={},
                top_countries=[],
                device_distribution={
                    "desktop": 50.0,
                    "mobile": 40.0,
                    "tablet": 8.0,
                    "tv": 2.0,
                },
                revenue_30d=revenue,
                rpm=revenue / (period_views / 1000) if period_views > 0 else Decimal("0"),
            )
        )

    return VideoAnalyticsListResponse(
        videos=analytics_list,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/videos/{video_id}", response_model=VideoAnalytics)
async def get_video_analytics(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VideoAnalytics:
    """Get detailed analytics for a specific video."""
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Views by period
    result = await db.execute(
        select(func.count()).where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.is_valid_view == True,
                ViewEvent.viewed_at >= thirty_days_ago,
            )
        )
    )
    views_30d = result.scalar() or 0

    result = await db.execute(
        select(func.count()).where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.is_valid_view == True,
                ViewEvent.viewed_at >= seven_days_ago,
            )
        )
    )
    views_7d = result.scalar() or 0

    result = await db.execute(
        select(func.count()).where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.is_valid_view == True,
                ViewEvent.viewed_at >= today_start,
            )
        )
    )
    views_today = result.scalar() or 0

    # Watch time and average
    result = await db.execute(
        select(
            func.sum(WatchSession.watch_time_seconds),
            func.avg(WatchSession.watch_time_seconds),
        ).where(WatchSession.video_id == video_id)
    )
    row = result.first()
    total_watch_seconds = row[0] or 0
    avg_duration = row[1] or 0

    # Average watch percent
    result = await db.execute(
        select(func.avg(ViewEvent.watch_percent)).where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.is_valid_view == True,
            )
        )
    )
    avg_watch_percent = result.scalar() or 0

    # Revenue
    result = await db.execute(
        select(func.sum(Transaction.amount_net)).where(
            and_(
                Transaction.video_id == video_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= thirty_days_ago,
            )
        )
    )
    revenue_30d = result.scalar() or Decimal("0")

    # Country breakdown
    result = await db.execute(
        select(ViewEvent.country_code, func.count())
        .where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.country_code.isnot(None),
            )
        )
        .group_by(ViewEvent.country_code)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_countries = [
        {"country_code": code, "views": count, "percent": 0}
        for code, count in result.all()
    ]

    # Device breakdown
    result = await db.execute(
        select(ViewEvent.device_type, func.count())
        .where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.device_type.isnot(None),
            )
        )
        .group_by(ViewEvent.device_type)
    )
    device_counts = dict(result.all())
    total_device = sum(device_counts.values()) or 1
    device_distribution = {
        k: round((v / total_device) * 100, 1) for k, v in device_counts.items()
    }

    return VideoAnalytics(
        video_id=video.id,
        title=video.title,
        thumbnail_url=video.thumbnail_url,
        total_views=video.view_count,
        views_30d=views_30d,
        views_7d=views_7d,
        views_today=views_today,
        total_watch_time_hours=total_watch_seconds / 3600,
        average_view_duration_seconds=avg_duration,
        average_view_percent=avg_watch_percent,
        like_count=video.like_count,
        dislike_count=0,
        comment_count=video.comment_count,
        share_count=video.share_count,
        like_rate=(video.like_count / max(video.view_count, 1)) * 100,
        retention_curve=[100, 90, 80, 70, 60, 50, 45, 40, 35, 30],  # Placeholder
        traffic_sources={
            "direct": 40.0,
            "search": 30.0,
            "suggested": 20.0,
            "external": 10.0,
        },
        age_distribution={},
        gender_distribution={},
        top_countries=top_countries,
        device_distribution=device_distribution,
        revenue_30d=revenue_30d,
        rpm=revenue_30d / (views_30d / 1000) if views_30d > 0 else Decimal("0"),
    )


@router.get("/realtime", response_model=RealTimeMetrics)
async def get_realtime_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RealTimeMetrics:
    """Get real-time streaming metrics."""
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    forty_eight_hours_ago = now - timedelta(hours=48)
    five_minutes_ago = now - timedelta(minutes=5)

    # Current viewers (active sessions in last 5 minutes)
    result = await db.execute(
        select(func.count())
        .select_from(WatchSession)
        .join(Video, Video.id == WatchSession.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                WatchSession.is_active == True,
                WatchSession.last_heartbeat_at >= five_minutes_ago,
            )
        )
    )
    current_viewers = result.scalar() or 0

    # Views last hour
    result = await db.execute(
        select(func.count())
        .select_from(ViewEvent)
        .join(Video, Video.id == ViewEvent.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                ViewEvent.viewed_at >= one_hour_ago,
            )
        )
    )
    views_last_hour = result.scalar() or 0

    # Views last 48 hours
    result = await db.execute(
        select(func.count())
        .select_from(ViewEvent)
        .join(Video, Video.id == ViewEvent.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                ViewEvent.viewed_at >= forty_eight_hours_ago,
            )
        )
    )
    views_last_48h = result.scalar() or 0

    # Active videos with current viewers
    result = await db.execute(
        select(Video.id, Video.title, func.count(WatchSession.id))
        .join(WatchSession, WatchSession.video_id == Video.id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                WatchSession.is_active == True,
                WatchSession.last_heartbeat_at >= five_minutes_ago,
            )
        )
        .group_by(Video.id, Video.title)
        .order_by(func.count(WatchSession.id).desc())
        .limit(5)
    )
    active_videos = [
        {"video_id": str(vid), "title": title, "current_viewers": count}
        for vid, title, count in result.all()
    ]

    return RealTimeMetrics(
        current_viewers=current_viewers,
        views_last_hour=views_last_hour,
        views_last_48_hours=views_last_48h,
        active_videos=active_videos,
        recent_comments=0,  # Would need separate query
        recent_likes=0,
        recent_subscribers=0,
    )


@router.get("/views/timeseries", response_model=TimeSeriesResponse)
async def get_views_timeseries(
    period: str = Query("30d", regex="^(7d|30d|90d|365d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimeSeriesResponse:
    """Get views over time."""
    now = datetime.now(timezone.utc)

    if period == "7d":
        days = 7
    elif period == "30d":
        days = 30
    elif period == "90d":
        days = 90
    else:
        days = 365

    since = now - timedelta(days=days)

    # Get daily view counts
    result = await db.execute(
        select(
            func.date(ViewEvent.viewed_at).label("date"),
            func.count().label("count"),
        )
        .join(Video, Video.id == ViewEvent.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                ViewEvent.viewed_at >= since,
                ViewEvent.is_valid_view == True,
            )
        )
        .group_by(func.date(ViewEvent.viewed_at))
        .order_by(func.date(ViewEvent.viewed_at))
    )
    rows = result.all()

    data = [TimeSeriesDataPoint(date=row.date, value=row.count) for row in rows]
    total = sum(d.value for d in data)
    average = total / len(data) if data else 0

    # Calculate change
    midpoint = len(data) // 2
    first_half = sum(d.value for d in data[:midpoint]) if midpoint > 0 else 0
    second_half = sum(d.value for d in data[midpoint:]) if midpoint > 0 else 0
    change = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

    return TimeSeriesResponse(
        metric="views",
        period=period,
        data=data,
        total=total,
        average=average,
        change_percent=round(change, 1),
    )
