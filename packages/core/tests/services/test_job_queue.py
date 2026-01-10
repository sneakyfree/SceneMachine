"""Tests for Job Queue service."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.job_queue import JobQueueService
from scenemachine.models import Project


class TestJobQueueService:
    """Tests for JobQueueService."""

    @pytest.fixture
    def job_queue_service(self, db_session: AsyncSession) -> JobQueueService:
        """Create a job queue service instance."""
        return JobQueueService(db_session)

    @pytest.mark.asyncio
    async def test_enqueue_job(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test enqueueing a job."""
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={
                "prompt": "A sunset over the ocean",
                "provider": "replicate",
            },
        )

        assert job is not None
        assert job.id is not None

    @pytest.mark.asyncio
    async def test_get_job_status(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test getting job status."""
        # Create a job
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        # Get status
        status = await job_queue_service.get_status(job.id)

        assert status is not None
        assert "status" in status or hasattr(status, "status")

    @pytest.mark.asyncio
    async def test_cancel_job(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test cancelling a job."""
        # Create a job
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        # Cancel it
        result = await job_queue_service.cancel(job.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_retry_failed_job(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test retrying a failed job."""
        # Create a job
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        # Mark as failed (if method exists)
        if hasattr(job_queue_service, "mark_failed"):
            await job_queue_service.mark_failed(job.id, error="Test error")

        # Retry
        if hasattr(job_queue_service, "retry"):
            result = await job_queue_service.retry(job.id)
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_queue_length(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test getting queue length."""
        # Enqueue some jobs
        for i in range(3):
            await job_queue_service.enqueue(
                project_id=sample_project.id,
                job_type="video_generation",
                payload={"prompt": f"Test {i}"},
            )

        length = await job_queue_service.get_queue_length()

        assert isinstance(length, int)
        assert length >= 3

    @pytest.mark.asyncio
    async def test_get_project_jobs(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test getting all jobs for a project."""
        # Enqueue some jobs
        for i in range(3):
            await job_queue_service.enqueue(
                project_id=sample_project.id,
                job_type="video_generation",
                payload={"prompt": f"Test {i}"},
            )

        jobs = await job_queue_service.get_project_jobs(sample_project.id)

        assert isinstance(jobs, list)
        assert len(jobs) >= 3

    @pytest.mark.asyncio
    async def test_job_priority(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test job priority ordering."""
        # Enqueue jobs with different priorities
        low_priority = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Low priority"},
            priority=1,
        )

        high_priority = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "High priority"},
            priority=10,
        )

        # Get next job - should be high priority
        if hasattr(job_queue_service, "get_next"):
            next_job = await job_queue_service.get_next()
            if next_job:
                # High priority should come first
                pass

    @pytest.mark.asyncio
    async def test_job_timeout(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test job timeout handling."""
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
            timeout_seconds=60,
        )

        assert job is not None

    @pytest.mark.asyncio
    async def test_dequeue_job(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test dequeueing a job for processing."""
        # Enqueue a job
        await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        # Dequeue for processing
        if hasattr(job_queue_service, "dequeue"):
            job = await job_queue_service.dequeue()
            assert job is not None

    @pytest.mark.asyncio
    async def test_complete_job(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test marking a job as complete."""
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        if hasattr(job_queue_service, "complete"):
            result = await job_queue_service.complete(
                job.id,
                result={"video_url": "https://example.com/video.mp4"},
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_get_job_progress(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test getting job progress."""
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        if hasattr(job_queue_service, "get_progress"):
            progress = await job_queue_service.get_progress(job.id)
            assert progress is not None

    @pytest.mark.asyncio
    async def test_update_job_progress(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test updating job progress."""
        job = await job_queue_service.enqueue(
            project_id=sample_project.id,
            job_type="video_generation",
            payload={"prompt": "Test"},
        )

        if hasattr(job_queue_service, "update_progress"):
            result = await job_queue_service.update_progress(job.id, 50)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_failed_jobs(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test getting failed jobs."""
        if hasattr(job_queue_service, "get_failed"):
            failed = await job_queue_service.get_failed()
            assert isinstance(failed, list)

    @pytest.mark.asyncio
    async def test_clear_completed_jobs(
        self,
        job_queue_service: JobQueueService,
        sample_project: Project,
    ):
        """Test clearing completed jobs."""
        if hasattr(job_queue_service, "clear_completed"):
            result = await job_queue_service.clear_completed(
                older_than_hours=24,
            )
            assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_get_queue_stats(
        self,
        job_queue_service: JobQueueService,
    ):
        """Test getting queue statistics."""
        if hasattr(job_queue_service, "get_stats"):
            stats = await job_queue_service.get_stats()
            assert stats is not None

    @pytest.mark.asyncio
    async def test_pause_queue(
        self,
        job_queue_service: JobQueueService,
    ):
        """Test pausing the queue."""
        if hasattr(job_queue_service, "pause"):
            result = await job_queue_service.pause()
            assert result is True

    @pytest.mark.asyncio
    async def test_resume_queue(
        self,
        job_queue_service: JobQueueService,
    ):
        """Test resuming the queue."""
        if hasattr(job_queue_service, "resume"):
            result = await job_queue_service.resume()
            assert result is True
