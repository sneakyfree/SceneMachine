"""Lip Sync API routes."""

import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.deps import get_db
from scenemachine.services.lipsync import (
    LipSyncProgress,
    LipSyncProvider,
    get_lip_sync_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lipsync", tags=["lipsync"])


class StartLipSyncRequest(BaseModel):
    """Request to start lip sync processing."""

    video_id: str = Field(..., description="ID of the video clip to apply lip sync")
    audio_id: str = Field(..., description="ID of the audio file to use")
    provider: str = Field(
        default="mock",
        description="Lip sync provider (mock, rhubarb, wav2lip, sadtalker)",
    )


class LipSyncJobResponse(BaseModel):
    """Response for lip sync job."""

    job_id: str
    video_id: str
    audio_id: str
    provider: str
    status: str
    progress_percent: float
    progress_message: str
    output_path: str | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class AvailableProvidersResponse(BaseModel):
    """Response for available providers."""

    providers: List[Dict[str, Any]]


# In-memory job storage (would be DB in production)
_jobs: Dict[str, Dict[str, Any]] = {}
_job_counter = 0


@router.post("/", response_model=LipSyncJobResponse)
async def start_lip_sync(
    request: StartLipSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Start a lip sync processing job."""
    global _job_counter
    _job_counter += 1
    job_id = f"lipsync-{_job_counter}"

    # Validate provider
    try:
        provider = LipSyncProvider(request.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")

    # Get lip sync service
    service = get_lip_sync_service()

    # Check if provider is available
    available_providers = await service.get_available_providers()
    provider_info = next(
        (p for p in available_providers if p["provider"] == provider.value),
        None,
    )

    if not provider_info or not provider_info["available"]:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider.value} is not available",
        )

    # TODO: Validate video_id and audio_id exist in database
    # For now, we'll accept any strings

    # Create job record
    from datetime import datetime
    job = {
        "job_id": job_id,
        "video_id": request.video_id,
        "audio_id": request.audio_id,
        "provider": provider.value,
        "status": "queued",
        "progress_percent": 0.0,
        "progress_message": "Job queued",
        "output_path": None,
        "error_message": None,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }

    _jobs[job_id] = job

    # Start processing in background (would use actual task queue in production)
    import asyncio
    asyncio.create_task(_process_lip_sync_job(job_id, request))

    return job


async def _process_lip_sync_job(job_id: str, request: StartLipSyncRequest) -> None:
    """Background task to process lip sync job."""
    job = _jobs[job_id]

    try:
        job["status"] = "processing"

        # Get lip sync service
        service = get_lip_sync_service()
        provider = LipSyncProvider(request.provider)

        # Progress callback to update job
        async def progress_callback(progress: LipSyncProgress) -> None:
            job["progress_percent"] = progress.percent
            job["progress_message"] = progress.message
            logger.info(
                f"Lip sync job {job_id}: {progress.percent}% - {progress.message}"
            )

        # TODO: Get actual video and audio paths from database
        # For now, use mock paths
        video_path = f"/mock/videos/{request.video_id}.mp4"
        audio_path = f"/mock/audio/{request.audio_id}.wav"
        output_path = f"/mock/output/{job_id}.mp4"

        # Process lip sync
        result = await service.apply_to_video(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            provider=provider,
            progress_callback=progress_callback,
        )

        if result.success:
            from datetime import datetime
            job["status"] = "completed"
            job["progress_percent"] = 100.0
            job["progress_message"] = "Lip sync complete"
            job["output_path"] = result.output_video_path
            job["completed_at"] = datetime.utcnow().isoformat()
        else:
            job["status"] = "failed"
            job["error_message"] = result.error_message

    except Exception as e:
        logger.exception(f"Lip sync job {job_id} failed")
        job["status"] = "failed"
        job["error_message"] = str(e)


@router.get("/jobs", response_model=List[LipSyncJobResponse])
async def list_jobs() -> List[Dict[str, Any]]:
    """List all lip sync jobs."""
    return list(_jobs.values())


@router.get("/jobs/{job_id}", response_model=LipSyncJobResponse)
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get lip sync job by ID."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, str]:
    """Cancel a lip sync job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Job already finished")

    job["status"] = "cancelled"
    job["error_message"] = "Job cancelled by user"

    return {"status": "cancelled", "job_id": job_id}


@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_providers() -> Dict[str, List[Dict[str, Any]]]:
    """Get list of available lip sync providers."""
    service = get_lip_sync_service()
    providers = await service.get_available_providers()

    return {"providers": providers}


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates."""
    await websocket.accept()

    try:
        # Send initial job state
        job = _jobs.get(job_id)
        if not job:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return

        await websocket.send_json({"type": "job_update", "data": job})

        # Poll for updates and send to client
        import asyncio
        while True:
            job = _jobs.get(job_id)
            if not job:
                break

            await websocket.send_json({"type": "job_update", "data": job})

            # If job finished, close connection
            if job["status"] in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(0.5)  # Poll every 500ms

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for job {job_id}")
        await websocket.close()
