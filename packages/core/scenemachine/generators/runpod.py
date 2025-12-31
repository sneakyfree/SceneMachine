"""RunPod serverless provider for video generation.

Provides serverless GPU access for video generation via RunPod's
endpoint API. Supports custom endpoints with various video models.
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


class RunPodProvider(GenerationProvider):
    """RunPod serverless provider for video generation.

    Connects to RunPod serverless endpoints for GPU-accelerated
    video generation. Supports custom endpoints with various models.

    Requirements:
        - RunPod API key
        - Deployed serverless endpoint

    Example:
        provider = RunPodProvider(
            api_key="your-api-key",
            endpoint_id="your-endpoint-id"
        )
        result = await provider.generate(request)
    """

    # Predefined endpoints (can be customized)
    ENDPOINTS: Dict[str, Dict[str, Any]] = {
        "animatediff": {
            "name": "AnimateDiff Serverless",
            "default_model": "animatediff-v3",
        },
        "svd": {
            "name": "Stable Video Diffusion",
            "default_model": "svd-xt",
        },
        "cogvideo": {
            "name": "CogVideoX Serverless",
            "default_model": "cogvideox-5b",
        },
    }

    MODELS: Dict[str, VideoModel] = {
        "animatediff-v3": VideoModel(
            id="animatediff-v3",
            name="AnimateDiff v3",
            version="3.0",
            cost_per_second=0.02,  # ~$0.02/sec based on GPU time
            supports_text_to_video=True,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=8,
            default_steps=25,
        ),
        "svd-xt": VideoModel(
            id="svd-xt",
            name="Stable Video Diffusion XT",
            version="1.1",
            cost_per_second=0.03,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=4.0,
            default_fps=14,
            default_steps=25,
        ),
        "cogvideox-5b": VideoModel(
            id="cogvideox-5b",
            name="CogVideoX 5B",
            version="5b",
            cost_per_second=0.04,
            supports_text_to_video=True,
            supports_image_to_video=False,
            max_duration=6.0,
            default_fps=8,
            default_steps=50,
        ),
        "wan2-t2v": VideoModel(
            id="wan2-t2v",
            name="Wan2.1 Text-to-Video",
            version="2.1",
            cost_per_second=0.03,
            supports_text_to_video=True,
            supports_image_to_video=False,
            max_duration=5.0,
            default_fps=16,
            default_steps=30,
        ),
    }

    API_BASE = "https://api.runpod.ai/v2"
    POLL_INTERVAL = 2.0  # seconds
    POLL_TIMEOUT = 600.0  # 10 minutes

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        """Initialize RunPod provider.

        Args:
            api_key: RunPod API key
            endpoint_id: Serverless endpoint ID
            model_id: Default model to use
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.model_id = model_id or "animatediff-v3"
        self._active_jobs: Dict[str, str] = {}  # shot_id -> job_id

    @property
    def name(self) -> str:
        return "RunPod Serverless"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.RUNPOD

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            features=[
                ProviderFeature.TEXT_TO_VIDEO,
                ProviderFeature.IMAGE_TO_VIDEO,
                ProviderFeature.LORA_SUPPORT,
            ],
            min_width=256,
            max_width=1920,
            min_height=256,
            max_height=1080,
            min_duration=1.0,
            max_duration=10.0,
            supported_fps=[8, 12, 16, 24, 30],
            max_concurrent_jobs=5,  # Depends on endpoint config
            supports_cost_estimation=True,
        )

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Generate video using RunPod serverless endpoint."""
        try:
            import httpx
        except ImportError:
            return GenerationResult(
                success=False,
                error_message="httpx package not installed. Run: pip install httpx",
                error_code="MISSING_DEPENDENCY",
            )

        if not self.api_key:
            return GenerationResult(
                success=False,
                error_message="RunPod API key not configured",
                error_code="MISSING_API_KEY",
            )

        if not self.endpoint_id:
            return GenerationResult(
                success=False,
                error_message="RunPod endpoint ID not configured",
                error_code="MISSING_ENDPOINT",
            )

        model = self.get_model(request.extra_params.get("model_id", self.model_id))
        if not model:
            model = self.MODELS["animatediff-v3"]

        start_time = datetime.now(timezone.utc)

        try:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=5,
                        message="Preparing RunPod request",
                        stage="preparing",
                    )
                )

            # Build input payload
            input_payload = self._build_input(request, model)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message="Submitting to RunPod",
                        stage="submitting",
                    )
                )

            # Submit async job
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.API_BASE}/{self.endpoint_id}/run",
                    headers=headers,
                    json={"input": input_payload},
                )

                if resp.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"RunPod submission failed: {resp.text}",
                        error_code="SUBMISSION_FAILED",
                    )

                result = resp.json()
                job_id = result.get("id")

                if not job_id:
                    return GenerationResult(
                        success=False,
                        error_message="No job ID returned from RunPod",
                        error_code="NO_JOB_ID",
                    )

            self._active_jobs[str(request.shot_id)] = job_id

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=15,
                        message=f"Job submitted (ID: {job_id[:8]}...)",
                        stage="queued",
                    )
                )

            # Poll for completion
            output_data = await self._poll_job(
                job_id,
                request.shot_id,
                progress_callback,
            )

            if not output_data:
                return GenerationResult(
                    success=False,
                    error_message="No output from RunPod job",
                    error_code="NO_OUTPUT",
                )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=90,
                        message="Downloading output",
                        stage="downloading",
                    )
                )

            # Download and save output
            settings = get_settings()
            shot_dir = settings.output_dir / "shots" / str(request.shot_id)
            shot_dir.mkdir(parents=True, exist_ok=True)

            output_path = await self._download_output(
                output_data,
                shot_dir / "output.mp4",
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
                Path(output_path),
                shot_dir / "thumbnail.jpg",
            )

            # Calculate cost
            end_time = datetime.now(timezone.utc)
            generation_duration = (end_time - start_time).total_seconds()
            estimated_cost = self.estimate_cost(
                duration_seconds=request.duration_seconds,
                model_id=model.id,
            )

            # Cleanup
            self._active_jobs.pop(str(request.shot_id), None)

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
                    "provider": "runpod",
                    "job_id": job_id,
                    "endpoint_id": self.endpoint_id,
                    "seed": request.seed,
                    "prompt": request.prompt[:200],
                },
            )

        except asyncio.TimeoutError:
            self._active_jobs.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message="RunPod job timed out",
                error_code="TIMEOUT",
            )

        except Exception as e:
            logger.exception("RunPod generation failed")
            self._active_jobs.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    def _build_input(
        self,
        request: GenerationRequest,
        model: VideoModel,
    ) -> Dict[str, Any]:
        """Build input payload for RunPod endpoint."""
        # Calculate frame count
        num_frames = int(request.duration_seconds * request.fps)

        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt
            or "bad quality, blurry, distorted",
            "width": request.width,
            "height": request.height,
            "num_frames": num_frames,
            "fps": request.fps,
            "seed": request.seed or -1,
            "steps": request.num_inference_steps or model.default_steps,
            "cfg_scale": request.guidance_scale or model.default_cfg_scale,
            "model_id": model.id,
        }

        # Add image for image-to-video models
        if request.input_image_path and model.supports_image_to_video:
            # Could be a URL or base64 depending on endpoint
            payload["input_image"] = request.input_image_path

        # Add character references if supported
        if request.character_references:
            payload["character_refs"] = request.character_references

        # Add any extra parameters
        payload.update(request.extra_params.get("runpod_params", {}))

        return payload

    async def _poll_job(
        self,
        job_id: str,
        shot_id: Any,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Optional[Dict[str, Any]]:
        """Poll RunPod job for completion."""
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        elapsed = 0.0
        last_progress = 15

        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < self.POLL_TIMEOUT:
                resp = await client.get(
                    f"{self.API_BASE}/{self.endpoint_id}/status/{job_id}",
                    headers=headers,
                )

                if resp.status_code != 200:
                    raise Exception(f"RunPod status check failed: {resp.text}")

                result = resp.json()
                status = result.get("status")

                if status == "COMPLETED":
                    return result.get("output")

                elif status == "FAILED":
                    error = result.get("error", "Unknown error")
                    raise Exception(f"RunPod job failed: {error}")

                elif status == "CANCELLED":
                    raise Exception("RunPod job was cancelled")

                # Update progress
                if status == "IN_PROGRESS":
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

                elif status == "IN_QUEUE":
                    if progress_callback:
                        await progress_callback(
                            GenerationProgress(
                                job_id=shot_id,
                                percent=15,
                                message="Waiting in queue...",
                                stage="queued",
                            )
                        )

                await asyncio.sleep(self.POLL_INTERVAL)
                elapsed += self.POLL_INTERVAL

        raise asyncio.TimeoutError("RunPod job polling timed out")

    async def _download_output(
        self,
        output_data: Dict[str, Any],
        output_path: Path,
    ) -> str:
        """Download output from RunPod result."""
        import httpx

        # Output could be a URL or base64 data
        video_url = output_data.get("video_url") or output_data.get("output_url")

        if video_url:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.get(video_url, follow_redirects=True)
                resp.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(resp.content)

        elif "video_base64" in output_data:
            import base64

            video_data = base64.b64decode(output_data["video_base64"])
            with open(output_path, "wb") as f:
                f.write(video_data)

        else:
            raise ValueError("No video URL or base64 data in output")

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
            from scenemachine.utils.ffmpeg import get_ffmpeg, FFmpegNotFoundError

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
        """Check if RunPod endpoint is available."""
        if not self.api_key or not self.endpoint_id:
            return False

        try:
            import httpx

            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check endpoint health
                resp = await client.get(
                    f"{self.API_BASE}/{self.endpoint_id}/health",
                    headers=headers,
                )
                return resp.status_code == 200

        except Exception:
            return False

    async def check_health(self) -> ProviderHealth:
        """Detailed health check for RunPod."""
        if not self.api_key:
            return ProviderHealth(
                available=False,
                message="RunPod API key not configured",
                error_code="MISSING_API_KEY",
            )

        if not self.endpoint_id:
            return ProviderHealth(
                available=False,
                message="RunPod endpoint ID not configured",
                error_code="MISSING_ENDPOINT",
            )

        try:
            import httpx
            import time

            headers = {"Authorization": f"Bearer {self.api_key}"}

            start = time.time()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.API_BASE}/{self.endpoint_id}/health",
                    headers=headers,
                )
                latency = (time.time() - start) * 1000

                if resp.status_code != 200:
                    return ProviderHealth(
                        available=False,
                        message=f"RunPod returned status {resp.status_code}",
                        latency_ms=latency,
                        error_code="BAD_STATUS",
                    )

                health_data = resp.json()
                workers = health_data.get("workers", {})
                ready_workers = workers.get("ready", 0)
                queue_length = health_data.get("jobs", {}).get("in_queue", 0)

                return ProviderHealth(
                    available=True,
                    message=f"RunPod healthy ({ready_workers} workers ready)",
                    latency_ms=latency,
                    models_available=len(self.MODELS),
                    queue_length=queue_length,
                )

        except Exception as e:
            return ProviderHealth(
                available=False,
                message=f"RunPod health check failed: {e}",
                error_code="HEALTH_CHECK_FAILED",
            )

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running RunPod job."""
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.API_BASE}/{self.endpoint_id}/cancel/{provider_job_id}",
                    headers=headers,
                )
                return resp.status_code == 200

        except Exception as e:
            logger.warning(f"Failed to cancel RunPod job: {e}")
            return False

    def estimate_cost(
        self,
        duration_seconds: float = 3.0,
        model_id: Optional[str] = None,
    ) -> float:
        """Estimate generation cost in USD."""
        model = self.get_model(model_id or self.model_id)
        if model:
            return model.cost_per_second * duration_seconds
        return 0.05 * duration_seconds  # Default estimate

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
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

    def get_model(self, model_id: str) -> Optional[VideoModel]:
        """Get model by ID."""
        return self.MODELS.get(model_id)
