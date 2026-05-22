"""
Timeline API Routes

REST endpoints for timeline tracks and clips.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.dependencies import CurrentActiveUser
from scenemachine.database import get_session
from scenemachine.models.track import TrackType
from scenemachine.services.timeline_service import (
    ClipNotFoundError,
    TimelineService,
    TimelineServiceError,
    TrackNotFoundError,
)

router = APIRouter(prefix="/timeline", tags=["timeline"])


# ==================== Schemas ====================


class TrackResponse(BaseModel):
    """Track response model."""

    id: UUID
    project_id: UUID
    name: str
    track_type: str
    order: int
    color: str | None = None
    is_visible: bool
    is_locked: bool
    is_solo: bool
    is_muted: bool
    volume: float
    pan: float
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ClipResponse(BaseModel):
    """Clip response model."""

    id: UUID
    track_id: UUID
    source_id: UUID
    source_type: str
    start_time: float
    duration: float
    trim_start: float
    trim_end: float
    z_index: int
    name: str | None = None
    volume: float
    fade_in: float
    fade_out: float
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TrackWithClipsResponse(TrackResponse):
    """Track with clips included."""

    clips: list[ClipResponse] = []


class CreateTrackRequest(BaseModel):
    """Request to create a track."""

    name: str = Field(..., min_length=1, max_length=100)
    track_type: TrackType
    order: int | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class UpdateTrackRequest(BaseModel):
    """Request to update a track."""

    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_visible: bool | None = None
    is_locked: bool | None = None
    is_muted: bool | None = None
    is_solo: bool | None = None
    volume: float | None = Field(None, ge=0.0, le=1.0)
    pan: float | None = Field(None, ge=-1.0, le=1.0)


class ReorderTracksRequest(BaseModel):
    """Request to reorder tracks."""

    track_ids: list[UUID]


class CreateClipRequest(BaseModel):
    """Request to create a clip."""

    source_id: UUID
    source_type: str = Field(..., min_length=1, max_length=50)
    start_time: float = Field(..., ge=0.0)
    duration: float = Field(..., gt=0.0)
    name: str | None = None
    z_index: int = 0


class UpdateClipRequest(BaseModel):
    """Request to update a clip."""

    start_time: float | None = Field(None, ge=0.0)
    duration: float | None = Field(None, gt=0.0)
    trim_start: float | None = Field(None, ge=0.0)
    trim_end: float | None = Field(None, ge=0.0)
    z_index: int | None = None
    volume: float | None = Field(None, ge=0.0, le=1.0)
    fade_in: float | None = Field(None, ge=0.0)
    fade_out: float | None = Field(None, ge=0.0)


class TrimClipRequest(BaseModel):
    """Request to trim a clip."""

    trim_start: float = Field(..., ge=0.0)
    trim_end: float = Field(..., ge=0.0)


class SplitClipRequest(BaseModel):
    """Request to split a clip."""

    split_time: float = Field(..., gt=0.0)


class SplitClipResponse(BaseModel):
    """Response for split clip."""

    first_clip: ClipResponse
    second_clip: ClipResponse


class MoveClipRequest(BaseModel):
    """Request to move clip to another track."""

    target_track_id: UUID
    start_time: float | None = None


# ==================== Dependencies ====================


def get_timeline_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TimelineService:
    """Get timeline service instance."""
    return TimelineService(session)


# ==================== Track Routes ====================


@router.get(
    "/projects/{project_id}/tracks",
    response_model=list[TrackWithClipsResponse],
    summary="Get all tracks for a project",
)
async def get_tracks(
    project_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> list[TrackWithClipsResponse]:
    """Get all tracks with their clips, ordered by position."""
    tracks = await service.get_tracks(project_id)
    return [
        TrackWithClipsResponse(
            **TrackResponse.model_validate(t).model_dump(),
            clips=[ClipResponse.model_validate(c) for c in t.clips],
        )
        for t in tracks
    ]


@router.post(
    "/projects/{project_id}/tracks",
    response_model=TrackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new track",
)
async def create_track(
    project_id: UUID,
    data: CreateTrackRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TrackResponse:
    """Create a new track in the project timeline."""
    track = await service.create_track(
        project_id=project_id,
        name=data.name,
        track_type=data.track_type,
        order=data.order,
        color=data.color,
    )
    return TrackResponse.model_validate(track)


@router.patch(
    "/tracks/{track_id}",
    response_model=TrackResponse,
    summary="Update a track",
)
async def update_track(
    track_id: UUID,
    data: UpdateTrackRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> TrackResponse:
    """Update track properties."""
    try:
        track = await service.update_track(
            track_id=track_id,
            name=data.name,
            color=data.color,
            is_visible=data.is_visible,
            is_locked=data.is_locked,
            is_muted=data.is_muted,
            is_solo=data.is_solo,
            volume=data.volume,
            pan=data.pan,
        )
        return TrackResponse.model_validate(track)
    except TrackNotFoundError:
        raise HTTPException(status_code=404, detail="Track not found")


@router.delete(
    "/tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a track",
)
async def delete_track(
    track_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> None:
    """Delete a track and all its clips."""
    try:
        await service.delete_track(track_id)
    except TrackNotFoundError:
        raise HTTPException(status_code=404, detail="Track not found")


@router.put(
    "/projects/{project_id}/tracks/reorder",
    response_model=list[TrackResponse],
    summary="Reorder tracks",
)
async def reorder_tracks(
    project_id: UUID,
    data: ReorderTracksRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> list[TrackResponse]:
    """Reorder tracks by providing new order."""
    tracks = await service.reorder_tracks(project_id, data.track_ids)
    return [TrackResponse.model_validate(t) for t in tracks]


# ==================== Clip Routes ====================


@router.post(
    "/tracks/{track_id}/clips",
    response_model=ClipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a clip",
)
async def create_clip(
    track_id: UUID,
    data: CreateClipRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> ClipResponse:
    """Create a new clip on a track."""
    clip = await service.create_clip(
        track_id=track_id,
        source_id=data.source_id,
        source_type=data.source_type,
        start_time=data.start_time,
        duration=data.duration,
        name=data.name,
        z_index=data.z_index,
    )
    return ClipResponse.model_validate(clip)


@router.get(
    "/clips/{clip_id}",
    response_model=ClipResponse,
    summary="Get a clip",
)
async def get_clip(
    clip_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> ClipResponse:
    """Get clip by ID."""
    clip = await service.get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return ClipResponse.model_validate(clip)


@router.patch(
    "/clips/{clip_id}",
    response_model=ClipResponse,
    summary="Update a clip",
)
async def update_clip(
    clip_id: UUID,
    data: UpdateClipRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> ClipResponse:
    """Update clip properties."""
    try:
        clip = await service.update_clip(
            clip_id=clip_id,
            start_time=data.start_time,
            duration=data.duration,
            trim_start=data.trim_start,
            trim_end=data.trim_end,
            z_index=data.z_index,
            volume=data.volume,
            fade_in=data.fade_in,
            fade_out=data.fade_out,
        )
        return ClipResponse.model_validate(clip)
    except ClipNotFoundError:
        raise HTTPException(status_code=404, detail="Clip not found")


@router.delete(
    "/clips/{clip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a clip",
)
async def delete_clip(
    clip_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> None:
    """Delete a clip."""
    try:
        await service.delete_clip(clip_id)
    except ClipNotFoundError:
        raise HTTPException(status_code=404, detail="Clip not found")


@router.post(
    "/clips/{clip_id}/trim",
    response_model=ClipResponse,
    summary="Trim a clip",
)
async def trim_clip(
    clip_id: UUID,
    data: TrimClipRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> ClipResponse:
    """Trim clip from start and/or end."""
    try:
        clip = await service.trim_clip(
            clip_id=clip_id,
            trim_start=data.trim_start,
            trim_end=data.trim_end,
        )
        return ClipResponse.model_validate(clip)
    except ClipNotFoundError:
        raise HTTPException(status_code=404, detail="Clip not found")


@router.post(
    "/clips/{clip_id}/split",
    response_model=SplitClipResponse,
    summary="Split a clip",
)
async def split_clip(
    clip_id: UUID,
    data: SplitClipRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> SplitClipResponse:
    """Split clip at specified time."""
    try:
        first, second = await service.split_clip(clip_id, data.split_time)
        return SplitClipResponse(
            first_clip=ClipResponse.model_validate(first),
            second_clip=ClipResponse.model_validate(second),
        )
    except ClipNotFoundError:
        raise HTTPException(status_code=404, detail="Clip not found")
    except TimelineServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.delete(
    "/clips/{clip_id}/ripple",
    response_model=list[ClipResponse],
    summary="Ripple delete a clip",
)
async def ripple_delete_clip(
    clip_id: UUID,
    track_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> list[ClipResponse]:
    """Delete clip and shift following clips to fill gap."""
    try:
        clips = await service.ripple_delete(clip_id, track_id)
        return [ClipResponse.model_validate(c) for c in clips]
    except ClipNotFoundError:
        raise HTTPException(status_code=404, detail="Clip not found")


@router.post(
    "/clips/{clip_id}/move",
    response_model=ClipResponse,
    summary="Move clip to another track",
)
async def move_clip(
    clip_id: UUID,
    data: MoveClipRequest,
    current_user: CurrentActiveUser,
    service: Annotated[TimelineService, Depends(get_timeline_service)],
) -> ClipResponse:
    """Move clip to a different track."""
    try:
        clip = await service.move_clip_to_track(
            clip_id=clip_id,
            target_track_id=data.target_track_id,
            start_time=data.start_time,
        )
        return ClipResponse.model_validate(clip)
    except ClipNotFoundError:
        raise HTTPException(status_code=404, detail="Clip not found")
