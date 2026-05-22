"""Mock generation provider for testing and development."""

import asyncio
import logging
from typing import Any

from scenemachine.config import get_settings
from scenemachine.models.generation_job import JobProvider

from .base import (
    GenerationProgress,
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    ProgressCallback,
    ProviderCapabilities,
    ProviderFeature,
    VideoModel,
)

logger = logging.getLogger(__name__)


class MockGenerationProvider(GenerationProvider):
    """Mock provider for testing and development.

    Simulates video generation with configurable delays
    and produces placeholder output files.
    """

    MODELS: dict[str, VideoModel] = {
        "mock-fast": VideoModel(
            id="mock-fast",
            name="Mock Fast Model",
            version="1.0",
            cost_per_second=0.0,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=10.0,
            default_fps=24,
        ),
        "mock-quality": VideoModel(
            id="mock-quality",
            name="Mock Quality Model",
            version="1.0",
            cost_per_second=0.0,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=10.0,
            default_fps=24,
        ),
    }

    def __init__(
        self,
        simulate_delay: float = 2.0,
        simulate_failures: bool = False,
        failure_rate: float = 0.1,
    ) -> None:
        """Initialize mock provider.

        Args:
            simulate_delay: Simulated generation time in seconds
            simulate_failures: Whether to randomly simulate failures
            failure_rate: Probability of failure (0.0-1.0)
        """
        self.simulate_delay = simulate_delay
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate

    @property
    def name(self) -> str:
        return "Mock Provider"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.LOCAL

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            features=[
                ProviderFeature.TEXT_TO_VIDEO,
                ProviderFeature.IMAGE_TO_VIDEO,
            ],
            min_width=256,
            max_width=3840,
            min_height=256,
            max_height=2160,
            min_duration=0.5,
            max_duration=30.0,
            supported_fps=[8, 12, 16, 24, 30, 60],
            max_concurrent_jobs=10,
            supports_cost_estimation=True,
        )

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Simulate generation with delays."""
        settings = get_settings()
        output_dir = settings.output_dir / "shots" / str(request.shot_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check for simulated failure
        if self.simulate_failures:
            import random

            if random.random() < self.failure_rate:
                return GenerationResult(
                    success=False,
                    error_message="Simulated random failure",
                    error_code="MOCK_FAILURE",
                )

        # Simulate progress stages
        stages = [
            (0, "Initializing generation"),
            (10, "Loading models"),
            (25, "Processing prompt"),
            (40, "Generating initial frames"),
            (60, "Generating video sequence"),
            (80, "Encoding video"),
            (95, "Finalizing output"),
        ]

        delay_per_stage = self.simulate_delay / len(stages)

        for percent, message in stages:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=percent,
                        message=message,
                        stage="generating",
                    )
                )
            await asyncio.sleep(delay_per_stage)

        # Create placeholder output files
        output_path = output_dir / "output.mp4"
        thumbnail_path = output_dir / "thumbnail.jpg"

        # Create minimal placeholder files
        output_path.touch()
        thumbnail_path.touch()

        # Final progress update
        if progress_callback:
            await progress_callback(
                GenerationProgress(
                    job_id=request.shot_id,
                    percent=100,
                    message="Generation complete",
                    stage="complete",
                )
            )

        return GenerationResult(
            success=True,
            output_path=f"shots/{request.shot_id}/output.mp4",
            thumbnail_path=f"shots/{request.shot_id}/thumbnail.jpg",
            duration_seconds=self.simulate_delay,
            cost_usd=0.0,
            metadata={
                "model": "mock-fast",
                "provider": "mock",
                "seed": request.seed or 42,
                "prompt": request.prompt[:100],
                "simulated": True,
            },
        )

    async def check_availability(self) -> bool:
        """Mock provider is always available."""
        return True

    def estimate_cost(
        self,
        duration_seconds: float = 3.0,
        model_id: str | None = None,
    ) -> float:
        """Mock generation is free."""
        return 0.0

    def list_models(self) -> list[dict[str, Any]]:
        """List available mock models."""
        return [
            {
                "id": model_id,
                "name": model.name,
                "cost_per_second": model.cost_per_second,
                "supports_text_to_video": model.supports_text_to_video,
                "supports_image_to_video": model.supports_image_to_video,
                "max_duration": model.max_duration,
            }
            for model_id, model in self.MODELS.items()
        ]

    def get_model(self, model_id: str) -> VideoModel | None:
        """Get mock model by ID."""
        return self.MODELS.get(model_id)
