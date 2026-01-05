"""Studio export routes - bridge between Scene Machine Studio and distribution channels."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models.distribution import (
    ContentFormat,
    DistributionChannel,
    StudioExport,
)
from ....shared.models.user import User
from ....shared.models.video import Video
from ...auth.dependencies import get_current_user
from ..schemas import (
    FormatOptimizationRequest,
    FormatOptimizationResponse,
    StudioExportCreate,
    StudioExportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exports", tags=["Exports"])

# Format optimization recommendations
FORMAT_RECOMMENDATIONS = {
    DistributionChannel.STORY_HEAVEN: {
        "preferred": [ContentFormat.VERTICAL_916, ContentFormat.SQUARE_11],
        "acceptable": [ContentFormat.HORIZONTAL_169],
        "max_duration": 600,  # 10 minutes
    },
    DistributionChannel.MOVIE_HEAVEN: {
        "preferred": [ContentFormat.HORIZONTAL_169, ContentFormat.CINEMATIC_235],
        "acceptable": [ContentFormat.IMAX_143],
        "min_duration": 600,  # 10 minutes
    },
}


@router.post("", response_model=StudioExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    data: StudioExportCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StudioExport:
    """Create an export record for Scene Machine Studio content."""
    # Parse channel
    try:
        channel = DistributionChannel(data.channel)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel. Must be one of: {[c.value for c in DistributionChannel]}",
        )

    # Validate duration for channel
    if channel == DistributionChannel.STORY_HEAVEN and data.duration_seconds > 600:
        raise HTTPException(
            status_code=400,
            detail="Content too long for StoryHeaven (max 10 minutes)",
        )
    if channel == DistributionChannel.MOVIE_HEAVEN and data.duration_seconds < 600:
        raise HTTPException(
            status_code=400,
            detail="Content too short for MovieHeaven (min 10 minutes)",
        )

    # Determine format adjustments needed
    format_adjustments = {}
    exported_formats = data.target_formats if data.target_formats else [data.original_format]

    if data.auto_format:
        recommendations = FORMAT_RECOMMENDATIONS[channel]
        original_format = None
        try:
            original_format = ContentFormat(data.original_format)
        except ValueError:
            pass

        if original_format and original_format not in recommendations["preferred"]:
            # Need to reformat
            target = recommendations["preferred"][0]
            format_adjustments = {
                "original": data.original_format,
                "target": target.value,
                "crop_required": original_format in recommendations.get("acceptable", []),
                "letterbox_required": original_format not in recommendations["acceptable"],
            }
            exported_formats = [target.value]

    export = StudioExport(
        studio_project_id=data.studio_project_id,
        studio_user_id=data.studio_user_id,
        creator_id=current_user.id,
        channel=channel,
        original_format=data.original_format,
        exported_formats=exported_formats,
        duration_seconds=data.duration_seconds,
        file_size_bytes=data.file_size_bytes,
        auto_formatted=bool(format_adjustments),
        format_adjustments=format_adjustments,
        export_completed=False,
        published=False,
    )

    session.add(export)
    await session.commit()
    await session.refresh(export)

    logger.info(
        f"Created export {export.id} for studio project {data.studio_project_id} to {channel.value}"
    )
    return export


@router.get("", response_model=list[StudioExportResponse])
async def list_exports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    channel: Optional[str] = None,
    published: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[StudioExport]:
    """List user's studio exports."""
    query = select(StudioExport).where(StudioExport.creator_id == current_user.id)

    if channel:
        try:
            dist_channel = DistributionChannel(channel)
            query = query.where(StudioExport.channel == dist_channel)
        except ValueError:
            pass

    if published is not None:
        query = query.where(StudioExport.published == published)

    query = query.order_by(desc(StudioExport.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{export_id}", response_model=StudioExportResponse)
async def get_export(
    export_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StudioExport:
    """Get export details."""
    export = await session.get(StudioExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return export


@router.post("/{export_id}/complete")
async def mark_export_complete(
    export_id: UUID,
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StudioExportResponse:
    """Mark an export as complete and link to video."""
    export = await session.get(StudioExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify video exists
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    export.video_id = video_id
    export.export_completed = True

    await session.commit()
    await session.refresh(export)

    logger.info(f"Export {export_id} completed, linked to video {video_id}")
    return export


@router.post("/{export_id}/publish")
async def publish_export(
    export_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StudioExportResponse:
    """Publish an exported video to its distribution channel."""
    export = await session.get(StudioExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not export.export_completed:
        raise HTTPException(status_code=400, detail="Export not yet completed")
    if not export.video_id:
        raise HTTPException(status_code=400, detail="No video linked to export")
    if export.published:
        raise HTTPException(status_code=400, detail="Already published")

    # The actual publishing to StoryHeaven/MovieHeaven would be handled
    # by the respective channel routes - this just marks intent
    export.published = True

    await session.commit()
    await session.refresh(export)

    logger.info(f"Export {export_id} published to {export.channel.value}")
    return export


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    export_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an export record."""
    export = await session.get(StudioExport, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await session.delete(export)
    await session.commit()
    logger.info(f"Deleted export {export_id}")


# ============================================================================
# Format Optimization
# ============================================================================


@router.post("/optimize-format", response_model=FormatOptimizationResponse)
async def get_format_optimization(
    data: FormatOptimizationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FormatOptimizationResponse:
    """Get format optimization recommendations for a video."""
    # Get video details
    video = await session.get(Video, data.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Determine target channel
    try:
        channel = DistributionChannel(data.target_channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid target channel")

    recommendations = FORMAT_RECOMMENDATIONS[channel]

    # Analyze current format (would need actual video metadata)
    # For now, assume 16:9 horizontal as default
    original_format = "16:9"
    if video.transcoded_versions:
        original_format = video.transcoded_versions.get("aspect_ratio", "16:9")

    # Determine recommended format
    try:
        original = ContentFormat(original_format)
    except ValueError:
        original = ContentFormat.HORIZONTAL_169

    if original in recommendations["preferred"]:
        recommended = original.value
        adjustments_needed = {}
        quality_impact = "none"
        processing_time = 0
    elif original in recommendations.get("acceptable", []):
        recommended = recommendations["preferred"][0].value
        adjustments_needed = {
            "type": "crop",
            "from": original.value,
            "to": recommended,
        }
        quality_impact = "minimal"
        processing_time = max(30, video.duration_seconds // 10)
    else:
        recommended = recommendations["preferred"][0].value
        adjustments_needed = {
            "type": "letterbox_or_crop",
            "from": original.value,
            "to": recommended,
            "options": ["letterbox", "crop", "ai_extend"],
        }
        quality_impact = "moderate"
        processing_time = max(60, video.duration_seconds // 5)

    return FormatOptimizationResponse(
        original_format=original.value,
        recommended_format=recommended,
        adjustments_needed=adjustments_needed,
        estimated_processing_time_seconds=processing_time,
        quality_impact=quality_impact,
    )


@router.get("/by-project/{project_id}", response_model=list[StudioExportResponse])
async def get_exports_by_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[StudioExport]:
    """Get all exports for a specific studio project."""
    query = (
        select(StudioExport)
        .where(
            StudioExport.studio_project_id == project_id,
            StudioExport.creator_id == current_user.id,
        )
        .order_by(desc(StudioExport.created_at))
    )

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/channels", response_model=list[dict])
async def get_available_channels() -> list[dict]:
    """Get available distribution channels and their requirements."""
    return [
        {
            "id": DistributionChannel.STORY_HEAVEN.value,
            "name": "StoryHeaven",
            "description": "Short-form content platform optimized for mobile viewing",
            "max_duration_minutes": 10,
            "min_duration_minutes": None,
            "preferred_formats": ["9:16", "1:1"],
            "acceptable_formats": ["16:9"],
            "features": [
                "Trending feed",
                "Duets",
                "Sound reuse",
                "Hashtag discovery",
                "Viral tracking",
            ],
        },
        {
            "id": DistributionChannel.MOVIE_HEAVEN.value,
            "name": "MovieHeaven",
            "description": "Long-form content platform for films and series",
            "max_duration_minutes": None,
            "min_duration_minutes": 10,
            "preferred_formats": ["16:9", "2.35:1"],
            "acceptable_formats": ["1.43:1"],
            "features": [
                "Pay-per-view",
                "Rentals",
                "Subscriptions",
                "Film festivals",
                "Premieres",
                "4K/HDR support",
            ],
        },
    ]
