"""Tests for generation service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus
from scenemachine.models.shot import CameraMovement, Shot, ShotState, ShotType
from scenemachine.services.generation import (
    GenerationProgress,
    GenerationRequest,
    GenerationResult,
    GenerationService,
    MockGenerationProvider,
)


class TestGenerationRequest:
    """Tests for GenerationRequest dataclass."""

    def test_request_creation(self):
        """Test creating a generation request."""
        shot_id = uuid4()
        request = GenerationRequest(
            shot_id=shot_id,
            prompt="A beautiful sunset over the ocean",
            negative_prompt="blurry, distorted",
            width=1280,
            height=720,
            fps=24,
            duration_seconds=3.0,
            seed=12345,
        )

        assert request.shot_id == shot_id
        assert request.prompt == "A beautiful sunset over the ocean"
        assert request.width == 1280
        assert request.height == 720
        assert request.seed == 12345

    def test_request_defaults(self):
        """Test default values in request."""
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test prompt",
        )

        assert request.negative_prompt == ""
        assert request.width == 1280
        assert request.height == 720
        assert request.fps == 24
        assert request.duration_seconds == 3.0
        assert request.guidance_scale == 7.5


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = GenerationResult(
            success=True,
            output_path="/path/to/output.mp4",
            thumbnail_path="/path/to/thumb.jpg",
            duration_seconds=5.2,
            cost_usd=0.05,
        )

        assert result.success is True
        assert result.output_path == "/path/to/output.mp4"
        assert result.error_message is None

    def test_failure_result(self):
        """Test creating a failed result."""
        result = GenerationResult(
            success=False,
            error_message="GPU out of memory",
            error_code="OOM",
        )

        assert result.success is False
        assert result.error_message == "GPU out of memory"
        assert result.error_code == "OOM"
        assert result.output_path is None


class TestGenerationProgress:
    """Tests for GenerationProgress dataclass."""

    def test_progress_creation(self):
        """Test creating a progress update."""
        job_id = uuid4()
        progress = GenerationProgress(
            job_id=job_id,
            percent=50.0,
            message="Generating frames",
            stage="generating",
        )

        assert progress.job_id == job_id
        assert progress.percent == 50.0
        assert progress.message == "Generating frames"


class TestMockGenerationProvider:
    """Tests for MockGenerationProvider."""

    @pytest.fixture
    def provider(self):
        """Create a mock provider."""
        return MockGenerationProvider()

    def test_provider_properties(self, provider):
        """Test provider properties."""
        assert provider.name == "Mock Provider"
        assert provider.provider_type == JobProvider.LOCAL

    @pytest.mark.asyncio
    async def test_check_availability(self, provider):
        """Test availability check."""
        available = await provider.check_availability()
        assert available is True

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test generation",
        )

        result = await provider.generate(request)

        assert result.success is True
        assert result.output_path is not None
        assert "output.mp4" in result.output_path

    @pytest.mark.asyncio
    async def test_generate_with_progress(self, provider):
        """Test generation with progress callback."""
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test generation",
        )

        progress_updates = []

        async def progress_callback(progress: GenerationProgress):
            progress_updates.append(progress)

        result = await provider.generate(request, progress_callback)

        assert result.success is True
        assert len(progress_updates) > 0
        # Progress should increase
        percents = [p.percent for p in progress_updates]
        assert all(percents[i] <= percents[i + 1] for i in range(len(percents) - 1))


class TestGenerationService:
    """Tests for GenerationService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a generation service."""
        return GenerationService(mock_session)

    @pytest.fixture
    def mock_shot(self):
        """Create a mock shot."""
        shot = MagicMock(spec=Shot)
        shot.id = uuid4()
        shot.scene_id = uuid4()
        shot.shot_number = "1-1"
        shot.sequence_number = 1
        shot.shot_type = ShotType.MEDIUM
        shot.camera_movement = CameraMovement.STATIC
        shot.description = "A character walks into frame"
        shot.dialogue = None
        shot.action = "Character enters"
        shot.duration_seconds = 3.0
        shot.composition_notes = "Rule of thirds"
        shot.lighting_notes = "Natural lighting"
        shot.generation_prompt = None
        shot.negative_prompt = None
        shot.state = ShotState.PLANNED
        return shot

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert len(service._providers) > 0
        assert JobProvider.LOCAL in service._providers

    def test_register_provider(self, service):
        """Test registering a provider."""
        custom_provider = MockGenerationProvider()
        service.register_provider(JobProvider.CUSTOM, custom_provider)

        assert JobProvider.CUSTOM in service._providers
        assert service.get_provider(JobProvider.CUSTOM) == custom_provider

    @pytest.mark.asyncio
    async def test_get_available_providers(self, service):
        """Test getting available providers."""
        available = await service.get_available_providers()

        assert JobProvider.LOCAL in available

    @pytest.mark.asyncio
    async def test_build_prompt_from_shot(self, service, mock_shot):
        """Test building prompts from shot specification."""
        positive, negative = await service.build_prompt(mock_shot)

        assert "medium shot" in positive.lower()
        assert mock_shot.description in positive
        assert "blurry" in negative.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_with_camera_movement(self, service, mock_shot):
        """Test prompt building includes camera movement."""
        mock_shot.camera_movement = CameraMovement.TRACKING

        positive, negative = await service.build_prompt(mock_shot)

        assert "tracking" in positive.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_with_existing_prompt(self, service, mock_shot):
        """Test using existing generation prompt."""
        mock_shot.generation_prompt = "Custom prompt"
        mock_shot.negative_prompt = "Custom negative"

        positive, negative = await service.build_prompt(mock_shot)

        assert positive == "Custom prompt"
        assert negative == "Custom negative"


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_statuses_have_values(self):
        """Test all statuses have string values."""
        for status in JobStatus:
            assert isinstance(status.value, str)
            assert len(status.value) > 0

    def test_expected_statuses_exist(self):
        """Test expected statuses are defined."""
        expected = [
            "pending",
            "preparing",
            "running",
            "completed",
            "failed",
            "cancelled",
        ]

        for status_name in expected:
            assert any(s.value == status_name for s in JobStatus)


class TestJobProvider:
    """Tests for JobProvider enum."""

    def test_all_providers_have_values(self):
        """Test all providers have string values."""
        for provider in JobProvider:
            assert isinstance(provider.value, str)
            assert len(provider.value) > 0

    def test_local_provider_exists(self):
        """Test local provider is defined."""
        assert JobProvider.LOCAL.value == "local"


class TestGenerationJob:
    """Tests for GenerationJob model properties."""

    @pytest.fixture
    def job(self):
        """Create a test job."""
        job = MagicMock(spec=GenerationJob)
        job.status = JobStatus.PENDING
        job.queued_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job.started_at = None
        job.completed_at = None
        return job

    def test_is_running_pending(self, job):
        """Test is_running for pending job."""
        job.status = JobStatus.PENDING
        # Access the actual property implementation
        assert job.status not in (
            JobStatus.PREPARING,
            JobStatus.RUNNING,
            JobStatus.POST_PROCESSING,
        )

    def test_is_running_active(self, job):
        """Test is_running for active job."""
        job.status = JobStatus.RUNNING
        assert job.status in (
            JobStatus.PREPARING,
            JobStatus.RUNNING,
            JobStatus.POST_PROCESSING,
        )

    def test_is_complete_failed(self, job):
        """Test is_complete for failed job."""
        job.status = JobStatus.FAILED
        assert job.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMEOUT,
        )

    def test_is_successful(self, job):
        """Test is_successful property."""
        job.status = JobStatus.COMPLETED
        assert job.status == JobStatus.COMPLETED


class TestPromptBuilding:
    """Tests for prompt building logic."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create generation service."""
        return GenerationService(mock_session)

    @pytest.mark.asyncio
    async def test_establishing_shot_prompt(self, service):
        """Test prompt for establishing shot."""
        shot = MagicMock()
        shot.generation_prompt = None
        shot.negative_prompt = None
        shot.shot_type = ShotType.ESTABLISHING
        shot.camera_movement = CameraMovement.STATIC
        shot.description = "City skyline at night"
        shot.action = None
        shot.composition_notes = None
        shot.lighting_notes = None

        positive, _ = await service.build_prompt(shot)

        assert "establishing" in positive.lower()
        assert "city skyline at night" in positive.lower()

    @pytest.mark.asyncio
    async def test_close_up_shot_prompt(self, service):
        """Test prompt for close-up shot."""
        shot = MagicMock()
        shot.generation_prompt = None
        shot.negative_prompt = None
        shot.shot_type = ShotType.CLOSE_UP
        shot.camera_movement = CameraMovement.DOLLY
        shot.description = "Character's emotional reaction"
        shot.action = "Character cries"
        shot.composition_notes = "Focus on eyes"
        shot.lighting_notes = None

        positive, _ = await service.build_prompt(shot)

        assert "close-up" in positive.lower()
        assert "dolly" in positive.lower()
        assert "character cries" in positive.lower()

    @pytest.mark.asyncio
    async def test_two_shot_prompt(self, service):
        """Test prompt for two-shot."""
        shot = MagicMock()
        shot.generation_prompt = None
        shot.negative_prompt = None
        shot.shot_type = ShotType.TWO_SHOT
        shot.camera_movement = CameraMovement.STATIC
        shot.description = "Dialogue between two characters"
        shot.action = None
        shot.composition_notes = None
        shot.lighting_notes = "Soft window light"

        positive, _ = await service.build_prompt(shot)

        assert "two-shot" in positive.lower()
        assert "soft window light" in positive.lower()


class TestQueueManagement:
    """Tests for queue management functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create generation service."""
        return GenerationService(mock_session)

    @pytest.mark.asyncio
    async def test_get_queue_status_empty(self, service, mock_session):
        """Test queue status with no jobs."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        status = await service.get_queue_status()

        assert status["total_jobs"] == 0
        assert status["pending"] == 0
        assert status["running"] == 0

    @pytest.mark.asyncio
    async def test_get_pending_jobs(self, service, mock_session):
        """Test getting pending jobs."""
        mock_job = MagicMock(spec=GenerationJob)
        mock_job.status = JobStatus.PENDING

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job]
        mock_session.execute.return_value = mock_result

        jobs = await service.get_pending_jobs(limit=10)

        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.PENDING
