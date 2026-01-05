"""
Video routes for SceneMachine Network.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.config import get_settings
from ....shared.database import get_session
from ....shared.models import (
    Video,
    VideoStatus,
    TranscodingStatus,
    ContentType,
    CreatorProfile,
)
from ....shared.storage import get_storage, generate_video_key
from ...auth.dependencies import CurrentUser, CurrentCreator, OptionalUser
from ..schemas import (
    VideoCreateRequest,
    VideoUpdateRequest,
    VideoResponse,
    VideoListResponse,
    UploadInitResponse,
    UploadCompleteRequest,
    TranscodingStatusResponse,
    PublishRequest,
    StudioUploadRequest,
)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    request: VideoCreateRequest,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoResponse:
    """
    Create a new video entry.

    The video starts in UPLOADING status. Use the upload endpoint to upload the file.
    """
    video = Video(
        creator_id=current_user.id,
        title=request.title,
        description=request.description,
        content_type=request.content_type,
        monetization_type=request.monetization_type,
        ticket_price=request.ticket_price,
        series_id=request.series_id,
        episode_number=request.episode_number,
        tags=request.tags,
        is_age_restricted=request.is_age_restricted,
        status=VideoStatus.UPLOADING,
        transcoding_status=TranscodingStatus.PENDING,
    )
    session.add(video)
    await session.flush()

    return VideoResponse.model_validate(video)


@router.post("/upload/init", response_model=UploadInitResponse)
async def init_upload(
    video_id: uuid.UUID,
    content_type: str,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UploadInitResponse:
    """
    Initialize a video upload and get a presigned URL.

    Returns a presigned URL for direct upload to R2 storage.
    """
    # Get the video
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.status != VideoStatus.UPLOADING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not in uploading state",
        )

    # Generate storage key
    ext = ".mp4"  # Default extension
    if "webm" in content_type:
        ext = ".webm"
    elif "quicktime" in content_type or "mov" in content_type:
        ext = ".mov"

    key = generate_video_key(
        str(current_user.id),
        str(video_id),
        f"source{ext}",
    )

    # Get presigned upload URL
    storage = get_storage()
    upload_url = await storage.get_upload_url(
        key=key,
        content_type=content_type,
        expires_in=3600,  # 1 hour
    )

    # Update video with source key
    video.source_file_key = key

    return UploadInitResponse(
        video_id=video_id,
        upload_url=upload_url,
        upload_key=key,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@router.post("/upload/complete")
async def complete_upload(
    request: UploadCompleteRequest,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """
    Mark an upload as complete and trigger transcoding.
    """
    # Get the video
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == request.video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.status != VideoStatus.UPLOADING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not in uploading state",
        )

    # Verify file exists in storage
    storage = get_storage()
    if video.source_file_key:
        exists = await storage.object_exists(video.source_file_key)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload file not found",
            )

    # Update video status
    video.status = VideoStatus.PROCESSING
    video.transcoding_status = TranscodingStatus.PENDING
    video.file_size_bytes = request.file_size

    # TODO: Queue transcoding task
    # In production, this would add a job to Celery or similar
    # For now, we just mark it as ready
    video.transcoding_status = TranscodingStatus.IN_PROGRESS

    await session.flush()

    return {
        "video_id": str(video.id),
        "status": video.status.value,
        "message": "Upload complete. Transcoding started.",
    }


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: uuid.UUID,
    current_user: OptionalUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoResponse:
    """
    Get a video by ID.

    Public videos are accessible to anyone.
    Private/unlisted videos require the creator.
    """
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
        if video.status == VideoStatus.PRIVATE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This video is private",
            )
        if video.status == VideoStatus.REMOVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

    return VideoResponse.model_validate(video)


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: uuid.UUID,
    request: VideoUpdateRequest,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoResponse:
    """
    Update a video's metadata.
    """
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Update fields
    if request.title is not None:
        video.title = request.title
    if request.description is not None:
        video.description = request.description
    if request.monetization_type is not None:
        video.monetization_type = request.monetization_type
    if request.ticket_price is not None:
        video.ticket_price = request.ticket_price
    if request.tags is not None:
        video.tags = request.tags
    if request.is_age_restricted is not None:
        video.is_age_restricted = request.is_age_restricted
    if request.scheduled_publish_at is not None:
        video.scheduled_publish_at = request.scheduled_publish_at

    await session.flush()

    return VideoResponse.model_validate(video)


@router.delete("/{video_id}")
async def delete_video(
    video_id: uuid.UUID,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """
    Delete a video.

    This marks the video as REMOVED. Files are cleaned up by a background job.
    """
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    video.status = VideoStatus.REMOVED

    # Update creator video count
    result = await session.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile and profile.video_count > 0:
        profile.video_count -= 1

    await session.flush()

    return {"message": "Video deleted successfully"}


@router.post("/{video_id}/publish", response_model=VideoResponse)
async def publish_video(
    video_id: uuid.UUID,
    request: PublishRequest,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoResponse:
    """
    Publish a video (make it publicly visible).

    Can optionally schedule for future publication.
    """
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    # Check if ready to publish
    if video.transcoding_status != TranscodingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video transcoding is not complete",
        )

    if video.status == VideoStatus.REMOVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a removed video",
        )

    if request.scheduled_at:
        # Schedule for later
        video.scheduled_publish_at = request.scheduled_at
        video.status = VideoStatus.READY
    else:
        # Publish now
        video.status = VideoStatus.PUBLISHED
        video.published_at = datetime.now(timezone.utc)

        # Update creator video count
        result = await session.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.video_count += 1

    await session.flush()

    return VideoResponse.model_validate(video)


@router.post("/{video_id}/unpublish", response_model=VideoResponse)
async def unpublish_video(
    video_id: uuid.UUID,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoResponse:
    """
    Unpublish a video (make it private).
    """
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.status == VideoStatus.PUBLISHED:
        # Update creator video count
        result = await session.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        if profile and profile.video_count > 0:
            profile.video_count -= 1

    video.status = VideoStatus.PRIVATE
    video.scheduled_publish_at = None

    await session.flush()

    return VideoResponse.model_validate(video)


@router.get("/{video_id}/status", response_model=TranscodingStatusResponse)
async def get_transcoding_status(
    video_id: uuid.UUID,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TranscodingStatusResponse:
    """
    Get the transcoding status of a video.
    """
    result = await session.execute(
        select(Video).where(
            and_(
                Video.id == video_id,
                Video.creator_id == current_user.id,
            )
        )
    )
    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    return TranscodingStatusResponse(
        video_id=video.id,
        status=video.transcoding_status,
        progress=video.transcoding_progress,
        error=video.transcoding_error,
        variants=video.transcoded_versions,
    )


@router.get("/", response_model=VideoListResponse)
async def list_videos(
    current_user: OptionalUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    creator_id: Optional[uuid.UUID] = None,
    content_type: Optional[ContentType] = None,
    status_filter: Optional[VideoStatus] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> VideoListResponse:
    """
    List videos with optional filters.

    By default, only shows published videos.
    Creators can see their own videos in any status.
    """
    query = select(Video)

    # Filter by creator
    if creator_id:
        query = query.where(Video.creator_id == creator_id)

    # Filter by content type
    if content_type:
        query = query.where(Video.content_type == content_type)

    # Status filtering
    if current_user and creator_id == current_user.id:
        # Creator viewing their own videos
        if status_filter:
            query = query.where(Video.status == status_filter)
        else:
            query = query.where(Video.status != VideoStatus.REMOVED)
    else:
        # Public view - only published videos
        query = query.where(Video.status == VideoStatus.PUBLISHED)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(Video.published_at.desc().nullsfirst())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    videos = result.scalars().all()

    return VideoListResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


@router.post("/from-studio", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_from_studio(
    request: StudioUploadRequest,
    current_user: CurrentCreator,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoResponse:
    """
    Create a video entry for upload from SceneMachine Studio.

    Requires a linked Studio license.
    """
    # Check if Studio is linked
    if not current_user.settings or not current_user.settings.studio_linked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Studio license not linked",
        )

    video = Video(
        creator_id=current_user.id,
        title=request.title,
        description=request.description,
        content_type=request.content_type,
        monetization_type=request.monetization_type,
        ticket_price=request.ticket_price,
        tags=request.tags,
        made_with_studio=True,
        studio_project_id=request.project_id,
        status=VideoStatus.UPLOADING,
        transcoding_status=TranscodingStatus.PENDING,
    )
    session.add(video)
    await session.flush()

    return VideoResponse.model_validate(video)
