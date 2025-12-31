"""Replicate.com provider for video generation.

Production-ready provider for cloud-based video generation via Replicate.com.
Supports multiple video models including MiniMax, Luma, Kling, and SVD.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    ProviderHealth,
    VideoModel,
)

logger = logging.getLogger(__name__)


class ReplicateProvider(GenerationProvider):
    """Production-ready provider for Replicate.com API.

    Features:
    - Multiple video model support (MiniMax, Luma, Kling, SVD)
    - Async job submission and polling
    - Thumbnail generation
    - Cost estimation
    - Job cancellation

    Example:
        provider = ReplicateProvider(
            api_token="r8_...",
            model_id="minimax"
        )
        result = await provider.generate(request)
    """

    MODELS: Dict[str, VideoModel] = {
        "svd": VideoModel(
            id="stability-ai/stable-video-diffusion",
            name="Stable Video Diffusion",
            version="3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            cost_per_second=0.05,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=14,
            input_mapping={"prompt": "motion_bucket_id"},
        ),
        "minimax": VideoModel(
            id="minimax/video-01",
            name="MiniMax Video-01",
            version="",
            cost_per_second=0.08,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=6.0,
            default_fps=24,
        ),
        "luma": VideoModel(
            id="luma/ray",
            name="Luma Dream Machine",
            version="",
            cost_per_second=0.10,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=5.0,
            default_fps=24,
        ),
        "kling": VideoModel(
            id="kwaivgi/kling-v1",
            name="Kling v1",
            version="",
            cost_per_second=0.06,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=5.0,
            default_fps=24,
        ),
        "runway-gen3": VideoModel(
            id="fofr/runway-gen3-turbo",
            name="Runway Gen-3 Turbo",
            version="",
            cost_per_second=0.12,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=10.0,
            default_fps=24,
        ),
    }

    DEFAULT_MODEL = "minimax"
    POLL_INTERVAL = 2.0  # seconds
    POLL_TIMEOUT = 600.0  # 10 minutes max

    def __init__(
        self,
        api_token: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        """Initialize Replicate provider.

        Args:
            api_token: Replicate API token (starts with r8_)
            model_id: Default model ID to use
        """
        self.api_token = api_token
        self.model_id = model_id or self.DEFAULT_MODEL
        self._client = None
        self._active_predictions: Dict[str, str] = {}  # shot_id -> prediction_id

    @property
    def name(self) -> str:
        return "Replicate"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.REPLICATE

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            features=[
                ProviderFeature.TEXT_TO_VIDEO,
                ProviderFeature.IMAGE_TO_VIDEO,
            ],
            min_width=512,
            max_width=1920,
            min_height=512,
            max_height=1080,
            min_duration=1.0,
            max_duration=10.0,
            supported_fps=[14, 24, 30],
            max_concurrent_jobs=5,
            supports_cost_estimation=True,
        )

    def _get_client(self):
        """Get or create Replicate client."""
        if self._client is None:
            import replicate

            self._client = replicate.Client(api_token=self.api_token)
        return self._client

    def get_model(self, model_id: Optional[str] = None) -> Optional[VideoModel]:
        """Get model configuration."""
        mid = model_id or self.model_id
        return self.MODELS.get(mid)

    def estimate_cost(
        self,
        duration_seconds: float = 3.0,
        model_id: Optional[str] = None,
    ) -> float:
        """Estimate generation cost in USD."""
        model = self.get_model(model_id)
        if model:
            return model.cost_per_second * duration_seconds
        return 0.08 * duration_seconds  # Default estimate

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Generate video using Replicate API with async polling."""
        try:
            import replicate
        except ImportError:
            return GenerationResult(
                success=False,
                error_message="replicate package not installed. Run: pip install replicate",
                error_code="MISSING_DEPENDENCY",
            )

        if not self.api_token:
            return GenerationResult(
                success=False,
                error_message="Replicate API token not configured",
                error_code="MISSING_API_TOKEN",
            )

        start_time = datetime.now(timezone.utc)
        model = self.get_model(request.extra_params.get("model_id", self.model_id))
        if not model:
            model = self.MODELS[self.DEFAULT_MODEL]

        try:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=5,
                        message="Preparing generation request",
                        stage="preparing",
                    )
                )

            # Build input parameters
            input_params = self._build_input_params(request, model)

            # Submit prediction asynchronously
            client = self._get_client()
            model_ref = f"{model.id}:{model.version}" if model.version else model.id

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message=f"Submitting to {model.name}",
                        stage="submitting",
                    )
                )

            # Create prediction (async submission)
            prediction = await asyncio.to_thread(
                client.predictions.create,
                model=model_ref if model.version else None,
                version=model.version if model.version else None,
                input=input_params,
            )

            # Store prediction ID for potential cancellation
            self._active_predictions[str(request.shot_id)] = prediction.id

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=15,
                        message=f"Job submitted (ID: {prediction.id[:8]}...)",
                        stage="queued",
                    )
                )

            # Poll for completion
            output_url = await self._poll_prediction(
                prediction.id,
                request.shot_id,
                progress_callback,
            )

            if not output_url:
                return GenerationResult(
                    success=False,
                    error_message="Generation produced no output",
                    error_code="NO_OUTPUT",
                )

            # Download and save output
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=90,
                        message="Downloading generated video",
                        stage="downloading",
                    )
                )

            settings = get_settings()
            shot_dir = settings.output_dir / "shots" / str(request.shot_id)
            shot_dir.mkdir(parents=True, exist_ok=True)

            output_path = await self._download_output(
                output_url, shot_dir / "output.mp4"
            )

            # Generate thumbnail
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=95,
                        message="Generating thumbnail",
                        stage="thumbnail",
                    )
                )

            thumbnail_path = await self._generate_thumbnail(
                shot_dir / "output.mp4",
                shot_dir / "thumbnail.jpg",
            )

            # Calculate actual duration and cost
            end_time = datetime.now(timezone.utc)
            generation_duration = (end_time - start_time).total_seconds()
            estimated_cost = self.estimate_cost(
                duration_seconds=request.duration_seconds,
                model_id=self.model_id,
            )

            # Clean up
            self._active_predictions.pop(str(request.shot_id), None)

            return GenerationResult(
                success=True,
                output_path=f"shots/{request.shot_id}/output.mp4",
                thumbnail_path=f"shots/{request.shot_id}/thumbnail.jpg"
                if thumbnail_path
                else None,
                duration_seconds=generation_duration,
                cost_usd=estimated_cost,
                metadata={
                    "model": model.id,
                    "model_name": model.name,
                    "provider": "replicate",
                    "prediction_id": prediction.id,
                    "seed": request.seed,
                    "prompt": request.prompt[:200],
                    "video_duration": request.duration_seconds,
                },
            )

        except asyncio.TimeoutError:
            logger.error(f"Replicate generation timed out for shot {request.shot_id}")
            self._active_predictions.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message="Generation timed out",
                error_code="TIMEOUT",
            )

        except Exception as e:
            logger.exception("Replicate generation failed")
            self._active_predictions.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    def _build_input_params(
        self,
        request: GenerationRequest,
        model: VideoModel,
    ) -> Dict[str, Any]:
        """Build model-specific input parameters."""
        params: Dict[str, Any] = {}

        # Common parameters
        if model.supports_text_to_video:
            params["prompt"] = request.prompt
            if request.negative_prompt:
                params["negative_prompt"] = request.negative_prompt

        # Handle seed
        if request.seed is not None:
            params["seed"] = request.seed

        # Model-specific parameter mapping
        if model.id == "stability-ai/stable-video-diffusion":
            # SVD requires an input image
            if request.character_references:
                params["input_image"] = request.character_references[0].get("image_url")
            elif request.input_image_path:
                params["input_image"] = request.input_image_path
            params["motion_bucket_id"] = 127
            params["fps"] = min(request.fps, model.default_fps)
            params["num_frames"] = int(request.duration_seconds * model.default_fps)

        elif model.id == "minimax/video-01":
            params["prompt_optimizer"] = True

        elif model.id == "luma/ray":
            params["aspect_ratio"] = f"{request.width}:{request.height}"
            if request.character_references:
                params["start_image_url"] = request.character_references[0].get(
                    "image_url"
                )
            elif request.input_image_path:
                params["start_image_url"] = request.input_image_path

        elif model.id == "kwaivgi/kling-v1":
            params["duration"] = min(request.duration_seconds, model.max_duration)
            params["aspect_ratio"] = self._get_aspect_ratio(
                request.width, request.height
            )

        # Add any extra parameters
        params.update(request.extra_params.get("model_params", {}))

        return params

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """Convert dimensions to aspect ratio string."""
        if width == height:
            return "1:1"
        elif width > height:
            ratio = width / height
            if abs(ratio - 16 / 9) < 0.1:
                return "16:9"
            elif abs(ratio - 4 / 3) < 0.1:
                return "4:3"
        else:
            ratio = height / width
            if abs(ratio - 16 / 9) < 0.1:
                return "9:16"
            elif abs(ratio - 4 / 3) < 0.1:
                return "3:4"
        return "16:9"  # Default

    async def _poll_prediction(
        self,
        prediction_id: str,
        shot_id: Any,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Optional[str]:
        """Poll for prediction completion with progress updates."""
        client = self._get_client()
        elapsed = 0.0
        last_progress = 15

        while elapsed < self.POLL_TIMEOUT:
            prediction = await asyncio.to_thread(
                client.predictions.get,
                prediction_id,
            )

            status = prediction.status

            if status == "succeeded":
                output = prediction.output
                # Handle different output formats
                if isinstance(output, str):
                    return output
                elif isinstance(output, list) and output:
                    return (
                        output[0] if isinstance(output[0], str) else output[0].get("url")
                    )
                elif isinstance(output, dict):
                    return output.get("video") or output.get("url")
                return None

            elif status == "failed":
                error = prediction.error or "Unknown error"
                raise Exception(f"Prediction failed: {error}")

            elif status == "canceled":
                raise Exception("Prediction was canceled")

            # Update progress based on status
            if status == "starting":
                progress = 20
                message = "Model loading..."
            elif status == "processing":
                # Estimate progress during processing (20-85%)
                progress = min(85, 20 + int(elapsed / self.POLL_TIMEOUT * 65))
                message = "Generating video..."
            else:
                progress = last_progress
                message = f"Status: {status}"

            if progress > last_progress and progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=shot_id,
                        percent=progress,
                        message=message,
                        stage="generating",
                    )
                )
                last_progress = progress

            await asyncio.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

        raise asyncio.TimeoutError("Prediction polling timed out")

    async def _download_output(self, url: str, output_path: Path) -> str:
        """Download generated video from URL."""
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        return str(output_path)

    async def _generate_thumbnail(
        self,
        video_path: Path,
        thumbnail_path: Path,
    ) -> Optional[str]:
        """Generate thumbnail from video using ffmpeg."""
        if not video_path.exists():
            return None

        try:
            from scenemachine.utils.ffmpeg import FFmpegNotFoundError, get_ffmpeg

            ffmpeg = get_ffmpeg()
            await ffmpeg.extract_frame(
                video_path=video_path,
                output_path=thumbnail_path,
                timestamp=1.0,
                quality=2,
            )

            if thumbnail_path.exists():
                return str(thumbnail_path)
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        return None

    async def check_availability(self) -> bool:
        """Check if Replicate API is available."""
        if not self.api_token:
            return False
        try:
            import replicate

            client = replicate.Client(api_token=self.api_token)
            await asyncio.to_thread(lambda: client.models.list().__next__())
            return True
        except Exception as e:
            logger.debug(f"Replicate availability check failed: {e}")
            return False

    async def check_health(self) -> ProviderHealth:
        """Detailed health check for Replicate."""
        if not self.api_token:
            return ProviderHealth(
                available=False,
                message="Replicate API token not configured",
                error_code="MISSING_API_TOKEN",
            )

        try:
            import time

            import replicate

            start = time.time()
            client = replicate.Client(api_token=self.api_token)
            await asyncio.to_thread(lambda: client.models.list().__next__())
            latency = (time.time() - start) * 1000

            return ProviderHealth(
                available=True,
                message="Replicate API is available",
                latency_ms=latency,
                models_available=len(self.MODELS),
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                message=f"Replicate health check failed: {e}",
                error_code="HEALTH_CHECK_FAILED",
            )

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running prediction."""
        try:
            client = self._get_client()
            await asyncio.to_thread(
                client.predictions.cancel,
                provider_job_id,
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel Replicate prediction: {e}")
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        """List available video generation models."""
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
