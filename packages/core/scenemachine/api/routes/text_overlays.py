"""API routes for text overlays."""

import contextlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.models.text_overlay import (
    DEFAULT_STYLES,
    TextAnimation,
    TextOverlay,
    TextOverlayType,
    TextPosition,
)

router = APIRouter(prefix="/text-overlays", tags=["text-overlays"])


# ============================================================================
# Request/Response Models
# ============================================================================


class TextStyleSchema(BaseModel):
    """Text style configuration."""

    fontFamily: str = "Arial"
    fontSize: int = 48
    fontWeight: str = "bold"
    fontStyle: str = "normal"
    textDecoration: str = "none"
    color: str = "#FFFFFF"
    backgroundColor: str = "#000000"
    backgroundOpacity: float = 0.0
    textAlign: str = "center"
    letterSpacing: int = 0
    lineHeight: float = 1.2
    textShadow: bool = True
    textShadowColor: str = "#000000"
    textShadowBlur: int = 4


class AnimationSchema(BaseModel):
    """Animation configuration."""

    in_: str = Field("fade_in", alias="in")
    out: str = "fade_out"
    inDuration: int = 500
    outDuration: int = 500

    class Config:
        populate_by_name = True


class TimingSchema(BaseModel):
    """Timing configuration."""

    startTime: int = 0
    duration: int = 5000


class TextOverlayCreate(BaseModel):
    """Request body for creating a text overlay."""

    type: str = "custom"
    text: str
    position: str = "center"
    customX: float | None = None
    customY: float | None = None
    style: TextStyleSchema | None = None
    animation: AnimationSchema | None = None
    timing: TimingSchema | None = None
    isVisible: bool = True
    zIndex: int = 1

    # Parent reference (one of these should be set)
    shot_id: str | None = None
    scene_id: str | None = None
    project_id: str | None = None


class TextOverlayUpdate(BaseModel):
    """Request body for updating a text overlay."""

    type: str | None = None
    text: str | None = None
    position: str | None = None
    customX: float | None = None
    customY: float | None = None
    style: TextStyleSchema | None = None
    animation: AnimationSchema | None = None
    timing: TimingSchema | None = None
    isVisible: bool | None = None
    zIndex: int | None = None


class TextOverlayResponse(BaseModel):
    """Response model for a text overlay."""

    id: str
    type: str
    text: str
    position: str
    customX: float | None = None
    customY: float | None = None
    style: dict
    animation: dict
    timing: dict
    isVisible: bool
    zIndex: int
    shot_id: str | None = None
    scene_id: str | None = None
    project_id: str | None = None


class TextOverlayListResponse(BaseModel):
    """Response model for list of text overlays."""

    overlays: list[TextOverlayResponse]
    total: int


class PresetResponse(BaseModel):
    """Response model for a preset."""

    type: str
    label: str
    style: dict


# ============================================================================
# Helper Functions
# ============================================================================


def _overlay_to_response(overlay: TextOverlay) -> TextOverlayResponse:
    """Convert TextOverlay model to response."""
    data = overlay.to_dict()
    return TextOverlayResponse(
        id=data["id"],
        type=data["type"],
        text=data["text"],
        position=data["position"],
        customX=data.get("customX"),
        customY=data.get("customY"),
        style=data["style"],
        animation=data["animation"],
        timing=data["timing"],
        isVisible=data["isVisible"],
        zIndex=data["zIndex"],
        shot_id=str(overlay.shot_id) if overlay.shot_id else None,
        scene_id=str(overlay.scene_id) if overlay.scene_id else None,
        project_id=str(overlay.project_id) if overlay.project_id else None,
    )


# ============================================================================
# Routes
# ============================================================================


@router.get("/presets", response_model=list[PresetResponse])
async def get_presets():
    """Get available text overlay presets."""
    presets = [
        PresetResponse(type="title", label="Title", style=DEFAULT_STYLES[TextOverlayType.TITLE]),
        PresetResponse(
            type="subtitle", label="Subtitle", style=DEFAULT_STYLES[TextOverlayType.SUBTITLE]
        ),
        PresetResponse(
            type="lower_third",
            label="Lower Third",
            style=DEFAULT_STYLES[TextOverlayType.LOWER_THIRD],
        ),
        PresetResponse(
            type="caption", label="Caption", style=DEFAULT_STYLES[TextOverlayType.CAPTION]
        ),
        PresetResponse(type="custom", label="Custom", style=DEFAULT_STYLES[TextOverlayType.CUSTOM]),
    ]
    return presets


