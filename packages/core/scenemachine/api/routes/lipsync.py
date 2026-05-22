"""Lip Sync API routes."""

import contextlib
import logging
import os
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.database import get_db_manager
from scenemachine.models.asset import Asset, AssetType
from scenemachine.models.lipsync_job import LipsyncJob, LipsyncJobStatus
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

    providers: list[dict[str, Any]]


@router.post("/", response_model=LipSyncJobResponse)
async def start_lip_sync(
    request: StartLipSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start a lip sync processing job."""
    global _job_counter
    _job_counter += 1

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

    # Validate video_id exists and is a video asset
    try:
        video_uuid = UUID(request.video_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid video_id format: {request.video_id}")

    video_result = await db.execute(select(Asset).where(Asset.id == video_uuid))
    video_asset = video_result.scalar_one_or_none()

    if not video_asset:
        raise HTTPException(
            status_code=404, detail=f"Video asset with id {request.video_id} not found"
        )

    if not video_asset.is_video:
        raise HTTPException(
            status_code=400,
            detail=f"Asset {request.video_id} is not a video (type: {video_asset.asset_type.value})",
        )

    # Validate audio_id exists and is an audio asset
    try:
        audio_uuid = UUID(request.audio_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid audio_id format: {request.audio_id}")

    audio_result = await db.execute(select(Asset).where(Asset.id == audio_uuid))
    audio_asset = audio_result.scalar_one_or_none()

    if not audio_asset:
        raise HTTPException(
            status_code=404, detail=f"Audio asset with id {request.audio_id} not found"
        )

    # Accept SHOT_AUDIO type for audio assets
    if audio_asset.asset_type != AssetType.SHOT_AUDIO:
        raise HTTPException(
            status_code=400,
            detail=f"Asset {request.audio_id} is not an audio file (type: {audio_asset.asset_type.value})",
        )

    # Create job record in database
    job = LipsyncJob(
        video_asset_id=video_uuid,
        audio_asset_id=audio_uuid,
        provider=provider.value,
        status=LipsyncJobStatus.QUEUED,
        progress_percent=0.0,
        progress_message="Job queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Start processing in background
    import asyncio

    asyncio.create_task(_process_lip_sync_job(str(job.id)))

    # Return job response
    return {
        "job_id": str(job.id),
        "video_id": request.video_id,
        "audio_id": request.audio_id,
        "provider": provider.value,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "progress_message": job.progress_message,
        "output_path": job.output_path,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


async def _process_lip_sync_job(job_id: str) -> None:
    """Background task to process lip sync job."""
    # Get job from database
    db_manager = get_db_manager()
    async with db_manager.session() as db:
        result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == UUID(job_id)))
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"Lip sync job {job_id} not found in database")
            return

    # Log job start
    logger.info(
        f"Starting lip sync job {job_id} for video={job.video_asset_id}, "
        f"audio={job.audio_asset_id}, provider={job.provider}"
    )

    try:
        # Update job status to processing
        async with db_manager.session() as db:
            await db.execute(
                select(LipsyncJob).where(LipsyncJob.id == UUID(job_id)).with_for_update()
            )
            job.status = LipsyncJobStatus.PROCESSING
            db.add(job)
            await db.commit()

        # Get lip sync service
        service = get_lip_sync_service()
        provider = LipSyncProvider(job.provider)

        # Progress callback to update job in database
        async def progress_callback(progress: LipSyncProgress) -> None:
            async with db_manager.session() as db:
                result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == UUID(job_id)))
                job_update = result.scalar_one_or_none()
                if job_update:
                    job_update.progress_percent = progress.percent
                    job_update.progress_message = progress.message
                    await db.commit()
            logger.info(f"Lip sync job {job_id}: {progress.percent}% - {progress.message}")

        # Get actual video and audio paths from database
        async with db_manager.session() as db:
            video_result = await db.execute(select(Asset).where(Asset.id == job.video_asset_id))
            video_asset = video_result.scalar_one_or_none()

            audio_result = await db.execute(select(Asset).where(Asset.id == job.audio_asset_id))
            audio_asset = audio_result.scalar_one_or_none()

            if not video_asset or not audio_asset:
                raise ValueError("Video or audio asset no longer exists")

            video_path = video_asset.file_path
            audio_path = audio_asset.file_path

        # Validate files exist on disk
        if not os.path.exists(video_path):
            raise FileNotFoundError(
                f"Video file not found at {video_path}. Asset may need regeneration."
            )

        if not os.path.exists(audio_path):
            raise FileNotFoundError(
                f"Audio file not found at {audio_path}. Asset may need regeneration."
            )
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

            # Update job in database
            async with db_manager.session() as db:
                result_obj = await db.execute(
                    select(LipsyncJob).where(LipsyncJob.id == UUID(job_id))
                )
                job_update = result_obj.scalar_one_or_none()
                if job_update:
                    job_update.status = LipsyncJobStatus.COMPLETED
                    job_update.progress_percent = 100.0
                    job_update.progress_message = "Lip sync complete"
                    job_update.output_path = result.output_video_path
                    job_update.completed_at = datetime.utcnow()
                    await db.commit()
            logger.info(f"Lip sync job {job_id} completed successfully")
        else:
            # Update job failure in database
            async with db_manager.session() as db:
                result_obj = await db.execute(
                    select(LipsyncJob).where(LipsyncJob.id == UUID(job_id))
                )
                job_update = result_obj.scalar_one_or_none()
                if job_update:
                    job_update.status = LipsyncJobStatus.FAILED
                    job_update.error_message = result.error_message
                    await db.commit()
            logger.error(f"Lip sync job {job_id} failed: {result.error_message}")

    except FileNotFoundError as e:
        logger.error(f"Lip sync job {job_id} failed - file not found: {e}")
        async with db_manager.session() as db:
            result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == UUID(job_id)))
            job_update = result.scalar_one_or_none()
            if job_update:
                job_update.status = LipsyncJobStatus.FAILED
                job_update.error_message = str(e)
                await db.commit()
    except ValueError as e:
        logger.error(f"Lip sync job {job_id} failed - validation error: {e}")
        async with db_manager.session() as db:
            result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == UUID(job_id)))
            job_update = result.scalar_one_or_none()
            if job_update:
                job_update.status = LipsyncJobStatus.FAILED
                job_update.error_message = str(e)
                await db.commit()
    except Exception as e:
        logger.exception(f"Lip sync job {job_id} failed with unexpected error")
        async with db_manager.session() as db:
            result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == UUID(job_id)))
            job_update = result.scalar_one_or_none()
            if job_update:
                job_update.status = LipsyncJobStatus.FAILED
                job_update.error_message = f"Unexpected error: {str(e)}"
                await db.commit()


@router.get("/jobs", response_model=list[LipSyncJobResponse])
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """List all lip sync jobs."""
    result = await db.execute(select(LipsyncJob).order_by(LipsyncJob.created_at.desc()))
    jobs = result.scalars().all()

    return [
        {
            "job_id": str(job.id),
            "video_id": str(job.video_asset_id),
            "audio_id": str(job.audio_asset_id),
            "provider": job.provider,
            "status": job.status.value,
            "progress_percent": job.progress_percent,
            "progress_message": job.progress_message,
            "output_path": job.output_path,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=LipSyncJobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get lip sync job by ID."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(job.id),
        "video_id": str(job.video_asset_id),
        "audio_id": str(job.audio_asset_id),
        "provider": job.provider,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "progress_message": job.progress_message,
        "output_path": job.output_path,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Cancel a lip sync job."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.is_finished:
        raise HTTPException(status_code=400, detail="Job already finished")

    job.status = LipsyncJobStatus.CANCELLED
    job.error_message = "Job cancelled by user"
    await db.commit()

    return {"status": "cancelled", "job_id": job_id}


@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_providers() -> dict[str, list[dict[str, Any]]]:
    """Get list of available lip sync providers."""
    service = get_lip_sync_service()
    providers = await service.get_available_providers()

    return {"providers": providers}


# ---------------------------------------------------------------------------
# FEAT-069: Phoneme Visualization Data
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/phonemes")
async def get_phoneme_data(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get phoneme timing data for a completed lip sync job.

    Returns Preston Blair mouth shapes with timing for visualization.
    The frontend can use this to render a phoneme timeline or
    mouth shape animation preview.

    Response includes:
    - phonemes: List of {phoneme, mouth_shape, start, end, confidence}
    - metadata: Job info, duration, phoneme count
    - mouth_shapes: Reference of Preston Blair shape descriptions
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await db.execute(select(LipsyncJob).where(LipsyncJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != LipsyncJobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Phoneme data only available for completed jobs (current: {job.status.value})",
        )

    # Get lip sync service and analyze audio for phonemes
    service = get_lip_sync_service()

    try:
        # Fetch the audio asset path
        audio_result = await db.execute(select(Asset).where(Asset.id == job.audio_asset_id))
        audio_asset = audio_result.scalar_one_or_none()

        if not audio_asset or not os.path.exists(audio_asset.file_path):
            raise HTTPException(status_code=404, detail="Audio file no longer available")

        # Analyze audio for phoneme data
        analysis = await service.analyze_audio(audio_asset.file_path)

        # Build phoneme visualization data
        from scenemachine.services.lipsync import Phoneme

        # Preston Blair mouth shape descriptions for frontend rendering
        mouth_shapes = {
            "A": {"description": "Wide open mouth (AH, AA)", "svg_hint": "wide_open"},
            "B": {"description": "Closed mouth (M, B, P)", "svg_hint": "closed"},
            "C": {"description": "Open mouth, teeth showing (EH, AE)", "svg_hint": "open_teeth"},
            "D": {
                "description": "Wide mouth, teeth together (D, T, N, L)",
                "svg_hint": "wide_teeth",
            },
            "E": {"description": "Rounded mouth (OH, OO)", "svg_hint": "rounded"},
            "F": {"description": "Bottom lip under teeth (F, V)", "svg_hint": "lip_bite"},
            "G": {
                "description": "Open mouth, tongue visible (K, G, NG)",
                "svg_hint": "open_tongue",
            },
            "H": {"description": "Wide smile (EE, IY)", "svg_hint": "smile"},
            "X": {"description": "Silence / rest position", "svg_hint": "rest"},
        }

        phonemes = []
        if analysis and hasattr(analysis, "phonemes"):
            for pe in analysis.phonemes:
                phonemes.append(
                    {
                        "phoneme": pe.phoneme.value
                        if isinstance(pe.phoneme, Phoneme)
                        else str(pe.phoneme),
                        "mouth_shape": pe.phoneme.value[0]
                        if isinstance(pe.phoneme, Phoneme)
                        else "X",
                        "start": pe.start_time,
                        "end": pe.end_time,
                        "confidence": getattr(pe, "confidence", 0.9),
                    }
                )

        return {
            "job_id": job_id,
            "phoneme_count": len(phonemes),
            "duration_seconds": analysis.duration if analysis else 0,
            "phonemes": phonemes,
            "mouth_shapes": mouth_shapes,
            "provider": job.provider,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to extract phoneme data for job {job_id}")
        raise HTTPException(status_code=500, detail=f"Phoneme extraction failed: {str(e)}")


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time job progress updates.

    Polls the database for LipsyncJob row state and streams updates to the
    client every 500ms until the job reaches a terminal state. Originally
    referenced an in-memory ``_jobs`` dict that was never defined — caught
    by ruff F821 during the 2026-05-21 CI cleanup. Rewritten to use the
    LipsyncJob model that's the source of truth.
    """
    import asyncio

    await websocket.accept()
    db_manager = get_db_manager()

    try:
        # Validate job_id UUID upfront so we don't loop on a bad input.
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            await websocket.send_json({"error": f"Invalid job_id: {job_id}"})
            await websocket.close()
            return

        terminal_states = {
            LipsyncJobStatus.COMPLETED,
            LipsyncJobStatus.FAILED,
            LipsyncJobStatus.CANCELLED,
        }

        while True:
            async with db_manager.session() as session:
                stmt = select(LipsyncJob).where(LipsyncJob.id == job_uuid)
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()

            if job is None:
                await websocket.send_json({"error": "Job not found"})
                break

            await websocket.send_json(
                {
                    "type": "job_update",
                    "data": {
                        "id": str(job.id),
                        "status": job.status.value if hasattr(job.status, "value") else job.status,
                        "shot_id": str(job.shot_id) if job.shot_id else None,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "error_info": job.error_info,
                    },
                }
            )

            if job.status in terminal_states:
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception:
        logger.exception(f"WebSocket error for job {job_id}")
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
