"""Scene planning API routes.

Handles scene analysis, shot breakdown generation, and approval workflow.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.models.shot import CameraMovement, ShotType
from scenemachine.services.scene_planning import ScenePlanningService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenes", tags=["scenes"])


# Request/Response Models
class SceneResponse(BaseModel):
    """Scene response model."""

    id: str
    project_id: str
    screenplay_id: str
    scene_number: str
    sequence_number: int
    heading: str
    scene_type: str
    location: str
    time_of_day: str
    state: str
    character_ids: list[str] = Field(default_factory=list)
    analysis: dict[str, Any] | None = None
    shot_breakdown: dict[str, Any] | None = None
    shot_breakdown_approved: bool = False
    estimated_duration_seconds: float | None = None
    shot_count: int = 0


class SceneWithShotsResponse(SceneResponse):
    """Scene response with shots included."""

    shots: list["ShotResponse"] = Field(default_factory=list)


class ShotResponse(BaseModel):
    """Shot response model."""

    id: str
    scene_id: str
    shot_number: str
    sequence_number: int
    shot_type: str
    camera_movement: str
    description: str
    dialogue: str | None = None
    action: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    duration_seconds: float
    composition_notes: str | None = None
    lighting_notes: str | None = None
    state: str
    prompt: str | None = None


class SceneAnalysisResponse(BaseModel):
    """Scene analysis response model."""

    summary: str
    mood: str
    emotional_arc: list[str]
    key_moments: list[dict[str, Any]]
    visual_style_suggestions: list[str]
    pacing: str
    importance: int
    suggested_shot_count: int
    dialogue_heavy: bool
    action_heavy: bool


class ShotBreakdownResponse(BaseModel):
    """Shot breakdown response model."""

    scene_id: str
    approach: str
    coverage_style: str
    notes: str
    shots: list[ShotResponse]
    estimated_duration: float


class UpdateShotRequest(BaseModel):
    """Request to update a shot."""

    shot_type: str | None = None
    camera_movement: str | None = None
    description: str | None = None
    dialogue: str | None = None
    action: str | None = None
    duration_seconds: float | None = None
    composition_notes: str | None = None
    lighting_notes: str | None = None


class AddShotRequest(BaseModel):
    """Request to add a new shot."""

    shot_type: str
    description: str
    camera_movement: str = "static"
    duration_seconds: float = 3.0
    after_shot_id: str | None = None


class ReorderShotsRequest(BaseModel):
    """Request to reorder shots."""

    shot_ids: list[str]


# Helper functions
def scene_to_response(scene, include_shots: bool = False) -> dict[str, Any]:
    """Convert scene model to response dict."""
    # Scene doesn't have screenplay_id directly - it's accessed via project
    screenplay_id = getattr(scene, 'screenplay_id', None)
    if screenplay_id is None and hasattr(scene, 'project') and scene.project:
        screenplay_id = scene.project.screenplay_id if hasattr(scene.project, 'screenplay_id') else None
    data = {
        "id": str(scene.id),
        "project_id": str(scene.project_id),
        "screenplay_id": str(screenplay_id) if screenplay_id else None,
        "scene_number": scene.scene_number,
        "sequence_number": scene.sequence_number,
        "heading": scene.heading,
        "scene_type": scene.scene_type.value,
        "location": scene.location,
        "time_of_day": scene.time_of_day.value,
        "state": scene.state.value,
        "character_ids": [str(cid) for cid in (scene.character_ids or [])],
        "analysis": scene.analysis,
        "shot_breakdown": scene.shot_breakdown,
        "shot_breakdown_approved": scene.shot_breakdown_approved,
        "estimated_duration_seconds": scene.estimated_duration_seconds,
        "shot_count": len(scene.shots) if hasattr(scene, "shots") and scene.shots else 0,
    }

    if include_shots and hasattr(scene, "shots") and scene.shots:
        data["shots"] = [shot_to_response(s) for s in sorted(scene.shots, key=lambda x: x.sequence_number)]

    return data


def shot_to_response(shot) -> dict[str, Any]:
    """Convert shot model to response dict."""
    return {
        "id": str(shot.id),
        "scene_id": str(shot.scene_id),
        "shot_number": shot.shot_number,
        "sequence_number": shot.sequence_number,
        "shot_type": shot.shot_type.value,
        "camera_movement": shot.camera_movement.value,
        "description": shot.description,
        "dialogue": shot.dialogue,
        "action": shot.action,
        "character_ids": [str(cid) for cid in (shot.character_ids or [])],
        "duration_seconds": shot.duration_seconds,
        "composition_notes": shot.composition_notes,
        "lighting_notes": shot.lighting_notes,
        "state": shot.state.value,
        "prompt": shot.prompt,
    }


# Routes
@router.get("/project/{project_id}")
async def list_project_scenes(
    project_id: str,
    include_shots: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[SceneResponse]:
    """List all scenes for a project.

    Args:
        project_id: Project UUID
        include_shots: Whether to include shots in response

    Returns:
        List of scenes
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    service = ScenePlanningService(session)
    scenes = await service.get_project_scenes(pid, include_shots=include_shots)

    return [scene_to_response(s, include_shots=include_shots) for s in scenes]


