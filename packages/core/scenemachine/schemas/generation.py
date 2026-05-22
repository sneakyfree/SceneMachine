"""Pydantic schemas for Generation API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from scenemachine.models.generation_job import JobProvider, JobStatus

from .base import BaseSchema, TimestampSchema


class GenerationSettings(BaseSchema):
    """Settings for video generation."""

    model_id: str | None = None
    provider: JobProvider | None = None
    quality_tier: str = Field("high", pattern="^(draft|standard|high|maximum)$")
    seed: int | None = Field(None, ge=0)
    steps: int | None = Field(None, ge=1, le=150)
    cfg_scale: float | None = Field(None, ge=1.0, le=30.0)
    width: int = Field(1920, ge=256, le=4096)
    height: int = Field(1080, ge=256, le=4096)
    fps: int = Field(24, ge=12, le=60)


class GenerationStartRequest(BaseSchema):
    """Request to start generation for a project or scene."""

    project_id: UUID | None = None
    scene_ids: list[UUID] | None = None
    shot_ids: list[UUID] | None = None
    settings: GenerationSettings | None = None
    priority: int = Field(0, ge=-10, le=10, description="Higher = higher priority")


class GenerationStartResponse(BaseSchema):
    """Response after starting generation."""

    job_ids: list[UUID]
    total_shots: int
    estimated_time_seconds: float | None
    estimated_cost_usd: float | None


class JobProgress(BaseSchema):
    """Progress information for a generation job."""

    job_id: UUID
    shot_id: UUID
    status: JobStatus
    progress_percent: float | None
    progress_message: str | None
    started_at: datetime | None
    estimated_completion: datetime | None


class GenerationStatusResponse(BaseSchema):
    """Overall generation status for a project."""

    project_id: UUID
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    overall_progress_percent: float
    jobs: list[JobProgress]


class RegenerateShotRequest(BaseSchema):
    """Request to regenerate a specific shot."""

    shot_id: UUID
    prompt_override: str | None = Field(None, max_length=2000)
    negative_prompt_override: str | None = Field(None, max_length=1000)
    settings: GenerationSettings | None = None
    seed: int | None = Field(None, ge=0, description="Specific seed for reproducibility")


class GenerationJobDetail(TimestampSchema):
    """Full generation job information."""

    id: UUID
    shot_id: UUID
    job_number: int
    status: JobStatus
    provider: JobProvider
    provider_job_id: str | None
    model_id: str
    model_version: str | None
    parameters: dict[str, Any]
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    progress_percent: float | None
    progress_message: str | None
    output_path: str | None
    thumbnail_path: str | None
    error_message: str | None
    error_code: str | None
    retry_count: int
    cost_usd: float | None
    gpu_seconds: float | None
    duration_seconds: float | None
    quality_metrics: dict[str, Any] | None


class CancelGenerationRequest(BaseSchema):
    """Request to cancel generation jobs."""

    job_ids: list[UUID] | None = None
    project_id: UUID | None = None
    cancel_all_pending: bool = False


class CancelGenerationResponse(BaseSchema):
    """Response after cancelling generation."""

    cancelled_job_ids: list[UUID]
    already_completed_job_ids: list[UUID]
    failed_to_cancel_job_ids: list[UUID]


class CostEstimateRequest(BaseSchema):
    """Request for generation cost estimate."""

    project_id: UUID | None = None
    scene_ids: list[UUID] | None = None
    shot_ids: list[UUID] | None = None
    settings: GenerationSettings | None = None


class CostEstimateResponse(BaseSchema):
    """Response with cost estimate."""

    total_shots: int
    total_duration_seconds: float
    estimated_cost_usd: float
    estimated_time_seconds: float
    cost_breakdown: dict[str, float]  # By provider or category
