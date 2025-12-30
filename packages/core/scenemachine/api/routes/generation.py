"""Generation API routes.

Handles video generation queue, job management, and progress tracking.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.models.generation_job import JobProvider, JobStatus
from scenemachine.services.generation import GenerationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generation", tags=["generation"])


# Request/Response Models
class QueueShotRequest(BaseModel):
    """Request to queue a shot for generation."""

    provider: str = "local"
    priority: int = 0


class QueueSceneRequest(BaseModel):
    """Request to queue a scene for generation."""

    provider: str = "local"


class QueueProjectRequest(BaseModel):
    """Request to queue all project shots."""

    provider: str = "local"


class JobResponse(BaseModel):
    """Generation job response."""

    id: str
    shot_id: str
    job_number: int
    status: str
    provider: str
    model_id: str
    progress_percent: Optional[float] = None
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    cost_usd: Optional[float] = None
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class QueueStatusResponse(BaseModel):
    """Queue status response."""

    total_jobs: int
    pending: int
    running: int
    completed: int
    failed: int
    status_counts: Dict[str, int]


class ProviderResponse(BaseModel):
    """Provider information response."""

    provider: str
    name: str
    available: bool


class ProviderModelResponse(BaseModel):
    """Provider model information."""

    id: str
    name: str
    cost_per_second: float
    supports_text_to_video: bool
    supports_image_to_video: bool
    max_duration: float


class ProviderHealthResponse(BaseModel):
    """Detailed provider health response."""

    provider: str
    name: str
    available: bool
    configured: bool
    models: List[ProviderModelResponse]
    default_model: Optional[str] = None
    error: Optional[str] = None


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    provider: str = "replicate"
    model_id: Optional[str] = None
    duration_seconds: float = 3.0
    shot_count: int = 1


class CostEstimateResponse(BaseModel):
    """Cost estimation response."""

    provider: str
    model_id: str
    model_name: str
    duration_seconds: float
    shot_count: int
    cost_per_shot: float
    total_cost: float
    currency: str = "USD"


class WorkerStatusResponse(BaseModel):
    """Queue worker status response."""

    started_at: str
    uptime_seconds: float
    jobs_processed: int
    jobs_succeeded: int
    jobs_failed: int
    success_rate: float
    current_job_id: Optional[str] = None
    last_job_completed_at: Optional[str] = None
    is_running: bool
    is_paused: bool


class ApproveRejectRequest(BaseModel):
    """Request to approve or reject a shot."""

    notes: Optional[str] = None


# Helper functions
def job_to_response(job) -> Dict[str, Any]:
    """Convert job model to response dict."""
    return {
        "id": str(job.id),
        "shot_id": str(job.shot_id),
        "job_number": job.job_number,
        "status": job.status.value,
        "provider": job.provider.value,
        "model_id": job.model_id,
        "progress_percent": job.progress_percent,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
        "output_path": job.output_path,
        "thumbnail_path": job.thumbnail_path,
        "cost_usd": job.cost_usd,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


# Routes
@router.get("/providers")
async def list_providers(
    session: AsyncSession = Depends(get_session),
) -> List[ProviderResponse]:
    """List available generation providers.

    Returns:
        List of providers with availability status
    """
    service = GenerationService(session)
    available = await service.get_available_providers()

    providers = []
    for provider_type in JobProvider:
        provider = service.get_provider(provider_type)
        providers.append(
            ProviderResponse(
                provider=provider_type.value,
                name=provider.name if provider else provider_type.value,
                available=provider_type in available,
            )
        )

    return providers


@router.get("/queue")
async def get_queue_status(
    project_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> QueueStatusResponse:
    """Get generation queue status.

    Args:
        project_id: Optional project filter

    Returns:
        Queue status information
    """
    pid = UUID(project_id) if project_id else None
    service = GenerationService(session)
    status = await service.get_queue_status(pid)

    return QueueStatusResponse(**status)


@router.get("/queue/pending")
async def get_pending_jobs(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> List[JobResponse]:
    """Get pending jobs in queue.

    Args:
        limit: Maximum number of jobs to return

    Returns:
        List of pending jobs
    """
    service = GenerationService(session)
    jobs = await service.get_pending_jobs(limit)

    return [job_to_response(job) for job in jobs]


@router.post("/shots/{shot_id}/queue")
async def queue_shot(
    shot_id: str,
    request: QueueShotRequest,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Queue a shot for generation.

    Args:
        shot_id: Shot UUID
        request: Queue options

    Returns:
        Created job
    """
    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    try:
        provider = JobProvider(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}",
        )

    service = GenerationService(session)

    try:
        job = await service.queue_shot(sid, provider, request.priority)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return job_to_response(job)


