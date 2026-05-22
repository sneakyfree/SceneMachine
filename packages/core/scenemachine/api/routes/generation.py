"""Generation API routes.

Handles video generation queue, job management, and progress tracking.
"""

import logging
from datetime import UTC
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.models.generation_job import JobProvider
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
    progress_percent: float | None = None
    progress_message: str | None = None
    error_message: str | None = None
    output_path: str | None = None
    thumbnail_path: str | None = None
    cost_usd: float | None = None
    queued_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class QueueStatusResponse(BaseModel):
    """Queue status response."""

    total_jobs: int
    pending: int
    running: int
    completed: int
    failed: int
    status_counts: dict[str, int]


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
    models: list[ProviderModelResponse]
    default_model: str | None = None
    error: str | None = None


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    provider: str = "replicate"
    model_id: str | None = None
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
    current_job_id: str | None = None
    last_job_completed_at: str | None = None
    is_running: bool
    is_paused: bool


class ApproveRejectRequest(BaseModel):
    """Request to approve or reject a shot."""

    notes: str | None = None


# Helper functions
def job_to_response(job) -> dict[str, Any]:
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
) -> list[ProviderResponse]:
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
    project_id: str | None = None,
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
) -> list[JobResponse]:
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
) -> list[JobResponse]:
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
) -> dict[str, Any]:
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
        await service.process_job(jid)
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
) -> dict[str, bool]:
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


