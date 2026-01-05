"""
Streaming routes for SceneMachine Network.

Handles video playback, progress tracking, and view counting.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.config import get_settings
from ....shared.database import get_session
from ....shared.models import (
    Video,
    VideoStatus,
    WatchHistory,
    WatchSession,
    ViewEvent,
    VIEW_DEDUP_WINDOW_HOURS,
    VIEW_MINIMUM_WATCH_PERCENT,
    VIEW_MINIMUM_WATCH_SECONDS,
)
from ....shared.storage import get_storage
from ...auth.dependencies import CurrentUser, OptionalUser
from ..schemas import (
    EndSessionRequest,
    EndSessionResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    ManifestResponse,
    QualityInfo,
    StartSessionRequest,
    StartSessionResponse,
    StreamingStatsResponse,
    WatchHistoryResponse,
    WatchProgressResponse,
)

router = APIRouter(prefix="/stream", tags=["streaming"])


def generate_session_token() -> str:
    """Generate a unique session token."""
    return secrets.token_urlsafe(48)


def hash_ip(ip: str) -> str:
    """Hash an IP address for deduplication."""
    return hashlib.sha256(ip.encode()).hexdigest()


def parse_user_agent(user_agent: str) -> dict:
    """Parse user agent string for device info."""
    ua_lower = user_agent.lower()

    # Device type
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device_type = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_type = "tablet"
    elif "tv" in ua_lower or "smart-tv" in ua_lower:
        device_type = "tv"
    else:
        device_type = "desktop"

    # Browser
    if "chrome" in ua_lower:
        browser = "chrome"
    elif "firefox" in ua_lower:
        browser = "firefox"
    elif "safari" in ua_lower:
        browser = "safari"
    elif "edge" in ua_lower:
        browser = "edge"
    else:
        browser = "other"

    # OS
    if "windows" in ua_lower:
        os = "windows"
    elif "mac" in ua_lower:
        os = "macos"
    elif "linux" in ua_lower:
        os = "linux"
    elif "android" in ua_lower:
        os = "android"
    elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
        os = "ios"
    else:
        os = "other"

    return {"device_type": device_type, "browser": browser, "os": os}


@router.get("/{video_id}/manifest", response_model=ManifestResponse)
async def get_manifest(
    video_id: uuid.UUID,
    current_user: OptionalUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    format: str = Query("hls", enum=["hls", "dash"]),
) -> ManifestResponse:
    """
    Get the streaming manifest URL for a video.

    Returns a signed URL to the HLS or DASH manifest.
    """
    # Get video
    result = await session.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Check access
    is_owner = current_user is not None and video.creator_id == current_user.id
    if not is_owner:
        if video.status not in (VideoStatus.PUBLISHED, VideoStatus.UNLISTED):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Video is not available for streaming",
            )

    # Check monetization
    if video.monetization_type.value == "paid":
        # TODO: Check if user has purchased access
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for paid content",
            )

    # Get transcoded versions
    versions = video.transcoded_versions or {}
    available_qualities = list(versions.keys())

    if not available_qualities:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video is still being processed",
        )

    # Generate manifest URL
    storage = get_storage()
    manifest_key = f"videos/{video.creator_id}/{video_id}/hls/master.m3u8"

    if format == "dash":
        manifest_key = f"videos/{video.creator_id}/{video_id}/dash/manifest.mpd"

    manifest_url = await storage.get_signed_url(manifest_key, expires_in=7200)

    return ManifestResponse(
        video_id=video_id,
        manifest_url=manifest_url,
        format=format,
        available_qualities=available_qualities,
        duration_seconds=video.duration_seconds,
        thumbnail_url=video.thumbnail_url,
    )


@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
    req: Request,
    current_user: OptionalUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StartSessionResponse:
    """
    Start a new watch session.

    Returns a session token for tracking playback.
    """
    # Get video
    result = await session.execute(select(Video).where(Video.id == request.video_id))
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Parse user agent
    user_agent = req.headers.get("user-agent", "")
    device_info = parse_user_agent(user_agent)

    # Get client IP
    client_ip = req.client.host if req.client else None

    # Check for existing progress
    resume_position = 0
    if current_user:
        result = await session.execute(
            select(WatchHistory).where(
                and_(
                    WatchHistory.user_id == current_user.id,
                    WatchHistory.video_id == request.video_id,
                )
            )
        )
        history = result.scalar_one_or_none()
        if history and not history.completed:
            resume_position = history.progress_seconds

    # Create session
    session_token = generate_session_token()
    watch_session = WatchSession(
        user_id=current_user.id if current_user else None,
        video_id=request.video_id,
        session_token=session_token,
        ip_address=client_ip,
        user_agent=user_agent[:500] if user_agent else None,
        device_type=device_info["device_type"],
        browser=device_info["browser"],
        os=device_info["os"],
        quality_level=request.quality_level,
        referrer=request.referrer[:500] if request.referrer else None,
        traffic_source=request.traffic_source,
        is_active=True,
    )
    session.add(watch_session)
    await session.flush()

    return StartSessionResponse(
        session_token=session_token,
        session_id=watch_session.id,
        video_id=request.video_id,
        resume_position=resume_position,
    )


@router.post("/session/heartbeat", response_model=HeartbeatResponse)
async def session_heartbeat(
    request: HeartbeatRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HeartbeatResponse:
    """
    Send a playback heartbeat to update watch progress.

    Should be called every 10-30 seconds during playback.
    """
    # Get session
    result = await session.execute(
        select(WatchSession).where(WatchSession.session_token == request.session_token)
    )
    watch_session = result.scalar_one_or_none()

    if watch_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if not watch_session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has ended",
        )

    # Calculate watch time since last heartbeat
    now = datetime.now(timezone.utc)
    time_since_last = (now - watch_session.last_heartbeat_at).total_seconds()

    # Cap at 60 seconds to prevent abuse
    time_increment = min(int(time_since_last), 60)

    # Update session
    watch_session.current_position_seconds = request.position_seconds
    watch_session.last_heartbeat_at = now
    watch_session.watch_time_seconds += time_increment

    if request.quality_level:
        watch_session.quality_level = request.quality_level

    await session.flush()

    # Update watch history if user is logged in
    if watch_session.user_id:
        result = await session.execute(
            select(WatchHistory).where(
                and_(
                    WatchHistory.user_id == watch_session.user_id,
                    WatchHistory.video_id == watch_session.video_id,
                )
            )
        )
        history = result.scalar_one_or_none()

        # Get video duration
        result = await session.execute(
            select(Video.duration_seconds).where(Video.id == watch_session.video_id)
        )
        duration = result.scalar() or 0

        if history:
            # Update existing
            history.progress_seconds = request.position_seconds
            history.last_watched_at = now
            if duration > 0:
                history.watch_percent = (request.position_seconds / duration) * 100
                history.completed = history.watch_percent >= 90
        else:
            # Create new
            watch_percent = (request.position_seconds / duration * 100) if duration > 0 else 0
            history = WatchHistory(
                user_id=watch_session.user_id,
                video_id=watch_session.video_id,
                progress_seconds=request.position_seconds,
                duration_seconds=duration,
                watch_percent=watch_percent,
                completed=watch_percent >= 90,
            )
            session.add(history)

        await session.flush()

    return HeartbeatResponse(
        success=True,
        session_id=watch_session.id,
        watch_time_seconds=watch_session.watch_time_seconds,
    )


@router.post("/session/end", response_model=EndSessionResponse)
async def end_session(
    request: EndSessionRequest,
    req: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EndSessionResponse:
    """
    End a watch session and record the view.
    """
    # Get session
    result = await session.execute(
        select(WatchSession).where(WatchSession.session_token == request.session_token)
    )
    watch_session = result.scalar_one_or_none()

    if watch_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    now = datetime.now(timezone.utc)

    # Update session
    watch_session.is_active = False
    watch_session.ended_at = now
    watch_session.current_position_seconds = request.final_position_seconds

    # Get video for duration
    result = await session.execute(
        select(Video).where(Video.id == watch_session.video_id)
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Calculate watch percentage
    watch_percent = 0.0
    if video.duration_seconds > 0:
        watch_percent = (watch_session.watch_time_seconds / video.duration_seconds) * 100

    # Determine if this is a valid view
    is_valid_view = (
        watch_session.watch_time_seconds >= VIEW_MINIMUM_WATCH_SECONDS
        or watch_percent >= VIEW_MINIMUM_WATCH_PERCENT
    )

    # Check for duplicate views
    view_counted = False
    if is_valid_view:
        ip_hash = hash_ip(watch_session.ip_address or "unknown")
        dedup_window = now - timedelta(hours=VIEW_DEDUP_WINDOW_HOURS)

        # Check for recent view from same IP
        result = await session.execute(
            select(ViewEvent).where(
                and_(
                    ViewEvent.video_id == watch_session.video_id,
                    ViewEvent.ip_hash == ip_hash,
                    ViewEvent.viewed_at > dedup_window,
                    ViewEvent.is_valid_view == True,
                )
            )
        )
        existing_view = result.scalar_one_or_none()

        if existing_view is None:
            # Create view event
            view_event = ViewEvent(
                video_id=watch_session.video_id,
                user_id=watch_session.user_id,
                session_id=watch_session.id,
                ip_hash=ip_hash,
                watch_time_seconds=watch_session.watch_time_seconds,
                watch_percent=watch_percent,
                completed=request.completed,
                average_quality=watch_session.quality_level,
                device_type=watch_session.device_type,
                is_valid_view=True,
            )
            session.add(view_event)

            # Increment video view count
            video.view_count += 1
            view_counted = True

    # Update watch history
    if watch_session.user_id:
        result = await session.execute(
            select(WatchHistory).where(
                and_(
                    WatchHistory.user_id == watch_session.user_id,
                    WatchHistory.video_id == watch_session.video_id,
                )
            )
        )
        history = result.scalar_one_or_none()

        if history:
            history.progress_seconds = request.final_position_seconds
            history.watch_percent = watch_percent
            history.completed = request.completed or watch_percent >= 90
            history.last_watched_at = now
            history.watch_count += 1

    await session.flush()

    return EndSessionResponse(
        success=True,
        total_watch_time_seconds=watch_session.watch_time_seconds,
        view_counted=view_counted,
    )


@router.get("/history", response_model=WatchHistoryResponse)
async def get_watch_history(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> WatchHistoryResponse:
    """
    Get the current user's watch history.
    """
    # Count total
    count_query = select(func.count()).select_from(
        select(WatchHistory).where(WatchHistory.user_id == current_user.id).subquery()
    )
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Get history
    query = (
        select(WatchHistory)
        .where(WatchHistory.user_id == current_user.id)
        .order_by(WatchHistory.last_watched_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(query)
    history_items = result.scalars().all()

    return WatchHistoryResponse(
        items=[
            WatchProgressResponse(
                video_id=h.video_id,
                progress_seconds=h.progress_seconds,
                duration_seconds=h.duration_seconds,
                watch_percent=h.watch_percent,
                completed=h.completed,
                last_watched_at=h.last_watched_at,
            )
            for h in history_items
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.delete("/history/{video_id}")
async def remove_from_history(
    video_id: uuid.UUID,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """
    Remove a video from watch history.
    """
    result = await session.execute(
        select(WatchHistory).where(
            and_(
                WatchHistory.user_id == current_user.id,
                WatchHistory.video_id == video_id,
            )
        )
    )
    history = result.scalar_one_or_none()

    if history:
        await session.delete(history)
        await session.flush()

    return {"message": "Removed from history"}


@router.get("/{video_id}/stats", response_model=StreamingStatsResponse)
async def get_streaming_stats(
    video_id: uuid.UUID,
    current_user: OptionalUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StreamingStatsResponse:
    """
    Get real-time streaming statistics for a video.
    """
    # Get video
    result = await session.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Check access (only creator can see detailed stats)
    is_owner = current_user is not None and video.creator_id == current_user.id

    # Count concurrent viewers (active sessions in last 2 minutes)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    result = await session.execute(
        select(func.count())
        .select_from(WatchSession)
        .where(
            and_(
                WatchSession.video_id == video_id,
                WatchSession.is_active == True,
                WatchSession.last_heartbeat_at > recent_cutoff,
            )
        )
    )
    concurrent_viewers = result.scalar() or 0

    # Count views today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count())
        .select_from(ViewEvent)
        .where(
            and_(
                ViewEvent.video_id == video_id,
                ViewEvent.is_valid_view == True,
                ViewEvent.viewed_at >= today_start,
            )
        )
    )
    views_today = result.scalar() or 0

    # Average watch time (from recent sessions)
    result = await session.execute(
        select(func.avg(WatchSession.watch_time_seconds))
        .where(
            and_(
                WatchSession.video_id == video_id,
                WatchSession.watch_time_seconds > 0,
            )
        )
    )
    avg_watch_time = int(result.scalar() or 0)

    return StreamingStatsResponse(
        video_id=video_id,
        concurrent_viewers=concurrent_viewers,
        total_views_today=views_today,
        average_watch_time_seconds=avg_watch_time,
        average_quality=None,  # Could calculate from sessions
    )