@router.get("/{scene_id}")
async def get_scene(
    scene_id: str,
    include_shots: bool = True,
    session: AsyncSession = Depends(get_session),
) -> SceneWithShotsResponse:
    """Get a scene by ID.

    Args:
        scene_id: Scene UUID
        include_shots: Whether to include shots

    Returns:
        Scene details with optional shots
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    service = ScenePlanningService(session)
    scene = await service.get_scene(sid, include_shots=include_shots)

    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene {scene_id} not found",
        )

    return scene_to_response(scene, include_shots=include_shots)


@router.post("/{scene_id}/analyze")
async def analyze_scene(
    scene_id: str,
    session: AsyncSession = Depends(get_session),
) -> SceneAnalysisResponse:
    """Analyze a scene for shot planning.

    Args:
        scene_id: Scene UUID

    Returns:
        Scene analysis with mood, pacing, key moments
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    service = ScenePlanningService(session)

    try:
        analysis = await service.analyze_scene(sid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return SceneAnalysisResponse(
        summary=analysis.summary,
        mood=analysis.mood,
        emotional_arc=analysis.emotional_arc,
        key_moments=analysis.key_moments,
        visual_style_suggestions=analysis.visual_style_suggestions,
        pacing=analysis.pacing,
        importance=analysis.importance,
        suggested_shot_count=analysis.suggested_shot_count,
        dialogue_heavy=analysis.dialogue_heavy,
        action_heavy=analysis.action_heavy,
    )


@router.post("/{scene_id}/breakdown")
async def generate_shot_breakdown(
    scene_id: str,
    regenerate: bool = False,
    session: AsyncSession = Depends(get_session),
) -> ShotBreakdownResponse:
    """Generate shot breakdown for a scene.

    Args:
        scene_id: Scene UUID
        regenerate: Whether to regenerate if breakdown exists

    Returns:
        Shot breakdown with all shots
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    service = ScenePlanningService(session)

    try:
        breakdown = await service.generate_shot_breakdown(sid, regenerate=regenerate)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return ShotBreakdownResponse(
        scene_id=breakdown.scene_id,
        approach=breakdown.approach,
        coverage_style=breakdown.coverage_style,
        notes=breakdown.notes,
        shots=[
            ShotResponse(
                id="",  # Will be set from DB
                scene_id=breakdown.scene_id,
                shot_number=s.shot_number,
                sequence_number=s.sequence_number,
                shot_type=s.shot_type.value,
                camera_movement=s.camera_movement.value,
                description=s.description,
                dialogue=s.dialogue,
                action=s.action,
                character_ids=[str(cid) for cid in s.character_ids],
                duration_seconds=s.duration_seconds,
                composition_notes=s.composition_notes,
                lighting_notes=s.lighting_notes,
                state="planned",
                prompt=None,
            )
            for s in breakdown.shots
        ],
        estimated_duration=breakdown.estimated_duration,
    )


@router.post("/{scene_id}/approve")
async def approve_shot_breakdown(
    scene_id: str,
    session: AsyncSession = Depends(get_session),
) -> SceneResponse:
    """Approve the shot breakdown for a scene.

    Args:
        scene_id: Scene UUID

    Returns:
        Updated scene
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    service = ScenePlanningService(session)

    try:
        scene = await service.approve_shot_breakdown(sid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return scene_to_response(scene)


# Shot management routes
@router.get("/{scene_id}/shots")
async def list_scene_shots(
    scene_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[ShotResponse]:
    """List all shots for a scene.

    Args:
        scene_id: Scene UUID

    Returns:
        List of shots ordered by sequence
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    service = ScenePlanningService(session)
    scene = await service.get_scene(sid, include_shots=True)

    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene {scene_id} not found",
        )

    shots = sorted(scene.shots, key=lambda x: x.sequence_number) if scene.shots else []
    return [shot_to_response(s) for s in shots]


@router.post("/{scene_id}/shots")
async def add_shot(
    scene_id: str,
    request: AddShotRequest,
    session: AsyncSession = Depends(get_session),
) -> ShotResponse:
    """Add a new shot to a scene.

    Args:
        scene_id: Scene UUID
        request: Shot details

    Returns:
        Created shot
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    try:
        shot_type = ShotType(request.shot_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid shot type: {request.shot_type}",
        )

    try:
        camera_movement = CameraMovement(request.camera_movement)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid camera movement: {request.camera_movement}",
        )

    after_shot = UUID(request.after_shot_id) if request.after_shot_id else None

    service = ScenePlanningService(session)

    try:
        shot = await service.add_shot(
            scene_id=sid,
            shot_type=shot_type,
            description=request.description,
            camera_movement=camera_movement,
            duration_seconds=request.duration_seconds,
            after_shot_id=after_shot,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return shot_to_response(shot)


@router.get("/shots/{shot_id}")
async def get_shot(
    shot_id: str,
    session: AsyncSession = Depends(get_session),
) -> ShotResponse:
    """Get a shot by ID.

    Args:
        shot_id: Shot UUID

    Returns:
        Shot details
    """
    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    service = ScenePlanningService(session)
    shot = await service.get_shot(sid)

    if not shot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shot {shot_id} not found",
        )

    return shot_to_response(shot)


@router.patch("/shots/{shot_id}")
async def update_shot(
    shot_id: str,
    request: UpdateShotRequest,
    session: AsyncSession = Depends(get_session),
) -> ShotResponse:
    """Update a shot.

    Args:
        shot_id: Shot UUID
        request: Fields to update

    Returns:
        Updated shot
    """
    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    shot_type = None
    if request.shot_type:
        try:
            shot_type = ShotType(request.shot_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid shot type: {request.shot_type}",
            )

    camera_movement = None
    if request.camera_movement:
        try:
            camera_movement = CameraMovement(request.camera_movement)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid camera movement: {request.camera_movement}",
            )

    service = ScenePlanningService(session)

    try:
        shot = await service.update_shot(
            shot_id=sid,
            shot_type=shot_type,
            camera_movement=camera_movement,
            description=request.description,
            dialogue=request.dialogue,
            action=request.action,
            duration_seconds=request.duration_seconds,
            composition_notes=request.composition_notes,
            lighting_notes=request.lighting_notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return shot_to_response(shot)


@router.delete("/shots/{shot_id}")
async def delete_shot(
    shot_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete a shot.

    Args:
        shot_id: Shot UUID

    Returns:
        Success status
    """
    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    service = ScenePlanningService(session)

    try:
        deleted = await service.delete_shot(sid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shot {shot_id} not found",
        )

    return {"success": True}


# Reference data endpoints
@router.get("/reference/shot-types")
async def list_shot_types() -> list[dict[str, str]]:
    """Get available shot types.

    Returns:
        List of shot types with descriptions
    """
    shot_type_descriptions = {
        ShotType.ESTABLISHING: "Wide shot that establishes location/setting",
        ShotType.WIDE: "Full view of the scene with all characters",
        ShotType.FULL: "Full body shot of character",
        ShotType.MEDIUM: "Characters visible from waist up",
        ShotType.MEDIUM_CLOSE_UP: "Characters visible from chest up",
        ShotType.CLOSE_UP: "Face or important detail fills frame",
        ShotType.EXTREME_CLOSE_UP: "Very tight on specific detail",
        ShotType.OVER_THE_SHOULDER: "Shot from behind one character",
        ShotType.POV: "Point of view from character's perspective",
        ShotType.TWO_SHOT: "Two characters in frame together",
        ShotType.GROUP: "Multiple characters in frame",
        ShotType.INSERT: "Close shot of specific object or detail",
        ShotType.CUTAWAY: "Shot that cuts away from main action",
    }

    return [
        {"value": st.value, "label": st.value.replace("_", " ").title(), "description": desc}
        for st, desc in shot_type_descriptions.items()
    ]


@router.get("/reference/camera-movements")
async def list_camera_movements() -> list[dict[str, str]]:
    """Get available camera movements.

    Returns:
        List of camera movements with descriptions
    """
    movement_descriptions = {
        CameraMovement.STATIC: "Camera remains stationary",
        CameraMovement.PAN: "Camera pivots horizontally on fixed point",
        CameraMovement.TILT: "Camera pivots vertically on fixed point",
        CameraMovement.DOLLY: "Camera moves toward or away from subject",
        CameraMovement.TRUCK: "Camera moves left or right parallel to subject",
        CameraMovement.CRANE: "Camera moves up or down vertically",
        CameraMovement.HANDHELD: "Camera held by operator for organic movement",
        CameraMovement.STEADICAM: "Stabilized moving camera for smooth tracking",
        CameraMovement.ZOOM: "Lens zooms in or out (not camera movement)",
        CameraMovement.RACK_FOCUS: "Focus shifts between subjects at different depths",
        CameraMovement.TRACKING: "Camera follows alongside moving subject",
    }

    return [
        {"value": cm.value, "label": cm.value.replace("_", " ").title(), "description": desc}
        for cm, desc in movement_descriptions.items()
    ]
