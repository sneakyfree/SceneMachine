"""Assembly and export API routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session

from ...services.assembly import (
    AssemblyService,
    ExportFormat,
    ExportQuality,
    ExportSettings,
)

router = APIRouter(prefix="/assembly", tags=["assembly"])


# Request/Response Models
class ExportRequest(BaseModel):
    """Export request model."""

    format: ExportFormat = ExportFormat.MP4_H264
    quality: ExportQuality = ExportQuality.HIGH
    resolution: str = "1920x1080"
    frame_rate: int = 24
    include_audio: bool = True
    include_subtitles: bool = False
    watermark: bool = False
    output_filename: str | None = None


class AssemblyStatusResponse(BaseModel):
    """Assembly status response."""

    project_id: str
    is_ready: bool
    total_scenes: int
    assembled_scenes: int
    total_shots: int
    generated_shots: int
    missing_shots: list[str]


class TimelineResponse(BaseModel):
    """Timeline response model."""

    project_id: str
    total_duration: float
    scenes: list[dict]


class ExportProgressResponse(BaseModel):
    """Export progress response."""

    export_id: str
    status: str
    percent: float
    stage: str
    message: str


class ExportResultResponse(BaseModel):
    """Export result response."""

    success: bool
    output_path: str | None = None
    file_size: int | None = None
    duration_seconds: float | None = None
    error_message: str | None = None


# Track active exports
_active_exports: dict[str, dict] = {}


@router.get("/status/{project_id}")
async def get_assembly_status(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AssemblyStatusResponse:
    """Get assembly status for a project."""
    service = AssemblyService(session)

    try:
        timeline = await service.get_timeline(project_id)

        # Calculate stats
        total_shots = 0
        generated_shots = 0
        missing_shots = []

        for scene in timeline.scenes:
            for shot in scene.shots:
                total_shots += 1
                if shot.output_path:
                    generated_shots += 1
                else:
                    missing_shots.append(f"{scene.scene_number}-{shot.shot_number}")

        return AssemblyStatusResponse(
            project_id=str(project_id),
            is_ready=generated_shots == total_shots and total_shots > 0,
            total_scenes=len(timeline.scenes),
            assembled_scenes=0,  # Would track scene renders
            total_shots=total_shots,
            generated_shots=generated_shots,
            missing_shots=missing_shots[:10],  # Limit to first 10
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/{project_id}")
async def get_timeline(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TimelineResponse:
    """Get timeline for a project."""
    service = AssemblyService(session)

    try:
        timeline = await service.get_timeline(project_id)

        scenes_data = []
        for scene in timeline.scenes:
            scenes_data.append(
                {
                    "scene_id": str(scene.scene_id),
                    "scene_number": scene.scene_number,
                    "title": scene.title,
                    "duration": scene.duration,
                    "shots": [
                        {
                            "shot_id": str(shot.shot_id),
                            "shot_number": shot.shot_number,
                            "duration": shot.duration,
                            "has_output": shot.output_path is not None,
                            "thumbnail": shot.thumbnail_path,
                        }
                        for shot in scene.shots
                    ],
                }
            )

        return TimelineResponse(
            project_id=str(project_id),
            total_duration=timeline.total_duration,
            scenes=scenes_data,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assemble/scene/{scene_id}")
async def assemble_scene(
    scene_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Assemble a single scene from its shots."""
    service = AssemblyService(session)

    try:
        # Start assembly in background
        export_id = str(scene_id)
        _active_exports[export_id] = {
            "status": "starting",
            "percent": 0,
            "stage": "initializing",
            "message": "Starting scene assembly...",
        }

        async def progress_callback(progress) -> None:
            _active_exports[export_id] = {
                "status": "running",
                "percent": progress.percent,
                "stage": progress.stage,
                "message": progress.message,
            }

        # For now, run synchronously (would use background tasks in production)
        result = await service.assemble_scene(scene_id, progress_callback)

        _active_exports[export_id] = {
            "status": "completed",
            "percent": 100,
            "stage": "complete",
            "message": "Scene assembled successfully",
            "output_path": result.output_path,
        }

        return {
            "success": True,
            "scene_id": str(scene_id),
            "output_path": result.output_path,
            "duration": result.duration,
        }
    except Exception as e:
        _active_exports.get(str(scene_id), {})["status"] = "failed"
        _active_exports.get(str(scene_id), {})["message"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assemble/movie/{project_id}")
async def assemble_movie(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Assemble all scenes into a movie."""
    service = AssemblyService(session)

    try:
        export_id = f"movie-{project_id}"
        _active_exports[export_id] = {
            "status": "starting",
            "percent": 0,
            "stage": "initializing",
            "message": "Starting movie assembly...",
        }

        async def progress_callback(progress) -> None:
            _active_exports[export_id] = {
                "status": "running",
                "percent": progress.percent,
                "stage": progress.stage,
                "message": progress.message,
            }

        output_path = await service.assemble_movie(project_id, progress_callback)

        _active_exports[export_id] = {
            "status": "completed",
            "percent": 100,
            "stage": "complete",
            "message": "Movie assembled successfully",
            "output_path": output_path,
        }

        return {
            "success": True,
            "project_id": str(project_id),
            "output_path": output_path,
        }
    except Exception as e:
        export_id = f"movie-{project_id}"
        if export_id in _active_exports:
            _active_exports[export_id]["status"] = "failed"
            _active_exports[export_id]["message"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/{project_id}")
async def export_movie(
    project_id: UUID,
    request: ExportRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Export movie with specified settings."""
    service = AssemblyService(session)

    try:
        settings = ExportSettings(
            format=request.format,
            quality=request.quality,
            resolution=request.resolution,
            frame_rate=request.frame_rate,
            include_audio=request.include_audio,
            include_subtitles=request.include_subtitles,
            watermark=request.watermark,
        )

        export_id = f"export-{project_id}"
        _active_exports[export_id] = {
            "status": "starting",
            "percent": 0,
            "stage": "initializing",
            "message": "Starting export...",
        }

        async def progress_callback(progress) -> None:
            _active_exports[export_id] = {
                "status": "running",
                "percent": progress.percent,
                "stage": progress.stage,
                "message": progress.message,
            }

        result = await service.export_movie(
            project_id,
            settings,
            request.output_filename,
            progress_callback,
        )

        _active_exports[export_id] = {
            "status": "completed" if result.success else "failed",
            "percent": 100 if result.success else 0,
            "stage": "complete" if result.success else "error",
            "message": "Export completed" if result.success else result.error_message,
            "output_path": result.output_path,
        }

        return {
            "success": result.success,
            "export_id": export_id,
            "output_path": result.output_path,
            "file_size": result.file_size,
            "duration_seconds": result.duration_seconds,
            "error_message": result.error_message,
        }
    except Exception as e:
        export_id = f"export-{project_id}"
        if export_id in _active_exports:
            _active_exports[export_id]["status"] = "failed"
            _active_exports[export_id]["message"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/progress/{export_id}")
async def get_export_progress(export_id: str) -> ExportProgressResponse:
    """Get progress of an export operation."""
    if export_id not in _active_exports:
        raise HTTPException(status_code=404, detail="Export not found")

    progress = _active_exports[export_id]
    return ExportProgressResponse(
        export_id=export_id,
        status=progress.get("status", "unknown"),
        percent=progress.get("percent", 0),
        stage=progress.get("stage", ""),
        message=progress.get("message", ""),
    )


@router.get("/export/history/{project_id}")
async def get_export_history(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get export history for a project."""
    service = AssemblyService(session)

    try:
        history = await service.get_export_history(project_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_export_formats(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get available export formats."""
    service = AssemblyService(session)
    return await service.get_export_formats()


@router.get("/quality-presets")
async def get_quality_presets(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get available quality presets."""
    service = AssemblyService(session)
    return await service.get_quality_presets()


@router.delete("/export/{export_id}")
async def cancel_export(export_id: str) -> dict:
    """Cancel an ongoing export."""
    if export_id not in _active_exports:
        raise HTTPException(status_code=404, detail="Export not found")

    progress = _active_exports[export_id]
    if progress.get("status") in ("completed", "failed"):
        return {"success": False, "message": "Export already finished"}

    # Mark as cancelled
    _active_exports[export_id] = {
        "status": "cancelled",
        "percent": progress.get("percent", 0),
        "stage": "cancelled",
        "message": "Export cancelled by user",
    }

    return {"success": True, "message": "Export cancelled"}
