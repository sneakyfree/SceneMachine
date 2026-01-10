"""
Studio integration routes for SceneMachine Network.

These routes are used by the SceneMachine Studio desktop application
to publish content directly to the Network platform.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...shared.config import settings
from ...shared.database import get_db
from ...shared.models import (
    CreatorProfile,
    Follow,
    Transaction,
    TransactionStatus,
    User,
    UserSettings,
    Video,
    VideoStatus,
    TranscodingStatus,
)
from ...shared.storage import R2Storage
from ..auth.dependencies import get_current_user
from .schemas import (
    StudioPublishRequest,
    StudioPublishResponse,
    StudioUploadCompleteRequest,
    StudioVideoStatusResponse,
    StudioMyVideosResponse,
    StudioVideoSummary,
    StudioAnalyticsSummary,
    StudioAccountStatus,
)

router = APIRouter(prefix="/studio", tags=["studio"])


def _require_studio_linked(user: User, user_settings: Optional[UserSettings]) -> None:
    """Verify user has Studio linked."""
    if not user_settings or not user_settings.studio_linked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Studio license not linked. Please link your Studio license first.",
        )


@router.get("/account", response_model=StudioAccountStatus)
async def get_account_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudioAccountStatus:
    """Get account status for Studio integration."""
    # Get user settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = result.scalar_one_or_none()

    # Get creator profile
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    # Get available balance
    available_for_payout = Decimal("0")
    if profile and profile.stripe_account_id:
        # Would get from Stripe balance
        available_for_payout = Decimal("0")

    return StudioAccountStatus(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_creator=current_user.is_creator,
        is_verified=current_user.is_verified,
        studio_linked=user_settings.studio_linked if user_settings else False,
        studio_license_key=user_settings.studio_license_key if user_settings else None,
        studio_linked_at=None,  # Would track in user_settings
        monetization_enabled=profile.monetization_enabled if profile else False,
        stripe_connected=bool(profile and profile.stripe_account_id),
        current_tier=profile.current_tier if profile else 1,
        total_earnings=profile.total_earnings if profile else Decimal("0"),
        available_for_payout=available_for_payout,
    )


@router.post("/publish", response_model=StudioPublishResponse)
async def publish_from_studio(
    request: StudioPublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudioPublishResponse:
    """
    Initiate a publish from SceneMachine Studio.

    Creates the video record and returns presigned URLs for uploading.
    """
    # Get and verify user settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = result.scalar_one_or_none()
    _require_studio_linked(current_user, user_settings)

    # Check if project was already published
    result = await db.execute(
        select(Video).where(
            and_(
                Video.creator_id == current_user.id,
                Video.studio_project_id == request.project_id,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.status != VideoStatus.REMOVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project already published as video {existing.id}",
        )

    # Create video record
    video = Video(
        creator_id=current_user.id,
        title=request.title,
        description=request.description,
        content_type=request.content_type,
        monetization_type=request.monetization_type,
        ticket_price=request.ticket_price,
        tags=request.tags,
        is_age_restricted=request.is_age_restricted,
        made_with_studio=True,
        studio_project_id=request.project_id,
        duration_seconds=request.duration_seconds,
        status=VideoStatus.UPLOADING,
        transcoding_status=TranscodingStatus.PENDING,
    )
    db.add(video)
    await db.flush()

    # Generate upload URLs
    storage = R2Storage()
    expires_in = 3600  # 1 hour

    # Main video upload URL
    video_key = f"videos/{current_user.id}/{video.id}/source.mp4"
    video.source_file_key = video_key

    upload_url = await storage.get_presigned_upload_url(
        key=video_key,
        content_type="video/mp4",
        expires_in=expires_in,
    )

    # Thumbnail upload URL if needed
    thumbnail_upload_url = None
    if request.has_thumbnail:
        thumbnail_key = f"videos/{current_user.id}/{video.id}/thumbnail.jpg"
        thumbnail_upload_url = await storage.get_presigned_upload_url(
            key=thumbnail_key,
            content_type="image/jpeg",
            expires_in=expires_in,
        )
        video.thumbnail_url = f"{settings.cdn_base_url}/{thumbnail_key}"

    await db.commit()

    return StudioPublishResponse(
        video_id=video.id,
        upload_url=upload_url,
        thumbnail_upload_url=thumbnail_upload_url,
        upload_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        status="awaiting_upload",
    )


@router.post("/publish/complete")
async def complete_studio_upload(
    request: StudioUploadCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Complete the upload and start transcoding.
    """
    result = await db.execute(
        select(Video).where(
            and_(
                Video.id == request.video_id,
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

    if video.status != VideoStatus.UPLOADING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not in uploading state",
        )

    if not request.upload_successful:
        video.status = VideoStatus.REMOVED
        await db.commit()
        return {"status": "upload_failed"}

    # Verify file exists
    storage = R2Storage()
    exists = await storage.object_exists(video.source_file_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload file not found in storage",
        )

    # Update status and queue transcoding
    video.status = VideoStatus.PROCESSING
    video.transcoding_status = TranscodingStatus.IN_PROGRESS

    await db.commit()

    # Queue the actual transcoding task
    try:
        from ..content.tasks.transcoding import process_video_upload_task

        process_video_upload_task.delay(
            video_id=str(video.id),
            source_key=video.source_file_key,
            creator_id=str(current_user.id),
        )
    except Exception as e:
        # If task queue unavailable, log warning but don't fail the request
        import logging
        logging.getLogger(__name__).warning(
            f"Could not queue transcoding task for video {video.id}: {e}"
        )

    return {
        "status": "processing",
        "video_id": str(video.id),
        "message": "Upload complete. Transcoding started.",
    }


@router.get("/videos/{video_id}/status", response_model=StudioVideoStatusResponse)
async def get_video_status(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudioVideoStatusResponse:
    """Get the status of a video uploaded from Studio."""
    result = await db.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
            )
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Generate video URL if published
    video_url = None
    if video.status == VideoStatus.PUBLISHED:
        video_url = f"{settings.network_base_url}/watch/{video.id}"

    return StudioVideoStatusResponse(
        video_id=video.id,
        status=video.status,
        transcoding_progress=video.transcoding_progress,
        transcoding_status=video.transcoding_status.value,
        is_published=video.status == VideoStatus.PUBLISHED,
        published_at=video.published_at,
        video_url=video_url,
        thumbnail_url=video.thumbnail_url,
        view_count=video.view_count,
        like_count=video.like_count,
    )


@router.get("/videos", response_model=StudioMyVideosResponse)
async def get_studio_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudioMyVideosResponse:
    """Get all videos created from Studio."""
    # Count total
    result = await db.execute(
        select(func.count()).where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
                Video.status != VideoStatus.REMOVED,
            )
        )
    )
    total = result.scalar() or 0

    # Get videos
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Video)
        .where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
                Video.status != VideoStatus.REMOVED,
            )
        )
        .order_by(Video.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    videos = result.scalars().all()

    # Build summaries with revenue
    summaries = []
    for video in videos:
        # Get revenue for video
        result = await db.execute(
            select(func.sum(Transaction.amount_net)).where(
                and_(
                    Transaction.video_id == video.id,
                    Transaction.status == TransactionStatus.COMPLETED,
                )
            )
        )
        revenue = result.scalar() or Decimal("0")

        summaries.append(
            StudioVideoSummary(
                video_id=video.id,
                project_id=video.studio_project_id or "",
                title=video.title,
                status=video.status,
                is_published=video.status == VideoStatus.PUBLISHED,
                published_at=video.published_at,
                view_count=video.view_count,
                like_count=video.like_count,
                revenue=revenue,
                thumbnail_url=video.thumbnail_url,
                created_at=video.created_at,
            )
        )

    return StudioMyVideosResponse(
        videos=summaries,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/analytics", response_model=StudioAnalyticsSummary)
async def get_studio_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudioAnalyticsSummary:
    """Get analytics summary for Studio user."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # Total videos
    result = await db.execute(
        select(func.count()).where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
    )
    total_videos = result.scalar() or 0

    # Total views and watch hours
    result = await db.execute(
        select(func.sum(Video.view_count)).where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
            )
        )
    )
    total_views = result.scalar() or 0

    # Total revenue
    result = await db.execute(
        select(func.sum(Transaction.amount_net))
        .join(Video, Video.id == Transaction.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
    )
    total_revenue = result.scalar() or Decimal("0")

    # Total subscribers
    result = await db.execute(
        select(func.count()).where(Follow.following_id == current_user.id)
    )
    total_subscribers = result.scalar() or 0

    # 7-day metrics (simplified)
    result = await db.execute(
        select(func.sum(Transaction.amount_net))
        .join(Video, Video.id == Transaction.video_id)
        .where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= seven_days_ago,
            )
        )
    )
    revenue_7d = result.scalar() or Decimal("0")

    result = await db.execute(
        select(func.count()).where(
            and_(
                Follow.following_id == current_user.id,
                Follow.created_at >= seven_days_ago,
            )
        )
    )
    new_subscribers_7d = result.scalar() or 0

    # Top performing video
    result = await db.execute(
        select(Video)
        .where(
            and_(
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
                Video.status == VideoStatus.PUBLISHED,
            )
        )
        .order_by(Video.view_count.desc())
        .limit(1)
    )
    top_video = result.scalar_one_or_none()

    return StudioAnalyticsSummary(
        total_videos=total_videos,
        total_views=total_views,
        total_watch_hours=0,  # Would need watch time tracking
        total_revenue=total_revenue,
        total_subscribers=total_subscribers,
        views_7d=0,  # Would need view event tracking
        revenue_7d=revenue_7d,
        new_subscribers_7d=new_subscribers_7d,
        top_video_title=top_video.title if top_video else None,
        top_video_views=top_video.view_count if top_video else 0,
    )


@router.post("/videos/{video_id}/publish")
async def publish_studio_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Publish a ready video from Studio."""
    result = await db.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
            )
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.transcoding_status != TranscodingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video transcoding not complete",
        )

    if video.status == VideoStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video already published",
        )

    video.status = VideoStatus.PUBLISHED
    video.published_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "status": "published",
        "video_id": str(video.id),
        "video_url": f"{settings.network_base_url}/watch/{video.id}",
    }


@router.delete("/videos/{video_id}")
async def delete_studio_video(
    video_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a video uploaded from Studio."""
    result = await db.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
                Video.made_with_studio == True,
            )
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    video.status = VideoStatus.REMOVED

    await db.commit()

    return {"status": "deleted", "video_id": str(video_id)}
