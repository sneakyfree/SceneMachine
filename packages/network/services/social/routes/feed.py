"""
Social feed routes for social service.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_db
from ....shared.models import (
    Follow,
    User,
    Video,
    VideoStatus,
    WatchHistory,
    Share,
    Notification,
)
from ...auth.dependencies import get_current_user, get_optional_user
from ..schemas import (
    FeedResponse,
    ShareRequest,
    ShareResponse,
    NotificationResponse,
    NotificationListResponse,
    NotificationMarkReadRequest,
    UserSummary,
    VideoSummary,
)

router = APIRouter(tags=["feed"])


async def _build_video_summary(
    video: Video,
    db: AsyncSession,
) -> VideoSummary:
    """Build a video summary with creator info."""
    result = await db.execute(select(User).where(User.id == video.creator_id))
    creator = result.scalar_one()

    return VideoSummary(
        id=video.id,
        title=video.title,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=video.duration_seconds,
        creator_id=video.creator_id,
        creator_name=creator.display_name,
        view_count=video.view_count,
        like_count=video.like_count,
    )


@router.get("/feed", response_model=FeedResponse)
async def get_personalized_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    """
    Get personalized feed for current user.

    Algorithm:
    - 40% from followed creators (recent uploads)
    - 30% similar to watch history
    - 20% trending in interests
    - 10% discovery (new creators)
    """
    offset = (page - 1) * per_page

    # For MVP, prioritize followed creators then trending
    # Get videos from followed creators
    followed_query = (
        select(Video)
        .join(Follow, Follow.following_id == Video.creator_id)
        .where(
            and_(
                Follow.follower_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
        .order_by(Video.published_at.desc())
        .limit(per_page * 2)  # Get extra for mixing
    )
    result = await db.execute(followed_query)
    followed_videos = list(result.scalars().all())

    # Get trending videos (high quality score, recent)
    trending_query = (
        select(Video)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.published_at >= datetime.now(timezone.utc) - timedelta(days=7),
            )
        )
        .order_by(Video.quality_score.desc(), Video.view_count.desc())
        .limit(per_page * 2)
    )
    result = await db.execute(trending_query)
    trending_videos = list(result.scalars().all())

    # Mix videos: alternate between followed and trending
    mixed_videos = []
    followed_idx = 0
    trending_idx = 0
    seen_ids = set()

    while len(mixed_videos) < per_page:
        # Add followed video (40%)
        if followed_idx < len(followed_videos):
            video = followed_videos[followed_idx]
            followed_idx += 1
            if video.id not in seen_ids:
                mixed_videos.append(video)
                seen_ids.add(video.id)

        # Add trending video (60%)
        if trending_idx < len(trending_videos) and len(mixed_videos) < per_page:
            video = trending_videos[trending_idx]
            trending_idx += 1
            if video.id not in seen_ids:
                mixed_videos.append(video)
                seen_ids.add(video.id)

        # Break if no more videos
        if followed_idx >= len(followed_videos) and trending_idx >= len(
            trending_videos
        ):
            break

    # Apply pagination
    paginated = mixed_videos[offset : offset + per_page]

    # Build video summaries
    videos = []
    for video in paginated:
        summary = await _build_video_summary(video, db)
        videos.append(summary)

    return FeedResponse(
        videos=videos,
        page=page,
        per_page=per_page,
        has_more=len(mixed_videos) > offset + per_page,
    )


@router.get("/feed/trending", response_model=FeedResponse)
async def get_trending_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    period: str = Query("week", regex="^(day|week|month)$"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    """Get trending videos."""
    # Determine time range
    if period == "day":
        since = datetime.now(timezone.utc) - timedelta(days=1)
    elif period == "week":
        since = datetime.now(timezone.utc) - timedelta(days=7)
    else:  # month
        since = datetime.now(timezone.utc) - timedelta(days=30)

    offset = (page - 1) * per_page

    # Get trending videos by quality score
    query = (
        select(Video)
        .where(
            and_(
                Video.status == VideoStatus.PUBLISHED,
                Video.published_at >= since,
            )
        )
        .order_by(Video.quality_score.desc(), Video.view_count.desc())
        .offset(offset)
        .limit(per_page + 1)  # +1 to check has_more
    )
    result = await db.execute(query)
    videos_list = list(result.scalars().all())

    has_more = len(videos_list) > per_page
    videos_list = videos_list[:per_page]

    # Build video summaries
    videos = []
    for video in videos_list:
        summary = await _build_video_summary(video, db)
        videos.append(summary)

    return FeedResponse(
        videos=videos,
        page=page,
        per_page=per_page,
        has_more=has_more,
    )


@router.get("/feed/new", response_model=FeedResponse)
async def get_new_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    """Get newest videos."""
    offset = (page - 1) * per_page

    query = (
        select(Video)
        .where(Video.status == VideoStatus.PUBLISHED)
        .order_by(Video.published_at.desc())
        .offset(offset)
        .limit(per_page + 1)
    )
    result = await db.execute(query)
    videos_list = list(result.scalars().all())

    has_more = len(videos_list) > per_page
    videos_list = videos_list[:per_page]

    videos = []
    for video in videos_list:
        summary = await _build_video_summary(video, db)
        videos.append(summary)

    return FeedResponse(
        videos=videos,
        page=page,
        per_page=per_page,
        has_more=has_more,
    )


@router.get("/feed/following", response_model=FeedResponse)
async def get_following_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    """Get videos from followed creators only."""
    offset = (page - 1) * per_page

    query = (
        select(Video)
        .join(Follow, Follow.following_id == Video.creator_id)
        .where(
            and_(
                Follow.follower_id == current_user.id,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
        .order_by(Video.published_at.desc())
        .offset(offset)
        .limit(per_page + 1)
    )
    result = await db.execute(query)
    videos_list = list(result.scalars().all())

    has_more = len(videos_list) > per_page
    videos_list = videos_list[:per_page]

    videos = []
    for video in videos_list:
        summary = await _build_video_summary(video, db)
        videos.append(summary)

    return FeedResponse(
        videos=videos,
        page=page,
        per_page=per_page,
        has_more=has_more,
    )


# Share routes
@router.post("/videos/{video_id}/share", response_model=ShareResponse)
async def share_video(
    video_id: uuid.UUID,
    request: ShareRequest,
    http_request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Record a share event."""
    # Check if video exists
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Get IP hash for deduplication
    client_ip = http_request.client.host if http_request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()

    # Create share event
    share = Share(
        video_id=video_id,
        user_id=current_user.id if current_user else None,
        platform=request.platform,
        ip_hash=ip_hash,
    )
    db.add(share)

    # Update video share count
    video.share_count += 1

    await db.commit()
    await db.refresh(share)

    return ShareResponse.model_validate(share)


