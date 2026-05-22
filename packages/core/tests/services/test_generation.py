"""Tests for GenerationService and providers."""

from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project, Scene, Shot
from scenemachine.models.generation_job import JobProvider, JobStatus
from scenemachine.models.shot import CameraMovement, ShotState, ShotType
from scenemachine.services.generation import (
    FalProvider,
    GenerationProgress,
    GenerationRequest,
    GenerationResult,
    GenerationService,
    MockGenerationProvider,
    ReplicateProvider,
    VideoModel,
)


class TestVideoModel:
    """Test suite for VideoModel dataclass."""

    def test_video_model_creation(self):
        """Test creating a VideoModel."""
        model = VideoModel(
            id="test/model",
            name="Test Model",
            version="abc123",
            cost_per_second=0.05,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=5.0,
            default_fps=24,
        )
        assert model.id == "test/model"
        assert model.cost_per_second == 0.05
        assert model.max_duration == 5.0

    def test_video_model_defaults(self):
        """Test VideoModel default values."""
        model = VideoModel(
            id="test/model",
            name="Test",
            version="1.0",
            cost_per_second=0.01,
        )
        assert model.supports_text_to_video is True
        assert model.supports_image_to_video is False
        assert model.max_duration == 4.0
        assert model.default_fps == 24


class TestGenerationRequest:
    """Test suite for GenerationRequest dataclass."""

    def test_request_creation(self):
        """Test creating a GenerationRequest."""
        shot_id = uuid4()
        request = GenerationRequest(
            shot_id=shot_id,
            prompt="A cinematic establishing shot",
            negative_prompt="blurry, low quality",
            width=1920,
            height=1080,
            fps=30,
            duration_seconds=4.0,
        )
        assert request.shot_id == shot_id
        assert request.width == 1920
        assert request.fps == 30

    def test_request_defaults(self):
        """Test GenerationRequest default values."""
        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Test prompt",
        )
        assert request.width == 1280
        assert request.height == 720
        assert request.fps == 24
        assert request.duration_seconds == 3.0
        assert request.guidance_scale == 7.5


class TestGenerationResult:
    """Test suite for GenerationResult dataclass."""

    def test_successful_result(self):
        """Test successful generation result."""
        result = GenerationResult(
            success=True,
            output_path="shots/123/output.mp4",
            thumbnail_path="shots/123/thumbnail.jpg",
            duration_seconds=45.5,
            cost_usd=0.15,
        )
        assert result.success is True
        assert result.output_path == "shots/123/output.mp4"
        assert result.cost_usd == 0.15

    def test_failed_result(self):
        """Test failed generation result."""
        result = GenerationResult(
            success=False,
            error_message="API timeout",
            error_code="TIMEOUT",
        )
        assert result.success is False
        assert result.error_code == "TIMEOUT"


class TestMockGenerationProvider:
    """Test suite for MockGenerationProvider."""

    @pytest.fixture
    def mock_provider(self):
        return MockGenerationProvider()

    async def test_provider_properties(self, mock_provider):
        """Test provider name and type."""
        assert mock_provider.name == "Mock Provider"
        assert mock_provider.provider_type == JobProvider.LOCAL

    async def test_check_availability(self, mock_provider):
        """Test availability check always returns True."""
        assert await mock_provider.check_availability() is True

    async def test_generate_success(self, mock_provider, tmp_path):
        """Test successful mock generation."""
        with patch("scenemachine.services.generation.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            request = GenerationRequest(
                shot_id=uuid4(),
                prompt="Test cinematic shot",
            )

            result = await mock_provider.generate(request)

            assert result.success is True
            assert result.output_path is not None
            assert result.cost_usd == 0.0

    async def test_generate_with_progress_callback(self, mock_provider, tmp_path):
        """Test generation with progress callback."""
        with patch("scenemachine.services.generation.get_settings") as mock_settings:
            mock_settings.return_value.output_dir = tmp_path

            progress_updates = []

            async def progress_callback(progress: GenerationProgress):
                progress_updates.append(progress)

            request = GenerationRequest(
                shot_id=uuid4(),
                prompt="Test prompt",
            )

            await mock_provider.generate(request, progress_callback)

            assert len(progress_updates) > 0
            # Check progress increases
            percents = [p.percent for p in progress_updates]
            assert percents == sorted(percents)


