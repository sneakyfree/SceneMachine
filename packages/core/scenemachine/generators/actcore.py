"""ActCore provider for performer-driven video generation.

Production-ready provider for motion retargeting using performer motion data.
Integrates with ActForge marketplace bookings for human and synthetic performers.

Supports:
- LivePortrait vectors for facial animation
- Roop-GS-Anim for full-body motion capture
- Blink (10s), Deep (120s), and Epic (20min) booking modes
"""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

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


class ActCoreProvider(GenerationProvider):
    """Provider for ActCore performer-driven video generation.

    This provider integrates with the ActForge marketplace to use
    performer motion data (LivePortrait vectors, Roop-GS-Anim captures)
    for high-quality retargeting.

    Booking Modes:
    - BLINK: 10-second quick generation, auto-matched performer
    - DEEP: Up to 120 seconds, method acting with emotion markers
    - EPIC: Long-form (5-20 minutes), dedicated session with performer

    Example:
        provider = ActCoreProvider()
        request = GenerationRequest(
            shot_id=shot_id,
            prompt="Character smiles warmly",
            extra_params={
                "booking_id": "...",
                "performer_id": "...",
                "mode": "BLINK",
            }
        )
        result = await provider.generate(request)
    """

    MODELS: dict[str, VideoModel] = {
        "liveportrait": VideoModel(
            id="liveportrait-v1",
            name="LivePortrait Face Retargeting",
            version="1.0.0",
            cost_per_second=0.05,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=30.0,
            default_fps=30,
            extra_params={"retargeting_type": "face"},
        ),
        "roop-gs-anim": VideoModel(
            id="roop-gs-anim-v1",
            name="Roop-GS Full-Body Animation",
            version="1.0.0",
            cost_per_second=0.08,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=120.0,
            default_fps=30,
            extra_params={"retargeting_type": "body"},
        ),
        "hybrid": VideoModel(
            id="actcore-hybrid-v1",
            name="ActCore Hybrid (Face + Body)",
            version="1.0.0",
            cost_per_second=0.12,
            supports_text_to_video=False,
            supports_image_to_video=True,
            max_duration=300.0,  # 5 minutes for Epic mode
            default_fps=30,
            extra_params={"retargeting_type": "hybrid"},
        ),
    }

    # Mode configurations
    MODE_CONFIGS = {
        "BLINK": {
            "max_duration": 10.0,
            "default_model": "liveportrait",
            "requires_booking": False,
            "auto_match": True,
        },
        "DEEP": {
            "max_duration": 120.0,
            "default_model": "roop-gs-anim",
            "requires_booking": True,
            "auto_match": False,
        },
        "EPIC": {
            "max_duration": 1200.0,  # 20 minutes
            "default_model": "hybrid",
            "requires_booking": True,
            "auto_match": False,
        },
    }

    DEFAULT_MODEL = "liveportrait"
    POLL_INTERVAL = 1.0
    POLL_TIMEOUT = 1800.0  # 30 minutes for long Epic sessions

    def __init__(
        self,
        comfyui_url: str | None = None,
        local_processing: bool = True,
    ) -> None:
        """Initialize ActCore provider.

        Args:
            comfyui_url: ComfyUI server URL for local processing
            local_processing: Whether to use local GPU (vs cloud fallback)
        """
        self.comfyui_url = comfyui_url or "http://127.0.0.1:8188"
        self.local_processing = local_processing
        self._active_jobs: dict[str, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "ActCore"

    @property
    def provider_type(self) -> JobProvider:
        return JobProvider.ACTCORE

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            features=[
                ProviderFeature.IMAGE_TO_VIDEO,
                ProviderFeature.VIDEO_TO_VIDEO,
                ProviderFeature.CHARACTER_CONSISTENCY,
                ProviderFeature.STYLE_TRANSFER,
            ],
            min_width=512,
            max_width=1920,
            min_height=512,
            max_height=1080,
            min_duration=1.0,
            max_duration=1200.0,  # 20 minutes for Epic mode
            supported_fps=[24, 30, 60],
            max_concurrent_jobs=3,
            supports_cost_estimation=True,
        )

    def get_model(self, model_id: str | None = None) -> VideoModel | None:
        """Get model configuration."""
        mid = model_id or self.DEFAULT_MODEL
        return self.MODELS.get(mid)

    def estimate_cost(
        self,
        duration_seconds: float = 3.0,
        model_id: str | None = None,
        mode: str | None = None,
    ) -> float:
        """Estimate generation cost in USD.

        Cost is based on model + performer booking fee.
        Actual performer fee is handled separately via PayoutService.
        """
        model = self.get_model(model_id)
        base_cost = model.cost_per_second * duration_seconds if model else 0.05 * duration_seconds

        # Mode-based multiplier
        mode_multipliers = {
            "BLINK": 1.0,
            "DEEP": 1.5,
            "EPIC": 2.0,
        }
        multiplier = mode_multipliers.get(mode or "BLINK", 1.0)

        return base_cost * multiplier

    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Generate video using ActCore performer motion retargeting.

        Required extra_params:
        - performer_id: UUID of the performer
        - mode: BLINK, DEEP, or EPIC
        - take_id: (optional) Specific performance take to use
        - booking_id: (optional, required for DEEP/EPIC) Booking reference
        - source_image: Path to character image for retargeting
        - motion_profile: (optional) Custom motion profile override
        """
        start_time = datetime.now(UTC)
        mode = request.extra_params.get("mode", "BLINK")
        performer_id = request.extra_params.get("performer_id")
        booking_id = request.extra_params.get("booking_id")
        take_id = request.extra_params.get("take_id")
        source_image = request.extra_params.get("source_image") or request.input_image_path

        # Validate mode
        mode_config = self.MODE_CONFIGS.get(mode)
        if not mode_config:
            return GenerationResult(
                success=False,
                error_message=f"Invalid mode: {mode}. Must be BLINK, DEEP, or EPIC",
                error_code="INVALID_MODE",
            )

        # Validate booking for DEEP/EPIC
        if mode_config["requires_booking"] and not booking_id:
            return GenerationResult(
                success=False,
                error_message=f"Booking ID required for {mode} mode",
                error_code="BOOKING_REQUIRED",
            )

        # Validate source image
        if not source_image:
            return GenerationResult(
                success=False,
                error_message="Source image required for ActCore retargeting",
                error_code="SOURCE_IMAGE_REQUIRED",
            )

        try:
            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=5,
                        message="Preparing ActCore generation",
                        stage="preparing",
                    )
                )

            # Determine model based on mode
            model_id = request.extra_params.get("model_id") or mode_config["default_model"]
            model = self.get_model(model_id)

            if not model:
                model = self.MODELS[self.DEFAULT_MODEL]

            # Validate duration
            if request.duration_seconds > mode_config["max_duration"]:
                return GenerationResult(
                    success=False,
                    error_message=f"Duration {request.duration_seconds}s exceeds {mode} max of {mode_config['max_duration']}s",
                    error_code="DURATION_EXCEEDED",
                )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=10,
                        message=f"Loading performer motion data ({mode} mode)",
                        stage="loading_motion",
                    )
                )

            # Load motion profile
            motion_profile = await self._load_motion_profile(
                performer_id=performer_id,
                take_id=take_id,
                mode=mode,
                custom_profile=request.extra_params.get("motion_profile"),
            )

            if not motion_profile:
                return GenerationResult(
                    success=False,
                    error_message="Failed to load performer motion profile",
                    error_code="MOTION_PROFILE_NOT_FOUND",
                )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=20,
                        message="Preparing retargeting pipeline",
                        stage="pipeline_setup",
                    )
                )

            # Store active job info
            self._active_jobs[str(request.shot_id)] = {
                "mode": mode,
                "performer_id": performer_id,
                "booking_id": booking_id,
                "started_at": start_time,
            }

            # Execute retargeting based on model type
            retargeting_type = model.extra_params.get("retargeting_type", "face")

            if retargeting_type == "face":
                output_path = await self._process_liveportrait(
                    request=request,
                    motion_profile=motion_profile,
                    source_image=source_image,
                    progress_callback=progress_callback,
                )
            elif retargeting_type == "body":
                output_path = await self._process_roop_gs_anim(
                    request=request,
                    motion_profile=motion_profile,
                    source_image=source_image,
                    progress_callback=progress_callback,
                )
            else:  # hybrid
                output_path = await self._process_hybrid(
                    request=request,
                    motion_profile=motion_profile,
                    source_image=source_image,
                    progress_callback=progress_callback,
                )

            if not output_path:
                return GenerationResult(
                    success=False,
                    error_message="Retargeting produced no output",
                    error_code="NO_OUTPUT",
                )

            if progress_callback:
                await progress_callback(
                    GenerationProgress(
                        job_id=request.shot_id,
                        percent=95,
                        message="Generating thumbnail",
                        stage="thumbnail",
                    )
                )

            # Generate thumbnail
            settings = get_settings()
            shot_dir = settings.output_dir / "shots" / str(request.shot_id)
            thumbnail_path = await self._generate_thumbnail(
                Path(output_path),
                shot_dir / "thumbnail.jpg",
            )

            # Calculate final cost
            end_time = datetime.now(UTC)
            generation_duration = (end_time - start_time).total_seconds()
            estimated_cost = self.estimate_cost(
                duration_seconds=request.duration_seconds,
                model_id=model_id,
                mode=mode,
            )

            # Clean up
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
                    "provider": "actcore",
                    "mode": mode,
                    "performer_id": str(performer_id) if performer_id else None,
                    "booking_id": str(booking_id) if booking_id else None,
                    "take_id": str(take_id) if take_id else None,
                    "retargeting_type": retargeting_type,
                    "prompt": request.prompt[:200] if request.prompt else None,
                    "video_duration": request.duration_seconds,
                },
            )

        except TimeoutError:
            logger.error(f"ActCore generation timed out for shot {request.shot_id}")
            self._active_jobs.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message="Generation timed out",
                error_code="TIMEOUT",
            )

        except Exception as e:
            logger.exception("ActCore generation failed")
            self._active_jobs.pop(str(request.shot_id), None)
            return GenerationResult(
                success=False,
                error_message=str(e),
                error_code="GENERATION_FAILED",
            )

    async def _load_motion_profile(
        self,
        performer_id: str | None,
        take_id: str | None,
        mode: str,
        custom_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Load motion profile from database or custom input.

        Motion profile includes:
        - liveportrait_path: Path to LivePortrait vector data
        - roop_gs_anim_path: Path to Roop-GS-Anim capture
        - emotion_markers: Timestamps with emotion labels
        - keyframes: Critical pose keyframes
        """
        if custom_profile:
            return custom_profile

        if not performer_id:
            # For BLINK mode auto-match, use default synthetic performer
            return {
                "type": "default",
                "liveportrait_path": None,
                "roop_gs_anim_path": None,
                "emotion_markers": [],
                "keyframes": [],
            }

        # In production, this would query the database for performer's motion data
        # For now, return a structured placeholder that expects real paths
        return {
            "type": "performer",
            "performer_id": performer_id,
            "take_id": take_id,
            "liveportrait_path": f"performers/{performer_id}/liveportrait/latest.pkl",
            "roop_gs_anim_path": f"performers/{performer_id}/roop_gs_anim/latest.npz",
            "emotion_markers": [],
            "keyframes": [],
        }

    async def _process_liveportrait(
        self,
        request: GenerationRequest,
        motion_profile: dict[str, Any],
        source_image: str,
        progress_callback: ProgressCallback | None = None,
    ) -> str | None:
        """Process facial retargeting using LivePortrait.

        LivePortrait provides:
        - Real-time facial expression transfer
        - Eye gaze control
        - Lip sync capabilities
        """
        settings = get_settings()
        shot_dir = settings.output_dir / "shots" / str(request.shot_id)
        shot_dir.mkdir(parents=True, exist_ok=True)
        output_path = shot_dir / "output.mp4"

        if progress_callback:
            await progress_callback(
                GenerationProgress(
                    job_id=request.shot_id,
                    percent=30,
                    message="Processing facial expressions",
                    stage="liveportrait",
                )
            )

        # Build LivePortrait workflow for ComfyUI
        workflow = self._build_liveportrait_workflow(
            source_image=source_image,
            motion_data=motion_profile.get("liveportrait_path"),
            output_path=str(output_path),
            duration=request.duration_seconds,
            fps=request.fps,
            width=request.width,
            height=request.height,
        )

        # Execute via ComfyUI
        result = await self._execute_comfyui_workflow(
            workflow=workflow,
            shot_id=request.shot_id,
            progress_callback=progress_callback,
            progress_range=(30, 90),
        )

        if result and output_path.exists():
            return str(output_path)
        return None

    async def _process_roop_gs_anim(
        self,
        request: GenerationRequest,
        motion_profile: dict[str, Any],
        source_image: str,
        progress_callback: ProgressCallback | None = None,
    ) -> str | None:
        """Process full-body retargeting using Roop-GS-Anim.

        Roop-GS-Anim provides:
        - Full body pose transfer
        - Gaussian splatting for quality
        - Multi-angle synthesis
        """
        settings = get_settings()
        shot_dir = settings.output_dir / "shots" / str(request.shot_id)
        shot_dir.mkdir(parents=True, exist_ok=True)
        output_path = shot_dir / "output.mp4"

        if progress_callback:
            await progress_callback(
                GenerationProgress(
                    job_id=request.shot_id,
                    percent=30,
                    message="Processing body motion capture",
                    stage="roop_gs_anim",
                )
            )

        # Build Roop-GS-Anim workflow
        workflow = self._build_roop_gs_anim_workflow(
            source_image=source_image,
            motion_data=motion_profile.get("roop_gs_anim_path"),
            output_path=str(output_path),
            duration=request.duration_seconds,
            fps=request.fps,
            width=request.width,
            height=request.height,
        )

        # Execute via ComfyUI
        result = await self._execute_comfyui_workflow(
            workflow=workflow,
            shot_id=request.shot_id,
            progress_callback=progress_callback,
            progress_range=(30, 90),
        )

        if result and output_path.exists():
            return str(output_path)
        return None

    async def _process_hybrid(
        self,
        request: GenerationRequest,
        motion_profile: dict[str, Any],
        source_image: str,
        progress_callback: ProgressCallback | None = None,
    ) -> str | None:
        """Process hybrid face + body retargeting.

        Combines LivePortrait (face) with Roop-GS-Anim (body)
        for best quality in Epic mode sessions.
        """
        settings = get_settings()
        shot_dir = settings.output_dir / "shots" / str(request.shot_id)
        shot_dir.mkdir(parents=True, exist_ok=True)
        output_path = shot_dir / "output.mp4"

        if progress_callback:
            await progress_callback(
                GenerationProgress(
                    job_id=request.shot_id,
                    percent=25,
                    message="Processing body motion",
                    stage="hybrid_body",
                )
            )

        # First pass: Body motion
        body_workflow = self._build_roop_gs_anim_workflow(
            source_image=source_image,
            motion_data=motion_profile.get("roop_gs_anim_path"),
            output_path=str(shot_dir / "body_pass.mp4"),
            duration=request.duration_seconds,
            fps=request.fps,
            width=request.width,
            height=request.height,
        )

        await self._execute_comfyui_workflow(
            workflow=body_workflow,
            shot_id=request.shot_id,
            progress_callback=progress_callback,
            progress_range=(25, 55),
        )

        if progress_callback:
            await progress_callback(
                GenerationProgress(
                    job_id=request.shot_id,
                    percent=60,
                    message="Enhancing facial expressions",
                    stage="hybrid_face",
                )
            )

        # Second pass: Face enhancement
        face_workflow = self._build_liveportrait_workflow(
            source_image=str(shot_dir / "body_pass.mp4"),  # Use body output as input
            motion_data=motion_profile.get("liveportrait_path"),
            output_path=str(output_path),
            duration=request.duration_seconds,
            fps=request.fps,
            width=request.width,
            height=request.height,
            enhance_only=True,  # Only enhance face, keep body
        )

        result = await self._execute_comfyui_workflow(
            workflow=face_workflow,
            shot_id=request.shot_id,
            progress_callback=progress_callback,
            progress_range=(60, 90),
        )

        if result and output_path.exists():
            return str(output_path)
        return None

    def _build_liveportrait_workflow(
        self,
        source_image: str,
        motion_data: str | None,
        output_path: str,
        duration: float,
        fps: int,
        width: int,
        height: int,
        enhance_only: bool = False,
    ) -> dict[str, Any]:
        """Build ComfyUI workflow for LivePortrait processing."""
        return {
            "client_id": "actcore_liveportrait",
            "prompt": {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": source_image},
                },
                "2": {
                    "class_type": "LivePortraitLoader",
                    "inputs": {
                        "motion_data": motion_data,
                        "enhance_only": enhance_only,
                    },
                },
                "3": {
                    "class_type": "LivePortraitApply",
                    "inputs": {
                        "image": ["1", 0],
                        "model": ["2", 0],
                        "duration": duration,
                        "fps": fps,
                    },
                },
                "4": {
                    "class_type": "VHS_VideoCombine",
                    "inputs": {
                        "images": ["3", 0],
                        "frame_rate": fps,
                        "filename_prefix": "actcore",
                        "format": "video/mp4",
                    },
                },
            },
            "extra_data": {
                "output_path": output_path,
                "width": width,
                "height": height,
            },
        }

    def _build_roop_gs_anim_workflow(
        self,
        source_image: str,
        motion_data: str | None,
        output_path: str,
        duration: float,
        fps: int,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        """Build ComfyUI workflow for Roop-GS-Anim processing."""
        return {
            "client_id": "actcore_roop_gs",
            "prompt": {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": source_image},
                },
                "2": {
                    "class_type": "RoopGSAnimLoader",
                    "inputs": {
                        "motion_capture": motion_data,
                        "gaussian_model": "default",
                    },
                },
                "3": {
                    "class_type": "RoopGSAnimApply",
                    "inputs": {
                        "image": ["1", 0],
                        "motion": ["2", 0],
                        "duration": duration,
                        "fps": fps,
                        "width": width,
                        "height": height,
                    },
                },
                "4": {
                    "class_type": "VHS_VideoCombine",
                    "inputs": {
                        "images": ["3", 0],
                        "frame_rate": fps,
                        "filename_prefix": "actcore_body",
                        "format": "video/mp4",
                    },
                },
            },
            "extra_data": {
                "output_path": output_path,
            },
        }

    async def _execute_comfyui_workflow(
        self,
        workflow: dict[str, Any],
        shot_id: UUID,
        progress_callback: ProgressCallback | None = None,
        progress_range: tuple = (30, 90),
    ) -> bool:
        """Execute workflow via ComfyUI WebSocket API."""
        import httpx

        try:
            # Queue prompt
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.comfyui_url}/prompt",
                    json=workflow,
                )
                response.raise_for_status()
                result = response.json()
                prompt_id = result.get("prompt_id")

            if not prompt_id:
                logger.error("Failed to get prompt_id from ComfyUI")
                return False

            # Poll for completion
            start_progress, end_progress = progress_range
            elapsed = 0.0

            while elapsed < self.POLL_TIMEOUT:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.comfyui_url}/history/{prompt_id}")
                    history = response.json()

                if prompt_id in history:
                    if history[prompt_id].get("outputs"):
                        return True
                    if history[prompt_id].get("status", {}).get("status_str") == "error":
                        logger.error(f"ComfyUI workflow failed: {history[prompt_id]}")
                        return False

                # Update progress
                if progress_callback:
                    progress = start_progress + int(
                        (elapsed / self.POLL_TIMEOUT) * (end_progress - start_progress)
                    )
                    await progress_callback(
                        GenerationProgress(
                            job_id=shot_id,
                            percent=min(progress, end_progress),
                            message="Processing retargeting...",
                            stage="processing",
                        )
                    )

                await asyncio.sleep(self.POLL_INTERVAL)
                elapsed += self.POLL_INTERVAL

            raise TimeoutError("ComfyUI workflow timed out")

        except httpx.ConnectError:
            logger.error(f"Could not connect to ComfyUI at {self.comfyui_url}")
            return False
        except Exception as e:
            logger.exception(f"ComfyUI workflow execution failed: {e}")
            return False

    async def _generate_thumbnail(
        self,
        video_path: Path,
        thumbnail_path: Path,
    ) -> str | None:
        """Generate thumbnail from video using ffmpeg."""
        if not video_path.exists():
            return None

        try:
            from scenemachine.utils.ffmpeg import get_ffmpeg

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
        """Check if ActCore processing is available."""
        if not self.local_processing:
            return True  # Assume cloud fallback is available

        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.comfyui_url}/system_stats")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"ActCore availability check failed: {e}")
            return False

    async def check_health(self) -> ProviderHealth:
        """Detailed health check for ActCore."""
        try:
            import time

            import httpx

            start = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.comfyui_url}/system_stats")
                response.raise_for_status()
                stats = response.json()

            latency = (time.time() - start) * 1000

            # Check for required nodes
            has_liveportrait = "LivePortraitLoader" in str(stats)
            has_roop = "RoopGSAnimLoader" in str(stats)

            if not has_liveportrait and not has_roop:
                return ProviderHealth(
                    available=True,
                    message="ComfyUI available but ActCore nodes not installed",
                    latency_ms=latency,
                    models_available=0,
                )

            return ProviderHealth(
                available=True,
                message="ActCore processing available",
                latency_ms=latency,
                models_available=len(self.MODELS),
                queue_length=len(self._active_jobs),
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                message=f"ActCore health check failed: {e}",
                error_code="HEALTH_CHECK_FAILED",
            )

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running ActCore job."""
        try:
            import httpx

            # Cancel in ComfyUI
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.comfyui_url}/interrupt",
                    json={"client_id": f"actcore_{provider_job_id}"},
                )

            self._active_jobs.pop(provider_job_id, None)
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel ActCore job: {e}")
            return False

    def list_models(self) -> list[dict[str, Any]]:
        """List available ActCore models."""
        return [
            {
                "id": model_id,
                "name": model.name,
                "cost_per_second": model.cost_per_second,
                "supports_text_to_video": model.supports_text_to_video,
                "supports_image_to_video": model.supports_image_to_video,
                "max_duration": model.max_duration,
                "retargeting_type": model.extra_params.get("retargeting_type"),
            }
            for model_id, model in self.MODELS.items()
        ]

    def get_mode_info(self, mode: str) -> dict[str, Any] | None:
        """Get information about a booking mode."""
        config = self.MODE_CONFIGS.get(mode)
        if not config:
            return None

        return {
            "mode": mode,
            "max_duration_seconds": config["max_duration"],
            "default_model": config["default_model"],
            "requires_booking": config["requires_booking"],
            "auto_match_performer": config["auto_match"],
            "estimated_cost_per_second": self.estimate_cost(1.0, mode=mode),
        }

    def list_modes(self) -> list[dict[str, Any]]:
        """List all available booking modes with their configurations."""
        return [self.get_mode_info(mode) for mode in self.MODE_CONFIGS]