# Notification routes
@router.get("/me/notifications", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """Get current user's notifications."""
    # Count total and unread
    base_filter = Notification.user_id == current_user.id

    total_query = select(func.count()).where(base_filter)
    result = await db.execute(total_query)
    total = result.scalar() or 0

    unread_query = select(func.count()).where(
        and_(base_filter, Notification.is_read == False)
    )
    result = await db.execute(unread_query)
    unread_count = result.scalar() or 0

    # Get notifications
    offset = (page - 1) * per_page
    query = select(Notification).where(base_filter)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Build responses with actor info
    responses = []
    for notif in notifications:
        actor = None
        if notif.actor_id:
            result = await db.execute(select(User).where(User.id == notif.actor_id))
            actor_user = result.scalar_one_or_none()
            if actor_user:
                actor = UserSummary(
                    id=actor_user.id,
                    username=actor_user.username,
                    display_name=actor_user.display_name,
                    avatar_url=actor_user.avatar_url,
                    is_verified=actor_user.is_verified,
                    is_creator=actor_user.is_creator,
                )

        responses.append(
            NotificationResponse(
                id=notif.id,
                notification_type=notif.notification_type,
                title=notif.title,
                message=notif.message,
                is_read=notif.is_read,
                read_at=notif.read_at,
                created_at=notif.created_at,
                actor=actor,
                video_id=notif.video_id,
                comment_id=notif.comment_id,
            )
        )

    return NotificationListResponse(
        notifications=responses,
        total=total,
        unread_count=unread_count,
        page=page,
        per_page=per_page,
        has_more=(offset + len(responses)) < total,
    )


@router.post("/me/notifications/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    request: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark specific notifications as read."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id.in_(request.notification_ids),
                Notification.user_id == current_user.id,
            )
        )
    )
    notifications = result.scalars().all()

    for notif in notifications:
        notif.is_read = True
        notif.read_at = now

    await db.commit()


@router.post("/me/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all notifications as read."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
    )
    notifications = result.scalars().all()

    for notif in notifications:
        notif.is_read = True
        notif.read_at = now

    await db.commit()


@router.get("/me/notifications/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get count of unread notifications."""
    result = await db.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
    )
    count = result.scalar() or 0

    return {"unread_count": count}
