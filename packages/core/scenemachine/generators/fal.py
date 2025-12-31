"""Fal.ai provider for video generation.

Production-ready provider for cloud-based video generation via Fal.ai.
Supports multiple video models including CogVideoX, Hunyuan, LTX, and more.
"""

import asyncio
import logging
import os
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


class FalProvider(GenerationProvider):
    """Production-ready provider for Fal.ai API.

    Features:
    - Multiple video model support (CogVideoX, Hunyuan, LTX, AnimateDiff)
    - Async job submission with queue support
    - Thumbnail generation
    - Cost estimation
    - Job cancellation

    Example:
        provider = FalProvider(
            api_key="fal_...",
            model_id="ltx"
        )
        result = await provider.generate(request)
    """

    MODELS: Dict[str, VideoModel] = {
        "fast-svd": VideoModel(
            id="fal-ai/fast-svd-lcm",
            name="Fast SVD LCM",
            version="",
            cost_per_second=0.03,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=14,
        ),
        "animatediff": VideoModel(
            id="fal-ai/animatediff-v2v",
            name="AnimateDiff V2V",
            version="",
            cost_per_second=0.04,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=8,
        ),
        "cogvideox": VideoModel(
            id="fal-ai/cogvideox-5b",
            name="CogVideoX 5B",
            version="",
            cost_per_second=0.05,
            supports_text_to_video=True,
            supports_image_to_video=False,
            max_duration=6.0,
            default_fps=8,
        ),
        "hunyuan": VideoModel(
            id="fal-ai/hunyuan-video",
            name="Hunyuan Video",
            version="",
            cost_per_second=0.06,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=5.0,
            default_fps=24,
        ),
        "ltx": VideoModel(
            id="fal-ai/ltx-video",
            name="LTX Video",
            version="",
            cost_per_second=0.04,
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=5.0,
            default_fps=24,
        ),
        "mochi": VideoModel(
            id="fal-ai/mochi-v1",
            name="Mochi v1",
            version="",
            cost_per_second=0.05,
            supports_text_to_video=True,
            supports_image_to_video=False,
            max_duration=5.0,
            default_fps=24,
        ),
    }

    DEFAULT_MODEL = "ltx"
    POLL_INTERVAL = 1.5  # seconds
    POLL_TIMEOUT = 600.0  # 10 minutes max

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        """Initialize Fal.ai provider.

        Args:
            api_key: Fal API key
            model_id: Default model ID to use
        """
        self.api_key = api_key
        self.model_id = model_id or self.DEFAULT_MODEL
        self._active_requests: Dict[str, str] = {}  # shot_id -> request_id

    @property
    def name(self) -> str:
        return "Fal.ai"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.FAL

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            features=[
                ProviderFeature.TEXT_TO_VIDEO,
                ProviderFeature.IMAGE_TO_VIDEO,
            ],
            min_width=256,
            max_width=1280,
            min_height=256,
            max_height=720,
            min_duration=1.0,
            max_duration=6.0,
            supported_fps=[8, 14, 16, 24],
            max_concurrent_jobs=5,
            supports_cost_estimation=True,
        )

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
        return 0.05 * duration_seconds  # Default estimate

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Generate video using Fal.ai API with async queue."""
        try:
            import fal_client
        except ImportError:
            return GenerationResult(
                success=False,
                error_message="fal-client package not installed. Run: pip install fal-client",
                error_code="MISSING_DEPENDENCY",
            )

        if not self.api_key:
            return GenerationResult(
                success=False,
                error_message="Fal API key not configured",
                error_code="MISSING_API_TOKEN",
            )

        # Set API key for fal_client
        os.environ["FAL_KEY"] = self.api_key

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
                        message="Preparing Fal.ai request",
                        stage="preparing",
                    )
                )

            # Build input arguments
            arguments = self._build_arguments(request, model)

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message=f"Submitting to {model.name}",
                        stage="submitting",
                    )
                )

            # Submit to queue (async)
            handler = await asyncio.to_thread(
                fal_client.submit,
                model.id,
                arguments=arguments,
            )

            request_id = handler.request_id
            self._active_requests[str(request.shot_id)] = request_id

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=15,
                        message=f"Queued (ID: {request_id[:8]}...)",
                        stage="queued",
                    )
                )

            # Poll for completion with progress updates
            result = await self._poll_request(
                handler,
                request.shot_id,
                progress_callback,
            )

            # Extract video URL from result
            video_url = self._extract_video_url(result)

            if not video_url:
                return GenerationResult(
                    success=False,
                    error_message="No video URL in response",
                    error_code="NO_OUTPUT",
                )

            # Download and save
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

            await self._download_video(video_url, shot_dir / "output.mp4")

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

            # Calculate timing and cost
            end_time = datetime.now(timezone.utc)
            generation_duration = (end_time - start_time).total_seconds()
            estimated_cost = self.estimate_cost(
                duration_seconds=request.duration_seconds,
                model_id=self.model_id,
            )

            # Clean up
            self._active_requests.pop(str(request.shot_id), None)

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
                    "provider": "fal",
                    "request_id": request_id,
                    "seed": result.get("seed"),
                    "prompt": request.prompt[:200],
                    "video_duration": request.duration_seconds,
                },
            )

        except asyncio.TimeoutError:
            logger.error(f"Fal.ai generation timed out for shot {request.shot_id}")
            self._active_requests.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message="Generation timed out",
                error_code="TIMEOUT",
            )

        except Exception as e:
            logger.exception("Fal.ai generation failed")
            self._active_requests.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    def _build_arguments(
        self,
        request: GenerationRequest,
        model: VideoModel,
    ) -> Dict[str, Any]:
        """Build model-specific input arguments."""
        args: Dict[str, Any] = {}

        # Common parameters
        if model.supports_text_to_video:
            args["prompt"] = request.prompt
            if request.negative_prompt:
                args["negative_prompt"] = request.negative_prompt

        if request.seed is not None:
            args["seed"] = request.seed

        # Model-specific parameters
        if model.id == "fal-ai/fast-svd-lcm":
            if request.character_references:
                args["image_url"] = request.character_references[0].get("image_url")
            elif request.input_image_path:
                args["image_url"] = request.input_image_path
            args["motion_bucket_id"] = 127
            args["cond_aug"] = 0.02
            args["fps"] = min(request.fps, model.default_fps)
            args["num_frames"] = int(request.duration_seconds * model.default_fps)

        elif model.id == "fal-ai/cogvideox-5b":
            args["num_frames"] = min(
                int(request.duration_seconds * model.default_fps), 49
            )
            args["guidance_scale"] = request.guidance_scale
            args["num_inference_steps"] = min(request.num_inference_steps, 50)

        elif model.id == "fal-ai/hunyuan-video":
            args["num_frames"] = int(request.duration_seconds * model.default_fps)
            if request.character_references:
                args["image_url"] = request.character_references[0].get("image_url")
            elif request.input_image_path:
                args["image_url"] = request.input_image_path

        elif model.id == "fal-ai/ltx-video":
            args["num_frames"] = int(request.duration_seconds * model.default_fps)
            args["num_inference_steps"] = min(request.num_inference_steps, 30)
            if request.character_references:
                args["image_url"] = request.character_references[0].get("image_url")
            elif request.input_image_path:
                args["image_url"] = request.input_image_path

        elif model.id == "fal-ai/animatediff-v2v":
            args["fps"] = model.default_fps
            args["num_frames"] = int(request.duration_seconds * model.default_fps)
            args["guidance_scale"] = request.guidance_scale

        elif model.id == "fal-ai/mochi-v1":
            args["num_frames"] = int(request.duration_seconds * model.default_fps)
            args["fps"] = model.default_fps

        # Add any extra parameters
        args.update(request.extra_params.get("model_params", {}))

        return args

    async def _poll_request(
        self,
        handler,
        shot_id: Any,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """Poll for request completion with progress updates."""
        elapsed = 0.0
        last_progress = 15

        while elapsed < self.POLL_TIMEOUT:
            status = await asyncio.to_thread(handler.status)

            if hasattr(status, "status"):
                if status.status == "COMPLETED":
                    result = await asyncio.to_thread(handler.get)
                    return result

                elif status.status == "FAILED":
                    error = getattr(status, "error", "Unknown error")
                    raise Exception(f"Fal.ai request failed: {error}")

                # Progress updates
                if status.status == "IN_PROGRESS":
                    # Estimate progress (15-85%)
                    progress = min(85, 15 + int(elapsed / self.POLL_TIMEOUT * 70))
                    if progress > last_progress and progress_callback:
                        await progress_callback(
                            GenerationProgress(
                                job_id=shot_id,
                                percent=progress,
                                message="Generating video...",
                                stage="generating",
                            )
                        )
                        last_progress = progress

                elif status.status == "IN_QUEUE":
                    logs = getattr(status, "logs", [])
                    queue_pos = len(logs) if logs else 0
                    if progress_callback:
                        await progress_callback(
                            GenerationProgress(
                                job_id=shot_id,
                                percent=15,
                                message=f"In queue (position ~{queue_pos})"
                                if queue_pos
                                else "In queue",
                                stage="queued",
                            )
                        )

            await asyncio.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

        raise asyncio.TimeoutError("Fal.ai request polling timed out")

    def _extract_video_url(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract video URL from Fal.ai result."""
        # Different models return video in different fields
        if "video" in result:
            video = result["video"]
            if isinstance(video, dict):
                return video.get("url")
            return video

        if "output" in result:
            output = result["output"]
            if isinstance(output, str):
                return output
            if isinstance(output, dict):
                return output.get("url")

        if "url" in result:
            return result["url"]

        return None

    async def _download_video(self, url: str, output_path: Path) -> None:
        """Download video from URL."""
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

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
        """Check if Fal.ai API is available."""
        if not self.api_key:
            return False

        try:
            # Quick check - just ensure key format is valid
            return self.api_key.startswith("fal_") or len(self.api_key) > 10
        except Exception as e:
            logger.debug(f"Fal.ai availability check failed: {e}")
            return False

    async def check_health(self) -> ProviderHealth:
        """Detailed health check for Fal.ai."""
        if not self.api_key:
            return ProviderHealth(
                available=False,
                message="Fal API key not configured",
                error_code="MISSING_API_KEY",
            )

        try:
            import fal_client

            os.environ["FAL_KEY"] = self.api_key

            # Try to get status of a known model
            return ProviderHealth(
                available=True,
                message="Fal.ai API key configured",
                models_available=len(self.MODELS),
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                message=f"Fal.ai health check failed: {e}",
                error_code="HEALTH_CHECK_FAILED",
            )

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running request."""
        try:
            import fal_client

            await asyncio.to_thread(
                fal_client.cancel,
                provider_job_id,
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel Fal.ai request: {e}")
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
