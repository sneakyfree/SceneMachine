"""End-to-end tests for the generation pipeline.

Tests the complete flow from shot queuing through generation to approval.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project, ProjectState, Scene, Shot
from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus
from scenemachine.models.scene import SceneState
from scenemachine.models.shot import CameraMovement, ShotState, ShotType
from scenemachine.services.generation import (
    GenerationService,
    GenerationRequest,
    GenerationResult,
    MockGenerationProvider,
    ReplicateProvider,
    FalProvider,
)
from scenemachine.services.queue_worker import QueueWorker, get_queue_worker


@pytest.fixture
async def project_with_shots(db_session: AsyncSession) -> Project:
    """Create a project with scenes and shots for testing."""
    project = Project(
        name="Generation Test Project",
        description="E2E test project for generation pipeline",
        state=ProjectState.SCENES_APPROVED,
    )
    db_session.add(project)
    await db_session.flush()

    # Create scene
    scene = Scene(
        project_id=project.id,
        scene_number="1",
        sequence_number=1,
        location="LIVING ROOM",
        time_of_day="DAY",
        raw_content="INT. LIVING ROOM - DAY\n\nA bright, modern living room.",
        state=SceneState.APPROVED,
    )
    db_session.add(scene)
    await db_session.flush()

    # Create shots
    for i in range(3):
        shot = Shot(
            scene_id=scene.id,
            shot_number=str(i + 1),
            sequence_number=i,
            shot_type=ShotType.MEDIUM if i % 2 == 0 else ShotType.CLOSE_UP,
            camera_movement=CameraMovement.STATIC,
            description=f"Test shot {i + 1} description with action",
            action=f"Character performs action {i + 1}",
            duration_seconds=3.0,
            state=ShotState.PLANNED,
            generation_prompt=f"Medium shot of a character in a living room, shot {i + 1}",
        )
        db_session.add(shot)

    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestMockGeneration:
    """Tests using the mock provider for local development."""

    @pytest.mark.asyncio
    async def test_queue_single_shot(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test queuing a single shot for generation."""
        service = GenerationService(db_session)

        # Get first shot
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        # Queue the shot
        job = await service.queue_shot(shot.id, JobProvider.LOCAL)

        assert job is not None
        assert job.shot_id == shot.id
        assert job.status == JobStatus.PENDING
        assert job.provider == JobProvider.LOCAL

        # Verify shot state updated
        await db_session.refresh(shot)
        assert shot.state == ShotState.QUEUED

    @pytest.mark.asyncio
    async def test_process_job_with_mock_provider(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test processing a job with the mock provider."""
        service = GenerationService(db_session)

        # Get first shot and queue it
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        job = await service.queue_shot(shot.id, JobProvider.LOCAL)

        # Process the job
        gen_result = await service.process_job(job.id)

        assert gen_result.success is True
        assert gen_result.output_path is not None

        # Verify job updated
        await db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.output_path is not None

        # Verify shot updated
        await db_session.refresh(shot)
        assert shot.state == ShotState.GENERATED
        assert shot.output_video_path is not None

    @pytest.mark.asyncio
    async def test_queue_entire_scene(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test queuing all shots in a scene."""
        service = GenerationService(db_session)

        # Get scene
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.project_id == project_with_shots.id)
        )
        result = await db_session.execute(stmt)
        scene = result.scalars().first()

        # Queue the scene
        jobs = await service.queue_scene(scene.id, JobProvider.LOCAL)

        assert len(jobs) == 3  # All 3 shots
        assert all(j.status == JobStatus.PENDING for j in jobs)

    @pytest.mark.asyncio
    async def test_queue_entire_project(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test queuing all shots in a project."""
        service = GenerationService(db_session)

        jobs = await service.queue_project(project_with_shots.id, JobProvider.LOCAL)

        assert len(jobs) == 3
        assert all(j.provider == JobProvider.LOCAL for j in jobs)

        # Verify project state updated
        await db_session.refresh(project_with_shots)
        assert project_with_shots.state == ProjectState.GENERATING

    @pytest.mark.asyncio
    async def test_approve_generated_shot(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test approving a generated shot."""
        service = GenerationService(db_session)

        # Get shot, queue, and process
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        job = await service.queue_shot(shot.id, JobProvider.LOCAL)
        await service.process_job(job.id)

        # Approve the shot
        approved_shot = await service.approve_shot(shot.id)

        assert approved_shot.state == ShotState.APPROVED

    @pytest.mark.asyncio
    async def test_reject_generated_shot(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test rejecting a generated shot."""
        service = GenerationService(db_session)

        # Get shot, queue, and process
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        job = await service.queue_shot(shot.id, JobProvider.LOCAL)
        await service.process_job(job.id)

        # Reject with notes
        rejected_shot = await service.reject_shot(
            shot.id, notes="Lighting is too dark"
        )

        assert rejected_shot.state == ShotState.REJECTED
        assert rejected_shot.user_notes == "Lighting is too dark"

    @pytest.mark.asyncio
    async def test_retry_failed_job(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test retrying a failed job."""
        service = GenerationService(db_session)

        # Get shot and queue
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        job = await service.queue_shot(shot.id, JobProvider.LOCAL)

        # Manually mark as failed
        job.status = JobStatus.FAILED
        job.error_message = "Test failure"
        shot.state = ShotState.FAILED
        await db_session.commit()

        # Retry
        new_job = await service.retry_job(job.id)

        assert new_job is not None
        assert new_job.id != job.id
        assert new_job.shot_id == shot.id
        assert new_job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_cancel_pending_job(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test cancelling a pending job."""
        service = GenerationService(db_session)

        # Get shot and queue
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        job = await service.queue_shot(shot.id, JobProvider.LOCAL)

        # Cancel
        cancelled = await service.cancel_job(job.id)

        assert cancelled is True

        await db_session.refresh(job)
        assert job.status == JobStatus.CANCELLED

        await db_session.refresh(shot)
        assert shot.state == ShotState.PLANNED


class TestQueueStatus:
    """Tests for queue status and management."""

    @pytest.mark.asyncio
    async def test_get_queue_status(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test getting queue status."""
        service = GenerationService(db_session)

        # Queue all shots
        await service.queue_project(project_with_shots.id, JobProvider.LOCAL)

        # Get status
        status = await service.get_queue_status(project_with_shots.id)

        assert status["total_jobs"] == 3
        assert status["pending"] == 3
        assert status["running"] == 0
        assert status["completed"] == 0

    @pytest.mark.asyncio
    async def test_get_pending_jobs(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test getting pending jobs."""
        service = GenerationService(db_session)

        # Queue all shots
        await service.queue_project(project_with_shots.id, JobProvider.LOCAL)

        # Get pending
        pending = await service.get_pending_jobs(limit=10)

        assert len(pending) == 3
        assert all(j.status == JobStatus.PENDING for j in pending)


class TestProgressTracking:
    """Tests for generation progress tracking."""

    @pytest.mark.asyncio
    async def test_progress_callback(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test that progress callbacks are invoked."""
        service = GenerationService(db_session)

        # Get shot and queue
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        job = await service.queue_shot(shot.id, JobProvider.LOCAL)

        # Track progress updates
        progress_updates = []

        async def track_progress(progress):
            progress_updates.append(progress.percent)

        # Process with callback
        await service.process_job(job.id, progress_callback=track_progress)

        # Verify we got progress updates
        assert len(progress_updates) > 0
        assert max(progress_updates) >= 95  # Should reach near 100%


class TestProviders:
    """Tests for provider management."""

    @pytest.mark.asyncio
    async def test_list_available_providers(
        self, db_session: AsyncSession
    ) -> None:
        """Test listing available providers."""
        service = GenerationService(db_session)

        available = await service.get_available_providers()

        # At minimum, LOCAL should be available
        assert JobProvider.LOCAL in available

    @pytest.mark.asyncio
    async def test_replicate_provider_models(self) -> None:
        """Test listing Replicate provider models."""
        models = ReplicateProvider.list_models()

        assert len(models) > 0
        assert any(m["id"] == "minimax" for m in models)
        assert any(m["id"] == "luma" for m in models)

        # Verify model structure
        for model in models:
            assert "id" in model
            assert "name" in model
            assert "cost_per_second" in model
            assert "supports_text_to_video" in model

    @pytest.mark.asyncio
    async def test_fal_provider_models(self) -> None:
        """Test listing Fal.ai provider models."""
        models = FalProvider.list_models()

        assert len(models) > 0
        assert any(m["id"] == "ltx" for m in models)
        assert any(m["id"] == "cogvideox" for m in models)

    @pytest.mark.asyncio
    async def test_cost_estimation(self) -> None:
        """Test cost estimation for providers."""
        replicate = ReplicateProvider()
        fal = FalProvider()

        # Estimate for 3 seconds of video
        replicate_cost = replicate.estimate_cost("minimax", 3.0)
        fal_cost = fal.estimate_cost("ltx", 3.0)

        assert replicate_cost > 0
        assert fal_cost > 0

        # Verify model-specific costs
        expensive_cost = replicate.estimate_cost("luma", 3.0)
        assert expensive_cost > replicate_cost  # Luma costs more


class TestQueueWorker:
    """Tests for the queue worker."""

    @pytest.mark.asyncio
    async def test_worker_initialization(self) -> None:
        """Test worker initializes correctly."""
        worker = QueueWorker(max_concurrent=2, poll_interval=0.5)

        assert worker.max_concurrent == 2
        assert worker.poll_interval == 0.5
        assert not worker.is_running

    @pytest.mark.asyncio
    async def test_worker_stats(self) -> None:
        """Test worker statistics."""
        worker = QueueWorker()

        stats = worker.stats
        assert stats.jobs_processed == 0
        assert stats.is_running is False

        stats_dict = stats.to_dict()
        assert "uptime_seconds" in stats_dict
        assert "success_rate" in stats_dict

    @pytest.mark.asyncio
    async def test_worker_pause_resume(self) -> None:
        """Test pausing and resuming the worker."""
        worker = QueueWorker()

        worker.pause()
        assert worker.stats.is_paused is True

        worker.resume()
        assert worker.stats.is_paused is False


class TestGenerationRequest:
    """Tests for generation request building."""

    @pytest.mark.asyncio
    async def test_build_prompt_from_shot(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test building generation prompts from shot data."""
        service = GenerationService(db_session)

        # Get shot
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        # Build prompt
        positive, negative = await service.build_prompt(shot)

        assert len(positive) > 0
        assert "shot" in positive.lower() or "medium" in positive.lower()
        assert len(negative) > 0
        assert "blurry" in negative.lower()

    @pytest.mark.asyncio
    async def test_stored_prompt_used_if_available(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test that stored generation prompts are used when available."""
        service = GenerationService(db_session)

        # Get shot with stored prompt
        from sqlalchemy import select

        stmt = select(Shot).where(Shot.scene.has(project_id=project_with_shots.id))
        result = await db_session.execute(stmt)
        shot = result.scalars().first()

        # Shot has generation_prompt set in fixture
        positive, negative = await service.build_prompt(shot)

        # Should use stored prompt
        assert "living room" in positive.lower()


class TestFullPipeline:
    """Full pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_complete_generation_workflow(
        self, db_session: AsyncSession, project_with_shots: Project
    ) -> None:
        """Test the complete generation workflow from queue to approval."""
        service = GenerationService(db_session)

        # 1. Queue all project shots
        jobs = await service.queue_project(project_with_shots.id, JobProvider.LOCAL)
        assert len(jobs) == 3

        # 2. Process all jobs
        for job in jobs:
            result = await service.process_job(job.id)
            assert result.success is True

        # 3. Verify all shots generated
        await db_session.refresh(project_with_shots)

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Scene)
            .options(selectinload(Scene.shots))
            .where(Scene.project_id == project_with_shots.id)
        )
        result = await db_session.execute(stmt)
        scene = result.scalars().first()

        for shot in scene.shots:
            assert shot.state == ShotState.GENERATED
            assert shot.output_video_path is not None

        # 4. Approve all shots
        for shot in scene.shots:
            await service.approve_shot(shot.id)

        # 5. Verify all approved
        for shot in scene.shots:
            await db_session.refresh(shot)
            assert shot.state == ShotState.APPROVED

        # 6. Verify queue status
        status = await service.get_queue_status(project_with_shots.id)
        assert status["completed"] == 3
        assert status["pending"] == 0
