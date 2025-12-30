"""Generation service.

Handles video generation for shots with queue management,
provider abstraction, and progress tracking.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.config import get_settings
from scenemachine.models import Character, Project, Scene, Shot
from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus
from scenemachine.models.project import ProjectState
from scenemachine.models.shot import ShotState

# WebSocket event emitters for real-time updates
from scenemachine.api.websocket import (
    emit_job_queued,
    emit_job_started,
    emit_job_progress,
    emit_job_completed,
    emit_job_failed,
    emit_queue_updated,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """Request for generating video content."""

    shot_id: UUID
    prompt: str
    negative_prompt: str = ""
    width: int = 1280
    height: int = 720
    fps: int = 24
    duration_seconds: float = 3.0
    seed: Optional[int] = None
    guidance_scale: float = 7.5
    num_inference_steps: int = 50
    character_references: List[Dict[str, Any]] = field(default_factory=list)
    style_preset: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result from a generation attempt."""

    success: bool
    output_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    duration_seconds: Optional[float] = None
    cost_usd: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationProgress:
    """Progress update for a generation job."""

    job_id: UUID
    percent: float
    message: str
    stage: str = "generating"


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    async def __call__(self, progress: GenerationProgress) -> None:
        """Called when progress updates."""
        ...


class GenerationProvider(ABC):
    """Abstract base class for generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    @abstractmethod
    def provider_type(self) -> JobProvider:
        """Provider type enum value."""
        ...

    @abstractmethod
    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Execute generation.

        Args:
            request: Generation request parameters
            progress_callback: Optional callback for progress updates

        Returns:
            GenerationResult with output or error
        """
        ...

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if provider is available."""
        ...

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running job. Returns True if cancelled."""
        return False


class MockGenerationProvider(GenerationProvider):
    """Mock provider for testing and development."""

    @property
    def name(self) -> str:
        return "Mock Provider"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.LOCAL

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Simulate generation with delays."""
        settings = get_settings()
        output_dir = settings.output_dir / "shots"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Simulate progress
        stages = [
            (0, "Initializing generation"),
            (20, "Loading models"),
            (40, "Processing prompt"),
            (60, "Generating frames"),
            (80, "Encoding video"),
            (95, "Finalizing"),
        ]

        for percent, message in stages:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=percent,
                        message=message,
                    )
                )
            await asyncio.sleep(0.5)  # Simulate work

        # Create placeholder output
        output_path = f"shots/{request.shot_id}/output.mp4"
        thumbnail_path = f"shots/{request.shot_id}/thumbnail.jpg"

        # Create directories
        shot_dir = settings.output_dir / "shots" / str(request.shot_id)
        shot_dir.mkdir(parents=True, exist_ok=True)

        # Create placeholder files for testing
        (shot_dir / "output.mp4").touch()
        (shot_dir / "thumbnail.jpg").touch()

        return GenerationResult(
            success=True,
            output_path=output_path,
            thumbnail_path=thumbnail_path,
            duration_seconds=2.0,
            cost_usd=0.0,
            metadata={
                "model": "mock",
                "seed": request.seed or 42,
                "prompt": request.prompt,
            },
        )

    async def check_availability(self) -> bool:
        return True


class ReplicateProvider(GenerationProvider):
    """Provider for Replicate.com API."""

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token
        self._client = None

    @property
    def name(self) -> str:
        return "Replicate"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.REPLICATE

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Generate using Replicate API."""
        try:
            import replicate
        except ImportError:
            return GenerationResult(
                success=False,
                error_message="Replicate package not installed",
                error_code="MISSING_DEPENDENCY",
            )

        if not self.api_token:
            return GenerationResult(
                success=False,
                error_message="Replicate API token not configured",
                error_code="MISSING_API_TOKEN",
            )

        try:
            # Use a video generation model (example: Stable Video Diffusion)
            model = "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438"

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message="Submitting to Replicate",
                    )
                )

            output = await asyncio.to_thread(
                replicate.run,
                model,
                input={
                    "prompt": request.prompt,
                    "width": request.width,
                    "height": request.height,
                    "num_frames": int(request.fps * request.duration_seconds),
                    "fps": request.fps,
                    "seed": request.seed,
                },
            )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=90,
                        message="Downloading result",
                    )
                )

            # Download and save output
            settings = get_settings()
            shot_dir = settings.output_dir / "shots" / str(request.shot_id)
            shot_dir.mkdir(parents=True, exist_ok=True)

            output_path = f"shots/{request.shot_id}/output.mp4"

            # Download the video
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(output)
                with open(shot_dir / "output.mp4", "wb") as f:
                    f.write(response.content)

            return GenerationResult(
                success=True,
                output_path=output_path,
                metadata={"model": model, "provider": "replicate"},
            )

        except Exception as e:
            logger.exception("Replicate generation failed")
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    async def check_availability(self) -> bool:
        if not self.api_token:
            return False
        try:
            import replicate

            replicate.Client(api_token=self.api_token)
            return True
        except Exception:
            return False


