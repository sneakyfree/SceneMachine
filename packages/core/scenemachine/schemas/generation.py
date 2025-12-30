"""Pydantic schemas for Generation API endpoints."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import Field

from scenemachine.models.generation_job import JobProvider, JobStatus

from .base import BaseSchema, TimestampSchema


class GenerationSettings(BaseSchema):
    """Settings for video generation."""

    model_id: Optional[str] = None
    provider: Optional[JobProvider] = None
    quality_tier: str = Field("high", pattern="^(draft|standard|high|maximum)$")
    seed: Optional[int] = Field(None, ge=0)
    steps: Optional[int] = Field(None, ge=1, le=150)
    cfg_scale: Optional[float] = Field(None, ge=1.0, le=30.0)
    width: int = Field(1920, ge=256, le=4096)
    height: int = Field(1080, ge=256, le=4096)
    fps: int = Field(24, ge=12, le=60)


class GenerationStartRequest(BaseSchema):
    """Request to start generation for a project or scene."""

    project_id: Optional[UUID] = None
    scene_ids: Optional[List[UUID]] = None
    shot_ids: Optional[List[UUID]] = None
    settings: Optional[GenerationSettings] = None
    priority: int = Field(0, ge=-10, le=10, description="Higher = higher priority")


class GenerationStartResponse(BaseSchema):
    """Response after starting generation."""

    job_ids: List[UUID]
    total_shots: int
    estimated_time_seconds: Optional[float]
    estimated_cost_usd: Optional[float]


class JobProgress(BaseSchema):
    """Progress information for a generation job."""

    job_id: UUID
    shot_id: UUID
    status: JobStatus
    progress_percent: Optional[float]
    progress_message: Optional[str]
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]


class GenerationStatusResponse(BaseSchema):
    """Overall generation status for a project."""

    project_id: UUID
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    overall_progress_percent: float
    jobs: List[JobProgress]


class RegenerateShotRequest(BaseSchema):
    """Request to regenerate a specific shot."""

    shot_id: UUID
    prompt_override: Optional[str] = Field(None, max_length=2000)
    negative_prompt_override: Optional[str] = Field(None, max_length=1000)
    settings: Optional[GenerationSettings] = None
    seed: Optional[int] = Field(None, ge=0, description="Specific seed for reproducibility")


class GenerationJobDetail(TimestampSchema):
    """Full generation job information."""

    id: UUID
    shot_id: UUID
    job_number: int
    status: JobStatus
    provider: JobProvider
    provider_job_id: Optional[str]
    model_id: str
    model_version: Optional[str]
    parameters: dict[str, Any]
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_percent: Optional[float]
    progress_message: Optional[str]
    output_path: Optional[str]
    thumbnail_path: Optional[str]
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    cost_usd: Optional[float]
    gpu_seconds: Optional[float]
    duration_seconds: Optional[float]
    quality_metrics: Optional[dict[str, Any]]


class CancelGenerationRequest(BaseSchema):
    """Request to cancel generation jobs."""

    job_ids: Optional[List[UUID]] = None
    project_id: Optional[UUID] = None
    cancel_all_pending: bool = False


class CancelGenerationResponse(BaseSchema):
    """Response after cancelling generation."""

    cancelled_job_ids: List[UUID]
    already_completed_job_ids: List[UUID]
    failed_to_cancel_job_ids: List[UUID]


class CostEstimateRequest(BaseSchema):
    """Request for generation cost estimate."""

    project_id: Optional[UUID] = None
    scene_ids: Optional[List[UUID]] = None
    shot_ids: Optional[List[UUID]] = None
    settings: Optional[GenerationSettings] = None


class CostEstimateResponse(BaseSchema):
    """Response with cost estimate."""

    total_shots: int
    total_duration_seconds: float
    estimated_cost_usd: float
    estimated_time_seconds: float
    cost_breakdown: dict[str, float]  # By provider or category