class TestReplicateProvider:
    """Test suite for ReplicateProvider."""

    def test_available_models(self):
        """Test that models are defined."""
        assert "svd" in ReplicateProvider.MODELS
        assert "minimax" in ReplicateProvider.MODELS
        assert "luma" in ReplicateProvider.MODELS
        assert "kling" in ReplicateProvider.MODELS

    def test_list_models(self):
        """Test listing available models."""
        models = ReplicateProvider.list_models()
        assert len(models) > 0
        for model in models:
            assert "id" in model
            assert "name" in model
            assert "cost_per_second" in model

    def test_get_model_valid(self):
        """Test getting a valid model."""
        provider = ReplicateProvider(api_token="test-token")
        model = provider.get_model("minimax")
        assert model.name == "MiniMax Video-01"

    def test_get_model_invalid(self):
        """Test getting an invalid model."""
        provider = ReplicateProvider(api_token="test-token")
        with pytest.raises(ValueError, match="Unknown model"):
            provider.get_model("nonexistent")

    def test_estimate_cost(self):
        """Test cost estimation."""
        provider = ReplicateProvider(api_token="test-token", model_id="minimax")
        cost = provider.estimate_cost(duration_seconds=5.0)
        # minimax is $0.08/sec, so 5 seconds = $0.40
        assert cost == 0.40

    def test_provider_type(self):
        """Test provider type."""
        provider = ReplicateProvider()
        assert provider.provider_type == JobProvider.REPLICATE
        assert provider.name == "Replicate"

    async def test_generate_no_api_token(self):
        """Test generation without API token."""
        provider = ReplicateProvider(api_token=None)
        request = GenerationRequest(shot_id=uuid4(), prompt="Test")

        result = await provider.generate(request)

        assert result.success is False
        assert result.error_code == "MISSING_API_TOKEN"

    async def test_generate_missing_dependency(self):
        """Test generation with missing replicate package."""
        provider = ReplicateProvider(api_token="test-token")
        request = GenerationRequest(shot_id=uuid4(), prompt="Test")

        with patch.dict("sys.modules", {"replicate": None}):
            # Force import error
            with patch("builtins.__import__", side_effect=ImportError("No module named 'replicate'")):
                await provider.generate(request)
                # Note: This test structure may need adjustment based on actual import handling
                # The provider should handle ImportError gracefully

    async def test_check_availability_no_token(self):
        """Test availability without token."""
        provider = ReplicateProvider(api_token=None)
        assert await provider.check_availability() is False

    def test_aspect_ratio_calculation(self):
        """Test aspect ratio string generation."""
        provider = ReplicateProvider(api_token="test")

        assert provider._get_aspect_ratio(1920, 1080) == "16:9"
        assert provider._get_aspect_ratio(1080, 1920) == "9:16"
        assert provider._get_aspect_ratio(1080, 1080) == "1:1"
        assert provider._get_aspect_ratio(1440, 1080) == "4:3"

    def test_build_input_params_text_to_video(self):
        """Test building input parameters for text-to-video model."""
        provider = ReplicateProvider(api_token="test")
        model = provider.get_model("minimax")

        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="A beautiful sunset",
            negative_prompt="ugly, blurry",
            seed=12345,
        )

        params = provider._build_input_params(request, model)

        assert params["prompt"] == "A beautiful sunset"
        assert params["negative_prompt"] == "ugly, blurry"
        assert params["seed"] == 12345

    def test_build_input_params_image_to_video(self):
        """Test building input parameters for image-to-video model (SVD)."""
        provider = ReplicateProvider(api_token="test")
        model = provider.get_model("svd")

        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="Motion effect",
            character_references=[{"image_url": "https://example.com/image.jpg"}],
            duration_seconds=3.0,
        )

        params = provider._build_input_params(request, model)

        # SVD doesn't support text-to-video, so prompt shouldn't be in params
        assert "prompt" not in params
        assert params["input_image"] == "https://example.com/image.jpg"
        assert params["motion_bucket_id"] == 127