class FalProvider(GenerationProvider):
    """Provider for Fal.ai API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "Fal.ai"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.FAL

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Generate using Fal.ai API."""
        try:
            import fal_client
        except ImportError:
            return GenerationResult(
                success=False,
                error_message="fal-client package not installed",
                error_code="MISSING_DEPENDENCY",
            )

        if not self.api_key:
            return GenerationResult(
                success=False,
                error_message="Fal API key not configured",
                error_code="MISSING_API_TOKEN",
            )

        try:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message="Submitting to Fal.ai",
                    )
                )

            # Use video generation endpoint
            result = await asyncio.to_thread(
                fal_client.run,
                "fal-ai/fast-svd-lcm",
                arguments={
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "num_frames": int(request.fps * request.duration_seconds),
                    "fps": request.fps,
                    "seed": request.seed,
                },
            )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=90,
                        message="Processing result",
                    )
                )

            # Save output
            settings = get_settings()
            shot_dir = settings.output_dir / "shots" / str(request.shot_id)
            shot_dir.mkdir(parents=True, exist_ok=True)

            output_path = f"shots/{request.shot_id}/output.mp4"

            return GenerationResult(
                success=True,
                output_path=output_path,
                metadata={"provider": "fal"},
            )

        except Exception as e:
            logger.exception("Fal.ai generation failed")
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    async def check_availability(self) -> bool:
        return bool(self.api_key)