@router.get("/approval-queue")
async def get_approval_queue(
    project_id: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get shots pending HITL approval.

    FEAT-081: Returns shots that have been generated but are awaiting
    human review before being approved for final assembly.

    Args:
        project_id: Optional project filter
        limit: Maximum results (default 50)

    Returns:
        List of shots awaiting approval with generation details
    """
    from scenemachine.models import Scene, Shot
    from scenemachine.models.generation import GenerationJob

    # Build query for shots in "generated" state (pending review)
    stmt = (
        select(Shot)
        .where(Shot.state.in_(["generated", "pending_review", "review"]))
        .order_by(Shot.updated_at.desc())
        .limit(limit)
    )

    if project_id:
        try:
            pid = UUID(project_id)
            stmt = stmt.join(Scene).where(Scene.project_id == pid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID format",
            )

    result = await session.execute(stmt)
    shots = result.scalars().all()

    queue_items = []
    for shot in shots:
        # Get latest generation job for this shot
        job_stmt = (
            select(GenerationJob)
            .where(GenerationJob.shot_id == shot.id)
            .order_by(GenerationJob.created_at.desc())
            .limit(1)
        )
        job_result = await session.execute(job_stmt)
        latest_job = job_result.scalar_one_or_none()

        queue_items.append({
            "shot_id": str(shot.id),
            "shot_title": getattr(shot, "title", f"Shot {getattr(shot, 'order', '?')}"),
            "scene_id": str(shot.scene_id) if shot.scene_id else None,
            "state": shot.state.value if hasattr(shot.state, "value") else str(shot.state),
            "thumbnail_path": latest_job.thumbnail_path if latest_job else None,
            "output_path": latest_job.output_path if latest_job else None,
            "provider": latest_job.provider if latest_job else None,
            "generated_at": latest_job.completed_at.isoformat() if latest_job and latest_job.completed_at else None,
            "cost_usd": latest_job.cost_usd if latest_job else None,
        })

    return {
        "total": len(queue_items),
        "items": queue_items,
    }


@router.post("/shots/{shot_id}/approve")
async def approve_shot(
    shot_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> list[JobResponse]:
    """Get all generation jobs for a shot.

    Args:
        shot_id: Shot UUID

    Returns:
        List of jobs for the shot
    """
    from sqlalchemy import select

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
) -> list[ProviderHealthResponse]:
    """Get detailed health status for all providers.

    Returns detailed information including available models,
    configuration status, and any errors.

    Returns:
        List of provider health information
    """
    from scenemachine.generators.base import get_provider_registry

    registry = get_provider_registry()
    providers_health = []

    for provider_type in registry.list_providers():
        provider = registry.get_provider(provider_type)
        if not provider:
            providers_health.append(
                ProviderHealthResponse(
                    provider=provider_type.value,
                    name=provider_type.value,
                    available=False,
                    configured=False,
                    models=[],
                    error="Failed to instantiate provider",
                )
            )
            continue

        # Check availability
        available = False
        error = None
        try:
            available = await provider.check_availability()
        except Exception as e:
            error = str(e)

        # Get models
        models = []
        try:
            raw_models = provider.list_models()
            for m in raw_models:
                if isinstance(m, dict):
                    models.append(ProviderModelResponse(
                        id=m.get("id", "unknown"),
                        name=m.get("name", "Unknown"),
                        cost_per_second=m.get("cost_per_second", 0.0),
                        supports_text_to_video=m.get("supports_text_to_video", True),
                        supports_image_to_video=m.get("supports_image_to_video", False),
                        max_duration=m.get("max_duration", 10.0),
                    ))
        except Exception:
            pass

        providers_health.append(
            ProviderHealthResponse(
                provider=provider_type.value,
                name=provider.name,
                available=available,
                configured=True,
                models=models,
                error=error,
            )
        )

    return providers_health


@router.get("/providers/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
) -> list[ProviderModelResponse]:
    """Get available models for a specific provider.

    Args:
        provider_id: Provider identifier (replicate, fal, local, comfyui, runpod, actcore)

    Returns:
        List of available models
    """
    from scenemachine.generators.base import get_provider_registry
    from scenemachine.models.generation_job import JobProvider

    registry = get_provider_registry()

    # Map provider_id string to JobProvider enum
    try:
        provider_type = JobProvider(provider_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider_id}. Available: {[p.value for p in registry.list_providers()]}",
        )

    provider = registry.get_provider(provider_type)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_id} not registered",
        )

    models = []
    try:
        raw_models = provider.list_models()
        for m in raw_models:
            if isinstance(m, dict):
                models.append(ProviderModelResponse(
                    id=m.get("id", "unknown"),
                    name=m.get("name", "Unknown"),
                    cost_per_second=m.get("cost_per_second", 0.0),
                    supports_text_to_video=m.get("supports_text_to_video", True),
                    supports_image_to_video=m.get("supports_image_to_video", False),
                    max_duration=m.get("max_duration", 10.0),
                ))
    except Exception as e:
        logger.warning(f"Failed to list models for {provider_id}: {e}")

    return models


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
    from scenemachine.services.generation import FalProvider, ReplicateProvider

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
async def pause_worker() -> dict[str, bool]:
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
async def resume_worker() -> dict[str, bool]:
    """Resume the queue worker.

    Returns:
        Success status
    """
    from scenemachine.services.queue_worker import get_queue_worker

    worker = get_queue_worker()
    worker.resume()

    return {"success": True, "paused": False}


# ---- Quality Review ----

class QualityDimensionScoreResponse(BaseModel):
    """Score for a single quality dimension."""
    dimension: str
    score: float
    confidence: float
    weight: float
    issues: list[str] = []
    notes: str = ""


class QualityReviewResponse(BaseModel):
    """Full quality review result for a generation job."""
    job_id: str
    overall_score: float
    passed: bool
    dimensions: list[QualityDimensionScoreResponse]
    requires_escalation: bool = False
    escalation_reason: str | None = None
    recommendations: list[str] = []
    reviewed_at: str | None = None


@router.get("/jobs/{job_id}/quality-review")
async def get_job_quality_review(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> QualityReviewResponse:
    """Get quality review scores for a completed generation job.

    Returns per-dimension quality scores (8 axes), overall score,
    pass/fail verdict, and any escalation info.

    Args:
        job_id: Job UUID

    Returns:
        Quality review with dimensional breakdown
    """
    from scenemachine.services.video_quality_reviewer import get_video_quality_reviewer

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

    # Run quality review on the output video
    reviewer = get_video_quality_reviewer()
    output_path = getattr(job, "output_path", None)

    if not output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job has no output video to review",
        )

    result = await reviewer.review_video(output_path)

    # Map dimension weights for response
    weight_map = reviewer.DIMENSION_WEIGHTS
    from datetime import datetime

    dimensions = []
    for ds in result.dimension_scores:
        dimensions.append(QualityDimensionScoreResponse(
            dimension=ds.dimension.value,
            score=round(ds.score, 3),
            confidence=round(ds.confidence, 3),
            weight=weight_map.get(ds.dimension, 0.1),
            issues=[i.value for i in ds.issues],
            notes=ds.notes,
        ))

    return QualityReviewResponse(
        job_id=job_id,
        overall_score=round(result.overall_score, 3),
        passed=result.passed,
        dimensions=dimensions,
        requires_escalation=result.requires_escalation,
        escalation_reason=result.escalation_reason.value if result.escalation_reason else None,
        recommendations=result.recommendations,
        reviewed_at=datetime.now(UTC).isoformat(),
    )


# ---- IP-Adapter Settings ----

class IPAdapterSettingsResponse(BaseModel):
    """IP-Adapter character consistency settings."""
    mode: str = "balanced"
    strength: float = 0.6
    available_modes: list[str] = ["balanced", "strong", "face_only"]


class IPAdapterSettingsRequest(BaseModel):
    """Request to update IP-Adapter settings."""
    mode: str | None = None
    strength: float | None = None


# In-memory settings store (would be per-project in production)
_ip_adapter_settings: dict[str, Any] = {
    "mode": "balanced",
    "strength": 0.6,
}


@router.get("/settings/ip-adapter")
async def get_ip_adapter_settings() -> IPAdapterSettingsResponse:
    """Get current IP-Adapter character consistency settings.

    Returns:
        Current mode, strength, and available modes
    """
    return IPAdapterSettingsResponse(
        mode=_ip_adapter_settings["mode"],
        strength=_ip_adapter_settings["strength"],
    )


@router.put("/settings/ip-adapter")
async def update_ip_adapter_settings(
    request: IPAdapterSettingsRequest,
) -> IPAdapterSettingsResponse:
    """Update IP-Adapter character consistency settings.

    Args:
        request: New mode and/or strength values

    Returns:
        Updated settings
    """
    valid_modes = ["balanced", "strong", "face_only"]

    if request.mode is not None:
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode: {request.mode}. Must be one of {valid_modes}",
            )
        _ip_adapter_settings["mode"] = request.mode

    if request.strength is not None:
        if not 0.0 <= request.strength <= 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strength must be between 0.0 and 1.0",
            )
        _ip_adapter_settings["strength"] = request.strength

    return IPAdapterSettingsResponse(
        mode=_ip_adapter_settings["mode"],
        strength=_ip_adapter_settings["strength"],
    )