@router.post("/scenes/{scene_id}/queue")
async def queue_scene(
    scene_id: str,
    request: QueueSceneRequest,
    session: AsyncSession = Depends(get_session),
) -> List[JobResponse]:
    """Queue all planned shots in a scene.

    Args:
        scene_id: Scene UUID
        request: Queue options

    Returns:
        List of created jobs
    """
    try:
        sid = UUID(scene_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format",
        )

    try:
        provider = JobProvider(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}",
        )

    service = GenerationService(session)

    try:
        jobs = await service.queue_scene(sid, provider)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return [job_to_response(job) for job in jobs]


@router.post("/projects/{project_id}/queue")
async def queue_project(
    project_id: str,
    request: QueueProjectRequest,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Queue all planned shots in a project.

    Args:
        project_id: Project UUID
        request: Queue options

    Returns:
        Summary of queued jobs
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    try:
        provider = JobProvider(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}",
        )

    service = GenerationService(session)

    try:
        jobs = await service.queue_project(pid, provider)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return {
        "queued_count": len(jobs),
        "jobs": [job_to_response(job) for job in jobs],
    }


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Get a generation job by ID.

    Args:
        job_id: Job UUID

    Returns:
        Job details
    """
    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    service = GenerationService(session)
    job = await service.get_job(jid)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return job_to_response(job)


@router.post("/jobs/{job_id}/process")
async def process_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Process a pending generation job.

    This triggers the actual generation. In production, this would
    typically be handled by a background worker.

    Args:
        job_id: Job UUID

    Returns:
        Updated job
    """
    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    service = GenerationService(session)

    try:
        result = await service.process_job(jid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    job = await service.get_job(jid)
    return job_to_response(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, bool]:
    """Cancel a pending or running job.

    Args:
        job_id: Job UUID

    Returns:
        Success status
    """
    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    service = GenerationService(session)
    cancelled = await service.cancel_job(jid)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be cancelled",
        )

    return {"success": True}


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Retry a failed job.

    Args:
        job_id: Job UUID

    Returns:
        New job
    """
    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    service = GenerationService(session)
    job = await service.retry_job(jid)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be retried",
        )

    return job_to_response(job)


@router.post("/shots/{shot_id}/approve")
async def approve_shot(
    shot_id: str,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Approve a generated shot.

    Args:
        shot_id: Shot UUID

    Returns:
        Updated shot state
    """
    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    service = GenerationService(session)

    try:
        shot = await service.approve_shot(sid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "id": str(shot.id),
        "state": shot.state.value,
        "approved": True,
    }