class GenerationService:
    """Service for managing video generation.

    Handles:
    - Queue management
    - Provider selection
    - Prompt building
    - Progress tracking
    - Result storage
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize generation service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()
        self._providers: Dict[JobProvider, GenerationProvider] = {}
        self._progress_callbacks: Dict[UUID, List[ProgressCallback]] = {}

        # Register default providers
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Register default generation providers."""
        # Always available mock provider
        self._providers[JobProvider.LOCAL] = MockGenerationProvider()

        # Replicate if configured
        # self._providers[JobProvider.REPLICATE] = ReplicateProvider()

        # Fal.ai if configured
        # self._providers[JobProvider.FAL] = FalProvider()

    def register_provider(
        self, provider_type: JobProvider, provider: GenerationProvider
    ) -> None:
        """Register a generation provider."""
        self._providers[provider_type] = provider
        logger.info(f"Registered generation provider: {provider.name}")

    def get_provider(self, provider_type: JobProvider) -> Optional[GenerationProvider]:
        """Get a registered provider."""
        return self._providers.get(provider_type)

    async def get_available_providers(self) -> List[JobProvider]:
        """Get list of available providers."""
        available = []
        for provider_type, provider in self._providers.items():
            if await provider.check_availability():
                available.append(provider_type)
        return available

    async def build_prompt(self, shot: Shot) -> tuple[str, str]:
        """Build generation prompts for a shot.

        Args:
            shot: Shot to generate prompt for

        Returns:
            Tuple of (positive_prompt, negative_prompt)
        """
        # Use stored prompts if available
        if shot.generation_prompt:
            return shot.generation_prompt, shot.negative_prompt or ""

        # Build prompt from shot specification
        parts = []

        # Shot type
        shot_type_prompts = {
            "establishing": "establishing wide shot",
            "wide": "wide shot",
            "medium": "medium shot, waist up",
            "medium_close_up": "medium close-up shot, chest up",
            "close_up": "close-up shot, face",
            "extreme_close_up": "extreme close-up, detail",
            "two_shot": "two-shot, both characters visible",
            "over_the_shoulder": "over the shoulder shot",
            "pov": "point of view shot",
        }
        parts.append(shot_type_prompts.get(shot.shot_type.value, shot.shot_type.value))

        # Camera movement
        if shot.camera_movement.value != "static":
            movement_prompts = {
                "pan": "camera panning",
                "tilt": "camera tilting",
                "dolly": "dolly movement",
                "tracking": "tracking shot",
                "handheld": "handheld camera",
                "steadicam": "smooth steadicam",
            }
            parts.append(
                movement_prompts.get(shot.camera_movement.value, shot.camera_movement.value)
            )

        # Main description
        parts.append(shot.description)

        # Action if present
        if shot.action:
            parts.append(shot.action)

        # Composition notes
        if shot.composition_notes:
            parts.append(shot.composition_notes)

        # Lighting notes
        if shot.lighting_notes:
            parts.append(shot.lighting_notes)

        positive_prompt = ", ".join(parts)

        # Standard negative prompt
        negative_prompt = (
            "blurry, low quality, distorted, deformed, disfigured, "
            "bad anatomy, watermark, text, logo, signature"
        )

        return positive_prompt, negative_prompt

    async def queue_shot(
        self,
        shot_id: UUID,
        provider: JobProvider = JobProvider.LOCAL,
        priority: int = 0,
    ) -> GenerationJob:
        """Add a shot to the generation queue.

        Args:
            shot_id: Shot UUID to generate
            provider: Provider to use
            priority: Queue priority (higher = sooner)

        Returns:
            Created GenerationJob
        """
        # Get shot with scene to get project_id
        stmt = (
            select(Shot)
            .options(selectinload(Shot.scene))
            .where(Shot.id == shot_id)
        )
        result = await self.session.execute(stmt)
        shot = result.scalar_one_or_none()

        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        # Get project_id from scene
        project_id = str(shot.scene.project_id) if shot.scene else None

        # Build prompt
        positive_prompt, negative_prompt = await self.build_prompt(shot)

        # Get attempt number
        existing_jobs = await self.session.execute(
            select(GenerationJob).where(GenerationJob.shot_id == shot_id)
        )
        attempt_count = len(existing_jobs.scalars().all())

        # Create job
        job = GenerationJob(
            shot_id=shot_id,
            job_number=attempt_count + 1,
            status=JobStatus.PENDING,
            provider=provider,
            model_id=self.settings.default_video_model,
            parameters={
                "prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "width": 1280,
                "height": 720,
                "fps": 24,
                "duration_seconds": shot.duration_seconds,
                "priority": priority,
                "project_id": project_id,
            },
            queued_at=datetime.now(timezone.utc),
        )

        self.session.add(job)

        # Update shot state
        shot.state = ShotState.QUEUED

        await self.session.commit()
        await self.session.refresh(job)

        logger.info(f"Queued shot {shot_id} for generation (job {job.id})")

        # Emit WebSocket event for real-time updates
        if project_id:
            try:
                queue_position = await self._get_queue_position(job.id)
                await emit_job_queued(
                    job_id=str(job.id),
                    shot_id=str(shot_id),
                    project_id=project_id,
                    position=queue_position,
                )

                # Also emit queue status update
                queue_stats = await self.get_queue_status(UUID(project_id))
                await emit_queue_updated(
                    project_id=project_id,
                    queue_stats=queue_stats,
                )
            except Exception as e:
                logger.warning(f"Failed to emit job queued event: {e}")

        return job

    async def _get_queue_position(self, job_id: UUID) -> int:
        """Get the position of a job in the queue."""
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.status == JobStatus.PENDING)
            .order_by(GenerationJob.queued_at)
        )
        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        for i, job in enumerate(jobs):
            if job.id == job_id:
                return i + 1
        return 0

    async def queue_scene(
        self,
        scene_id: UUID,
        provider: JobProvider = JobProvider.LOCAL,
    ) -> List[GenerationJob]:
        """Queue all shots in a scene for generation.

        Args:
            scene_id: Scene UUID
            provider: Provider to use

        Returns:
            List of created GenerationJobs
        """
        stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.id == scene_id)
        )
        result = await self.session.execute(stmt)
        scene = result.scalar_one_or_none()

        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        jobs = []
        for i, shot in enumerate(sorted(scene.shots, key=lambda s: s.sequence_number)):
            if shot.state == ShotState.PLANNED:
                job = await self.queue_shot(shot.id, provider, priority=-i)
                jobs.append(job)

        return jobs

    async def queue_project(
        self,
        project_id: UUID,
        provider: JobProvider = JobProvider.LOCAL,
    ) -> List[GenerationJob]:
        """Queue all planned shots in a project.

        Args:
            project_id: Project UUID
            provider: Provider to use

        Returns:
            List of created GenerationJobs
        """
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Update project state
        project.state = ProjectState.GENERATING

        # Get all scenes
        scenes_stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.project_id == project_id)
            .order_by(Scene.sequence_number)
        )
        scenes_result = await self.session.execute(scenes_stmt)
        scenes = scenes_result.scalars().all()

        jobs = []
        for scene in scenes:
            scene_jobs = await self.queue_scene(scene.id, provider)
            jobs.extend(scene_jobs)

        await self.session.commit()

        return jobs

    async def process_job(
        self,
        job_id: UUID,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Process a single generation job.

        Args:
            job_id: Job UUID to process
            progress_callback: Optional progress callback

        Returns:
            GenerationResult
        """
        # Get job with shot and scene (for project_id)
        stmt = (
            select(GenerationJob)
            .options(
                selectinload(GenerationJob.shot).selectinload(Shot.scene)
            )
            .where(GenerationJob.id == job_id)
        )
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Get project_id for WebSocket events
        project_id = (
            str(job.shot.scene.project_id)
            if job.shot and job.shot.scene
            else None
        )

        # Get provider
        provider = self.get_provider(job.provider)
        if not provider:
            job.status = JobStatus.FAILED
            job.error_message = f"Provider {job.provider.value} not available"
            await self.session.commit()

            # Emit failure event
            if project_id:
                try:
                    await emit_job_failed(
                        job_id=str(job_id),
                        shot_id=str(job.shot_id),
                        project_id=project_id,
                        error_message=job.error_message,
                        error_code="PROVIDER_NOT_AVAILABLE",
                        retry_count=0,
                    )
                except Exception as e:
                    logger.warning(f"Failed to emit job failed event: {e}")

            return GenerationResult(
                success=False,
                error_message=job.error_message,
                error_code="PROVIDER_NOT_AVAILABLE",
            )

        # Update job status
        job.status = JobStatus.PREPARING
        job.started_at = datetime.now(timezone.utc)
        job.shot.state = ShotState.GENERATING
        await self.session.commit()

        try:
            # Build request
            params = job.parameters
            request = GenerationRequest(
                shot_id=job.shot_id,
                prompt=params.get("prompt", ""),
                negative_prompt=params.get("negative_prompt", ""),
                width=params.get("width", 1280),
                height=params.get("height", 720),
                fps=params.get("fps", 24),
                duration_seconds=params.get("duration_seconds", 3.0),
                seed=params.get("seed"),
                guidance_scale=params.get("cfg_scale", 7.5),
                num_inference_steps=params.get("steps", 50),
            )

            # Update status to running
            job.status = JobStatus.RUNNING
            await self.session.commit()

            # Emit job started event
            if project_id:
                try:
                    await emit_job_started(
                        job_id=str(job_id),
                        shot_id=str(job.shot_id),
                        project_id=project_id,
                        provider=job.provider.value,
                    )
                except Exception as e:
                    logger.warning(f"Failed to emit job started event: {e}")

            # Wrapper for progress updates
            async def update_progress(progress: GenerationProgress) -> None:
                job.progress_percent = progress.percent
                job.progress_message = progress.message
                await self.session.commit()

                # Emit progress event via WebSocket
                if project_id:
                    try:
                        await emit_job_progress(
                            job_id=str(job_id),
                            shot_id=str(job.shot_id),
                            project_id=project_id,
                            progress=progress.percent,
                            message=progress.message,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to emit job progress event: {e}")

                if progress_callback:
                    await progress_callback(progress)

            # Execute generation
            gen_result = await provider.generate(request, update_progress)

            # Update job with result
            job.completed_at = datetime.now(timezone.utc)

            if gen_result.success:
                job.status = JobStatus.COMPLETED
                job.output_path = gen_result.output_path
                job.thumbnail_path = gen_result.thumbnail_path
                job.cost_usd = gen_result.cost_usd
                job.progress_percent = 100.0
                job.progress_message = "Complete"

                # Update shot
                job.shot.state = ShotState.GENERATED
                job.shot.output_video_path = gen_result.output_path
                job.shot.output_thumbnail_path = gen_result.thumbnail_path
                job.shot.generation_metadata = {
                    **gen_result.metadata,
                    "job_id": str(job.id),
                    "attempts": job.job_number,
                    "generation_time_seconds": gen_result.duration_seconds,
                    "cost_estimate_usd": gen_result.cost_usd,
                }

                # Emit completion event
                if project_id:
                    try:
                        await emit_job_completed(
                            job_id=str(job_id),
                            shot_id=str(job.shot_id),
                            project_id=project_id,
                            output_path=gen_result.output_path,
                            thumbnail_path=gen_result.thumbnail_path,
                            duration_seconds=gen_result.duration_seconds,
                        )

                        # Emit queue status update
                        queue_stats = await self.get_queue_status(UUID(project_id))
                        await emit_queue_updated(
                            project_id=project_id,
                            queue_stats=queue_stats,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to emit job completed event: {e}")
            else:
                job.status = JobStatus.FAILED
                job.error_message = gen_result.error_message
                job.error_code = gen_result.error_code
                job.shot.state = ShotState.FAILED

                # Emit failure event
                if project_id:
                    try:
                        await emit_job_failed(
                            job_id=str(job_id),
                            shot_id=str(job.shot_id),
                            project_id=project_id,
                            error_message=gen_result.error_message or "Generation failed",
                            error_code=gen_result.error_code,
                            retry_count=job.job_number - 1,
                        )

                        # Emit queue status update
                        queue_stats = await self.get_queue_status(UUID(project_id))
                        await emit_queue_updated(
                            project_id=project_id,
                            queue_stats=queue_stats,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to emit job failed event: {e}")

            await self.session.commit()

            logger.info(
                f"Job {job_id} {'completed' if gen_result.success else 'failed'}"
            )

            return gen_result

        except Exception as e:
            logger.exception(f"Job {job_id} failed with exception")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.error_code = "EXCEPTION"
            job.completed_at = datetime.now(timezone.utc)
            job.shot.state = ShotState.FAILED
            await self.session.commit()

            # Emit failure event for exception
            if project_id:
                try:
                    await emit_job_failed(
                        job_id=str(job_id),
                        shot_id=str(job.shot_id),
                        project_id=project_id,
                        error_message=str(e),
                        error_code="EXCEPTION",
                        retry_count=job.job_number - 1,
                    )

                    # Emit queue status update
                    queue_stats = await self.get_queue_status(UUID(project_id))
                    await emit_queue_updated(
                        project_id=project_id,
                        queue_stats=queue_stats,
                    )
                except Exception as emit_err:
                    logger.warning(f"Failed to emit job failed event: {emit_err}")

            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="EXCEPTION",
            )

    async def get_queue_status(
        self, project_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get generation queue status.

        Args:
            project_id: Optional project filter

        Returns:
            Queue status information
        """
        # Build query
        stmt = select(GenerationJob)

        if project_id:
            stmt = stmt.join(Shot).join(Scene).where(Scene.project_id == project_id)

        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = sum(1 for j in jobs if j.status == status)

        return {
            "total_jobs": len(jobs),
            "status_counts": status_counts,
            "pending": status_counts.get("pending", 0),
            "running": sum(
                1 for j in jobs if j.status in (JobStatus.PREPARING, JobStatus.RUNNING)
            ),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
        }

    async def get_pending_jobs(self, limit: int = 10) -> List[GenerationJob]:
        """Get pending jobs in queue order."""
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.status == JobStatus.PENDING)
            .order_by(GenerationJob.queued_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_job(self, job_id: UUID) -> Optional[GenerationJob]:
        """Get a job by ID."""
        stmt = (
            select(GenerationJob)
            .options(selectinload(GenerationJob.shot))
            .where(GenerationJob.id == job_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a pending or running job."""
        job = await self.get_job(job_id)

        if not job:
            return False

        if job.status not in (JobStatus.PENDING, JobStatus.PREPARING, JobStatus.RUNNING):
            return False

        # Try to cancel with provider
        if job.provider_job_id:
            provider = self.get_provider(job.provider)
            if provider:
                await provider.cancel(job.provider_job_id)

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        job.shot.state = ShotState.PLANNED

        await self.session.commit()

        logger.info(f"Cancelled job {job_id}")

        return True

    async def retry_job(self, job_id: UUID) -> Optional[GenerationJob]:
        """Retry a failed job by creating a new one."""
        old_job = await self.get_job(job_id)

        if not old_job:
            return None

        if old_job.status not in (JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT):
            return None

        # Create new job with same parameters
        new_job = await self.queue_shot(
            old_job.shot_id,
            old_job.provider,
        )

        # Copy parameters
        new_job.parameters = old_job.parameters

        await self.session.commit()
        await self.session.refresh(new_job)

        logger.info(f"Created retry job {new_job.id} for failed job {job_id}")

        return new_job

    async def approve_shot(self, shot_id: UUID) -> Shot:
        """Approve a generated shot."""
        stmt = select(Shot).where(Shot.id == shot_id)
        result = await self.session.execute(stmt)
        shot = result.scalar_one_or_none()

        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        if shot.state != ShotState.GENERATED:
            raise ValueError("Shot must be in GENERATED state to approve")

        shot.state = ShotState.APPROVED

        await self.session.commit()
        await self.session.refresh(shot)

        # Check if all shots in scene are approved
        await self._check_scene_completion(shot.scene_id)

        return shot

    async def reject_shot(
        self, shot_id: UUID, notes: Optional[str] = None
    ) -> Shot:
        """Reject a generated shot for regeneration."""
        stmt = select(Shot).where(Shot.id == shot_id)
        result = await self.session.execute(stmt)
        shot = result.scalar_one_or_none()

        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        shot.state = ShotState.REJECTED
        if notes:
            shot.user_notes = notes

        await self.session.commit()
        await self.session.refresh(shot)

        return shot

    async def _check_scene_completion(self, scene_id: UUID) -> None:
        """Check if all shots in a scene are approved."""
        stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.id == scene_id)
        )
        result = await self.session.execute(stmt)
        scene = result.scalar_one_or_none()

        if not scene:
            return

        all_approved = all(s.state == ShotState.APPROVED for s in scene.shots)

        if all_approved:
            await self._check_project_completion(scene.project_id)

    async def _check_project_completion(self, project_id: UUID) -> None:
        """Check if all shots in project are approved."""
        stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        scenes = result.scalars().all()

        all_approved = all(
            s.state == ShotState.APPROVED for scene in scenes for s in scene.shots
        )

        if all_approved:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            project = result.scalar_one_or_none()

            if project:
                project.state = ProjectState.GENERATION_COMPLETE
                await self.session.commit()
                logger.info(f"Project {project_id} generation complete")


async def get_generation_service(session: AsyncSession) -> GenerationService:
    """Factory function for GenerationService."""
    return GenerationService(session)