@router.get("/shot/{shot_id}", response_model=TextOverlayListResponse)
async def get_shot_overlays(
    shot_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all text overlays for a shot."""
    stmt = (
        select(TextOverlay)
        .where(TextOverlay.shot_id == UUID(shot_id))
        .order_by(TextOverlay.z_index)
    )
    result = await session.execute(stmt)
    overlays = result.scalars().all()

    return TextOverlayListResponse(
        overlays=[_overlay_to_response(o) for o in overlays],
        total=len(overlays),
    )


@router.get("/scene/{scene_id}", response_model=TextOverlayListResponse)
async def get_scene_overlays(
    scene_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all text overlays for a scene."""
    stmt = (
        select(TextOverlay)
        .where(TextOverlay.scene_id == UUID(scene_id))
        .order_by(TextOverlay.z_index)
    )
    result = await session.execute(stmt)
    overlays = result.scalars().all()

    return TextOverlayListResponse(
        overlays=[_overlay_to_response(o) for o in overlays],
        total=len(overlays),
    )


@router.get("/project/{project_id}", response_model=TextOverlayListResponse)
async def get_project_overlays(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all text overlays for a project (project-level only, not shots/scenes)."""
    stmt = (
        select(TextOverlay)
        .where(TextOverlay.project_id == UUID(project_id))
        .order_by(TextOverlay.z_index)
    )
    result = await session.execute(stmt)
    overlays = result.scalars().all()

    return TextOverlayListResponse(
        overlays=[_overlay_to_response(o) for o in overlays],
        total=len(overlays),
    )


@router.get("/{overlay_id}", response_model=TextOverlayResponse)
async def get_overlay(
    overlay_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific text overlay."""
    stmt = select(TextOverlay).where(TextOverlay.id == UUID(overlay_id))
    result = await session.execute(stmt)
    overlay = result.scalar_one_or_none()

    if not overlay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Text overlay {overlay_id} not found",
        )

    return _overlay_to_response(overlay)


@router.post("", response_model=TextOverlayResponse, status_code=status.HTTP_201_CREATED)
async def create_overlay(
    data: TextOverlayCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new text overlay."""
    # Determine parent
    shot_id = UUID(data.shot_id) if data.shot_id else None
    scene_id = UUID(data.scene_id) if data.scene_id else None
    project_id = UUID(data.project_id) if data.project_id else None

    if not any([shot_id, scene_id, project_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One of shot_id, scene_id, or project_id is required",
        )

    # Get overlay type
    try:
        overlay_type = TextOverlayType(data.type)
    except ValueError:
        overlay_type = TextOverlayType.CUSTOM

    # Get position
    try:
        position = TextPosition(data.position)
    except ValueError:
        position = TextPosition.CENTER

    # Get default style for type and merge with provided style
    default_style = DEFAULT_STYLES.get(overlay_type, DEFAULT_STYLES[TextOverlayType.CUSTOM])
    style = {**default_style}
    if data.style:
        style.update(data.style.model_dump())

    # Get animation settings
    anim_in = TextAnimation.FADE_IN
    anim_out = TextAnimation.FADE_OUT
    anim_in_dur = 500
    anim_out_dur = 500
    if data.animation:
        with contextlib.suppress(ValueError):
            anim_in = TextAnimation(data.animation.in_)
        with contextlib.suppress(ValueError):
            anim_out = TextAnimation(data.animation.out)
        anim_in_dur = data.animation.inDuration
        anim_out_dur = data.animation.outDuration

    # Get timing
    start_time = 0
    duration = 5000
    if data.timing:
        start_time = data.timing.startTime
        duration = data.timing.duration

    overlay = TextOverlay(
        shot_id=shot_id,
        scene_id=scene_id,
        project_id=project_id,
        overlay_type=overlay_type,
        text=data.text,
        position=position,
        custom_x=data.customX,
        custom_y=data.customY,
        style=style,
        animation_in=anim_in,
        animation_out=anim_out,
        animation_in_duration_ms=anim_in_dur,
        animation_out_duration_ms=anim_out_dur,
        start_time_ms=start_time,
        duration_ms=duration,
        is_visible=data.isVisible,
        z_index=data.zIndex,
    )

    session.add(overlay)
    await session.commit()
    await session.refresh(overlay)

    return _overlay_to_response(overlay)


@router.patch("/{overlay_id}", response_model=TextOverlayResponse)
async def update_overlay(
    overlay_id: str,
    data: TextOverlayUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a text overlay."""
    stmt = select(TextOverlay).where(TextOverlay.id == UUID(overlay_id))
    result = await session.execute(stmt)
    overlay = result.scalar_one_or_none()

    if not overlay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Text overlay {overlay_id} not found",
        )

    # Update fields
    if data.type is not None:
        with contextlib.suppress(ValueError):
            overlay.overlay_type = TextOverlayType(data.type)

    if data.text is not None:
        overlay.text = data.text

    if data.position is not None:
        with contextlib.suppress(ValueError):
            overlay.position = TextPosition(data.position)

    if data.customX is not None:
        overlay.custom_x = data.customX

    if data.customY is not None:
        overlay.custom_y = data.customY

    if data.style is not None:
        # Merge with existing style
        current_style = overlay.style or {}
        current_style.update(data.style.model_dump())
        overlay.style = current_style

    if data.animation is not None:
        with contextlib.suppress(ValueError):
            overlay.animation_in = TextAnimation(data.animation.in_)
        with contextlib.suppress(ValueError):
            overlay.animation_out = TextAnimation(data.animation.out)
        overlay.animation_in_duration_ms = data.animation.inDuration
        overlay.animation_out_duration_ms = data.animation.outDuration

    if data.timing is not None:
        overlay.start_time_ms = data.timing.startTime
        overlay.duration_ms = data.timing.duration

    if data.isVisible is not None:
        overlay.is_visible = data.isVisible

    if data.zIndex is not None:
        overlay.z_index = data.zIndex

    await session.commit()
    await session.refresh(overlay)

    return _overlay_to_response(overlay)


@router.delete("/{overlay_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_overlay(
    overlay_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a text overlay."""
    stmt = delete(TextOverlay).where(TextOverlay.id == UUID(overlay_id))
    result = await session.execute(stmt)
    await session.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Text overlay {overlay_id} not found",
        )


@router.post("/shot/{shot_id}/batch", response_model=TextOverlayListResponse)
async def batch_update_shot_overlays(
    shot_id: str,
    overlays: list[TextOverlayCreate],
    session: AsyncSession = Depends(get_session),
):
    """Replace all text overlays for a shot with a new set.

    This is useful for syncing the frontend state with the backend.
    """
    # Delete existing overlays
    await session.execute(delete(TextOverlay).where(TextOverlay.shot_id == UUID(shot_id)))

    # Create new overlays
    new_overlays = []
    for data in overlays:
        # Get overlay type
        try:
            overlay_type = TextOverlayType(data.type)
        except ValueError:
            overlay_type = TextOverlayType.CUSTOM

        # Get position
        try:
            position = TextPosition(data.position)
        except ValueError:
            position = TextPosition.CENTER

        # Get style
        default_style = DEFAULT_STYLES.get(overlay_type, DEFAULT_STYLES[TextOverlayType.CUSTOM])
        style = {**default_style}
        if data.style:
            style.update(data.style.model_dump())

        # Get animation
        anim_in = TextAnimation.FADE_IN
        anim_out = TextAnimation.FADE_OUT
        anim_in_dur = 500
        anim_out_dur = 500
        if data.animation:
            with contextlib.suppress(ValueError):
                anim_in = TextAnimation(data.animation.in_)
            with contextlib.suppress(ValueError):
                anim_out = TextAnimation(data.animation.out)
            anim_in_dur = data.animation.inDuration
            anim_out_dur = data.animation.outDuration

        # Get timing
        start_time = 0
        duration = 5000
        if data.timing:
            start_time = data.timing.startTime
            duration = data.timing.duration

        overlay = TextOverlay(
            shot_id=UUID(shot_id),
            overlay_type=overlay_type,
            text=data.text,
            position=position,
            custom_x=data.customX,
            custom_y=data.customY,
            style=style,
            animation_in=anim_in,
            animation_out=anim_out,
            animation_in_duration_ms=anim_in_dur,
            animation_out_duration_ms=anim_out_dur,
            start_time_ms=start_time,
            duration_ms=duration,
            is_visible=data.isVisible,
            z_index=data.zIndex,
        )
        session.add(overlay)
        new_overlays.append(overlay)

    await session.commit()

    # Refresh all overlays to get IDs
    for overlay in new_overlays:
        await session.refresh(overlay)

    return TextOverlayListResponse(
        overlays=[_overlay_to_response(o) for o in new_overlays],
        total=len(new_overlays),
    )