class TestFalProvider:
    """Test suite for FalProvider."""

    def test_available_models(self):
        """Test that models are defined."""
        assert "fast-svd" in FalProvider.MODELS
        assert "cogvideox" in FalProvider.MODELS
        assert "hunyuan" in FalProvider.MODELS
        assert "ltx" in FalProvider.MODELS

    def test_list_models(self):
        """Test listing available models."""
        models = FalProvider.list_models()
        assert len(models) > 0
        for model in models:
            assert "id" in model
            assert "name" in model
            assert "cost_per_second" in model

    def test_get_model_valid(self):
        """Test getting a valid model."""
        provider = FalProvider(api_key="test-key")
        model = provider.get_model("ltx")
        assert model.name == "LTX Video"

    def test_estimate_cost(self):
        """Test cost estimation."""
        provider = FalProvider(api_key="test-key", model_id="ltx")
        cost = provider.estimate_cost(duration_seconds=5.0)
        # ltx is $0.04/sec, so 5 seconds = $0.20
        assert cost == 0.20

    def test_provider_type(self):
        """Test provider type."""
        provider = FalProvider()
        assert provider.provider_type == JobProvider.FAL
        assert provider.name == "Fal.ai"

    async def test_generate_no_api_key(self):
        """Test generation without API key."""
        provider = FalProvider(api_key=None)
        request = GenerationRequest(shot_id=uuid4(), prompt="Test")

        result = await provider.generate(request)

        assert result.success is False
        assert result.error_code == "MISSING_API_TOKEN"

    async def test_check_availability_no_key(self):
        """Test availability without key."""
        provider = FalProvider(api_key=None)
        assert await provider.check_availability() is False

    def test_build_arguments_text_to_video(self):
        """Test building arguments for text-to-video model."""
        provider = FalProvider(api_key="test")
        model = provider.get_model("ltx")

        request = GenerationRequest(
            shot_id=uuid4(),
            prompt="A serene landscape",
            negative_prompt="dark, gloomy",
            seed=42,
            duration_seconds=4.0,
        )

        args = provider._build_arguments(request, model)

        assert args["prompt"] == "A serene landscape"
        assert args["negative_prompt"] == "dark, gloomy"
        assert args["seed"] == 42

    def test_extract_video_url_dict(self):
        """Test extracting video URL from dict result."""
        provider = FalProvider(api_key="test")

        # Test video dict
        result = {"video": {"url": "https://example.com/video.mp4"}}
        assert provider._extract_video_url(result) == "https://example.com/video.mp4"

        # Test direct video string
        result = {"video": "https://example.com/video.mp4"}
        assert provider._extract_video_url(result) == "https://example.com/video.mp4"

        # Test output dict
        result = {"output": {"url": "https://example.com/video.mp4"}}
        assert provider._extract_video_url(result) == "https://example.com/video.mp4"

        # Test url field
        result = {"url": "https://example.com/video.mp4"}
        assert provider._extract_video_url(result) == "https://example.com/video.mp4"

        # Test empty result
        result = {}
        assert provider._extract_video_url(result) is None


@pytest_asyncio.fixture
async def sample_scene(db_session: AsyncSession, sample_project: Project) -> Scene:
    """Create a sample scene for testing."""
    from scenemachine.models.scene import SceneType, TimeOfDay

    scene = Scene(
        project_id=sample_project.id,
        scene_number="1",
        sequence_number=1,
        scene_type=SceneType.INTERIOR,
        location="OFFICE",
        time_of_day=TimeOfDay.DAY,
        raw_content="INT. OFFICE - DAY\n\nA wide shot of the office.",
    )
    db_session.add(scene)
    await db_session.commit()
    await db_session.refresh(scene)
    return scene


@pytest_asyncio.fixture
async def sample_shot(db_session: AsyncSession, sample_scene: Scene) -> Shot:
    """Create a sample shot for testing."""
    shot = Shot(
        scene_id=sample_scene.id,
        shot_number="1",
        sequence_number=1,
        shot_type=ShotType.ESTABLISHING,
        camera_movement=CameraMovement.STATIC,
        description="Wide establishing shot of office",
        duration_seconds=3.0,
        state=ShotState.PLANNED,
    )
    db_session.add(shot)
    await db_session.commit()
    await db_session.refresh(shot)
    return shot