@router.post("/shots/{shot_id}/reject")
async def reject_shot(
    shot_id: str,
    request: ApproveRejectRequest,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Reject a generated shot for regeneration.

    Args:
        shot_id: Shot UUID
        request: Optional rejection notes

    Returns:
        Updated shot state
    """
    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    service = GenerationService(session)

    try:
        shot = await service.reject_shot(sid, request.notes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "id": str(shot.id),
        "state": shot.state.value,
        "rejected": True,
    }


@router.get("/shots/{shot_id}/jobs")
async def get_shot_jobs(
    shot_id: str,
    session: AsyncSession = Depends(get_session),
) -> List[JobResponse]:
    """Get all generation jobs for a shot.

    Args:
        shot_id: Shot UUID

    Returns:
        List of jobs for the shot
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from scenemachine.models import Shot
    from scenemachine.models.generation_job import GenerationJob

    try:
        sid = UUID(shot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shot ID format",
        )

    stmt = (
        select(GenerationJob)
        .where(GenerationJob.shot_id == sid)
        .order_by(GenerationJob.created_at.desc())
    )

    result = await session.execute(stmt)
    jobs = result.scalars().all()

    return [job_to_response(job) for job in jobs]


@router.get("/providers/health")
async def get_providers_health(
    session: AsyncSession = Depends(get_session),
) -> List[ProviderHealthResponse]:
    """Get detailed health status for all providers.

    Returns detailed information including available models,
    configuration status, and any errors.

    Returns:
        List of provider health information
    """
    from scenemachine.services.generation import (
        ReplicateProvider,
        FalProvider,
        MockGenerationProvider,
    )
    from scenemachine.config import get_settings

    settings = get_settings()
    providers_health = []

    # Check Replicate provider
    replicate_configured = bool(settings.replicate_api_token)
    replicate_available = False
    replicate_error = None

    if replicate_configured:
        try:
            provider = ReplicateProvider(
                api_token=settings.replicate_api_token,
                model_id=settings.replicate_video_model,
            )
            replicate_available = await provider.check_availability()
        except Exception as e:
            replicate_error = str(e)

    providers_health.append(
        ProviderHealthResponse(
            provider="replicate",
            name="Replicate",
            available=replicate_available,
            configured=replicate_configured,
            models=[
                ProviderModelResponse(**model)
                for model in ReplicateProvider.list_models()
            ],
            default_model=settings.replicate_video_model or "minimax",
            error=replicate_error,
        )
    )

    # Check Fal.ai provider
    fal_configured = bool(settings.fal_api_key)
    fal_available = False
    fal_error = None

    if fal_configured:
        try:
            provider = FalProvider(
                api_key=settings.fal_api_key,
                model_id=settings.fal_video_model,
            )
            fal_available = await provider.check_availability()
        except Exception as e:
            fal_error = str(e)

    providers_health.append(
        ProviderHealthResponse(
            provider="fal",
            name="Fal.ai",
            available=fal_available,
            configured=fal_configured,
            models=[
                ProviderModelResponse(**model)
                for model in FalProvider.list_models()
            ],
            default_model=settings.fal_video_model or "ltx",
            error=fal_error,
        )
    )

    # Local/Mock provider (always available)
    providers_health.append(
        ProviderHealthResponse(
            provider="local",
            name="Local (Development)",
            available=True,
            configured=True,
            models=[
                ProviderModelResponse(
                    id="mock",
                    name="Mock Generator",
                    cost_per_second=0.0,
                    supports_text_to_video=True,
                    supports_image_to_video=True,
                    max_duration=10.0,
                )
            ],
            default_model="mock",
        )
    )

    return providers_health


@router.get("/providers/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
) -> List[ProviderModelResponse]:
    """Get available models for a specific provider.

    Args:
        provider_id: Provider identifier (replicate, fal, local)

    Returns:
        List of available models
    """
    from scenemachine.services.generation import ReplicateProvider, FalProvider

    if provider_id == "replicate":
        return [
            ProviderModelResponse(**model)
            for model in ReplicateProvider.list_models()
        ]
    elif provider_id == "fal":
        return [
            ProviderModelResponse(**model)
            for model in FalProvider.list_models()
        ]
    elif provider_id == "local":
        return [
            ProviderModelResponse(
                id="mock",
                name="Mock Generator",
                cost_per_second=0.0,
                supports_text_to_video=True,
                supports_image_to_video=True,
                max_duration=10.0,
            )
        ]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider_id}",
        )


@router.post("/estimate-cost")
async def estimate_cost(
    request: CostEstimateRequest,
) -> CostEstimateResponse:
    """Estimate generation cost for a given configuration.

    Args:
        request: Cost estimation parameters

    Returns:
        Estimated costs
    """
    from scenemachine.services.generation import ReplicateProvider, FalProvider

    if request.provider == "replicate":
        provider = ReplicateProvider()
        model = provider.get_model(request.model_id)
        cost_per_shot = provider.estimate_cost(
            model_id=request.model_id,
            duration_seconds=request.duration_seconds,
        )
    elif request.provider == "fal":
        provider = FalProvider()
        model = provider.get_model(request.model_id)
        cost_per_shot = provider.estimate_cost(
            model_id=request.model_id,
            duration_seconds=request.duration_seconds,
        )
    elif request.provider == "local":
        return CostEstimateResponse(
            provider="local",
            model_id="mock",
            model_name="Mock Generator",
            duration_seconds=request.duration_seconds,
            shot_count=request.shot_count,
            cost_per_shot=0.0,
            total_cost=0.0,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {request.provider}",
        )

    return CostEstimateResponse(
        provider=request.provider,
        model_id=request.model_id or provider.model_id,
        model_name=model.name,
        duration_seconds=request.duration_seconds,
        shot_count=request.shot_count,
        cost_per_shot=cost_per_shot,
        total_cost=cost_per_shot * request.shot_count,
    )


@router.get("/worker/status")
async def get_worker_status() -> WorkerStatusResponse:
    """Get queue worker status.

    Returns:
        Worker status and statistics
    """
    from scenemachine.services.queue_worker import get_queue_worker

    worker = get_queue_worker()
    stats = worker.stats.to_dict()

    return WorkerStatusResponse(**stats)


@router.post("/worker/pause")
async def pause_worker() -> Dict[str, bool]:
    """Pause the queue worker.

    Active jobs will continue, but no new jobs will be started.

    Returns:
        Success status
    """
    from scenemachine.services.queue_worker import get_queue_worker

    worker = get_queue_worker()
    worker.pause()

    return {"success": True, "paused": True}


@router.post("/worker/resume")
async def resume_worker() -> Dict[str, bool]:
    """Resume the queue worker.

    Returns:
        Success status
    """
    from scenemachine.services.queue_worker import get_queue_worker

    worker = get_queue_worker()
    worker.resume()

    return {"success": True, "paused": False}