class TestGenerationService:
    """Test suite for GenerationService."""

    @pytest_asyncio.fixture
    async def generation_service(self, db_session: AsyncSession) -> GenerationService:
        """Create GenerationService instance."""
        return GenerationService(db_session)

    async def test_service_initialization(self, generation_service):
        """Test service initializes with default providers."""
        assert JobProvider.LOCAL in generation_service._providers
        mock_provider = generation_service.get_provider(JobProvider.LOCAL)
        assert isinstance(mock_provider, MockGenerationProvider)

    async def test_register_provider(self, generation_service):
        """Test registering a custom provider."""
        mock_provider = MockGenerationProvider()
        generation_service.register_provider(JobProvider.LOCAL, mock_provider)

        retrieved = generation_service.get_provider(JobProvider.LOCAL)
        assert retrieved is mock_provider

    async def test_get_available_providers(self, generation_service):
        """Test getting available providers."""
        providers = await generation_service.get_available_providers()

        assert JobProvider.LOCAL in providers

    async def test_build_prompt_from_shot(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
    ):
        """Test building prompt from shot data."""
        positive, negative = await generation_service.build_prompt(sample_shot)

        assert "establishing wide shot" in positive
        assert len(negative) > 0

    async def test_build_prompt_with_stored_prompt(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test using stored prompts."""
        sample_shot.generation_prompt = "Custom prompt"
        sample_shot.negative_prompt = "Custom negative"
        await db_session.commit()

        positive, negative = await generation_service.build_prompt(sample_shot)

        assert positive == "Custom prompt"
        assert negative == "Custom negative"

    async def test_queue_shot(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test queuing a shot for generation."""
        with patch("scenemachine.services.generation.emit_job_queued"):
            with patch("scenemachine.services.generation.emit_queue_updated"):
                job = await generation_service.queue_shot(sample_shot.id)

        assert job is not None
        assert job.shot_id == sample_shot.id
        assert job.status == JobStatus.PENDING
        assert job.provider == JobProvider.LOCAL

    async def test_queue_shot_not_found(self, generation_service: GenerationService):
        """Test queuing non-existent shot."""
        with pytest.raises(ValueError, match="not found"):
            await generation_service.queue_shot(uuid4())

    async def test_get_queue_status(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
    ):
        """Test getting queue status."""
        with patch("scenemachine.services.generation.emit_job_queued"):
            with patch("scenemachine.services.generation.emit_queue_updated"):
                await generation_service.queue_shot(sample_shot.id)

        status = await generation_service.get_queue_status()

        assert "total_jobs" in status
        assert status["total_jobs"] >= 1
        assert "pending" in status

    async def test_cancel_job(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test cancelling a pending job."""
        with patch("scenemachine.services.generation.emit_job_queued"):
            with patch("scenemachine.services.generation.emit_queue_updated"):
                job = await generation_service.queue_shot(sample_shot.id)

        cancelled = await generation_service.cancel_job(job.id)

        assert cancelled is True
        await db_session.refresh(job)
        assert job.status == JobStatus.CANCELLED

    async def test_cancel_job_not_found(self, generation_service: GenerationService):
        """Test cancelling non-existent job."""
        cancelled = await generation_service.cancel_job(uuid4())
        assert cancelled is False

    async def test_retry_job(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test retrying a failed job."""
        with patch("scenemachine.services.generation.emit_job_queued"):
            with patch("scenemachine.services.generation.emit_queue_updated"):
                job = await generation_service.queue_shot(sample_shot.id)

        # Mark as failed
        job.status = JobStatus.FAILED
        await db_session.commit()

        with patch("scenemachine.services.generation.emit_job_queued"):
            with patch("scenemachine.services.generation.emit_queue_updated"):
                new_job = await generation_service.retry_job(job.id)

        assert new_job is not None
        assert new_job.id != job.id
        assert new_job.shot_id == job.shot_id
        assert new_job.status == JobStatus.PENDING

    async def test_approve_shot(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test approving a generated shot."""
        # Set shot to generated state
        sample_shot.state = ShotState.GENERATED
        await db_session.commit()

        shot = await generation_service.approve_shot(sample_shot.id)

        assert shot.state == ShotState.APPROVED

    async def test_approve_shot_wrong_state(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
    ):
        """Test approving shot in wrong state."""
        with pytest.raises(ValueError, match="must be in GENERATED state"):
            await generation_service.approve_shot(sample_shot.id)

    async def test_reject_shot(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test rejecting a generated shot."""
        sample_shot.state = ShotState.GENERATED
        await db_session.commit()

        shot = await generation_service.reject_shot(sample_shot.id, notes="Too dark")

        assert shot.state == ShotState.REJECTED
        assert shot.user_notes == "Too dark"


class TestPromptBuilding:
    """Test suite for prompt building functionality."""

    @pytest_asyncio.fixture
    async def generation_service(self, db_session: AsyncSession) -> GenerationService:
        return GenerationService(db_session)

    async def test_prompt_includes_shot_type(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
    ):
        """Test that shot type is included in prompt."""
        positive, _ = await generation_service.build_prompt(sample_shot)
        assert "establishing" in positive.lower()

    async def test_prompt_includes_camera_movement(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
        db_session: AsyncSession,
    ):
        """Test camera movement is included for non-static shots."""
        sample_shot.camera_movement = CameraMovement.TRACKING
        await db_session.commit()

        positive, _ = await generation_service.build_prompt(sample_shot)
        assert "tracking" in positive.lower()

    async def test_prompt_includes_description(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
    ):
        """Test description is included."""
        positive, _ = await generation_service.build_prompt(sample_shot)
        assert "office" in positive.lower()

    async def test_negative_prompt_defaults(
        self,
        generation_service: GenerationService,
        sample_shot: Shot,
    ):
        """Test default negative prompt contents."""
        _, negative = await generation_service.build_prompt(sample_shot)
        assert "blurry" in negative
        assert "watermark" in negative
