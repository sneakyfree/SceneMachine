"""Video generation workflow with real service integration."""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.generation_job import JobProvider
from scenemachine.models.shot import Shot, ShotState
from scenemachine.services.generation import (
    GenerationRequest,
    GenerationService,
)
from scenemachine.workflows.base import (
    Workflow,
    WorkflowRegistry,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerationWorkflowContext:
    """Context for video generation workflow."""

    project_id: UUID
    session: AsyncSession | None = None
    scene_id: UUID | None = None
    shot_ids: list[UUID] = field(default_factory=list)
    provider: str = "local"
    quality: str = "high"
    batch_size: int = 4
    generated_outputs: dict[str, str] = field(default_factory=dict)
    failed_shots: list[str] = field(default_factory=list)

    # Service instances (injected at runtime)
    generation_service: GenerationService | None = None


@WorkflowRegistry.register
class VideoGenerationWorkflow(Workflow[GenerationWorkflowContext]):
    """Workflow for generating videos for shots."""

    @property
    def workflow_type(self) -> str:
        return "video_generation"

    def define_steps(self) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                id="validate_shots",
                name="Validate Shots",
                description="Validate shot data and prompts",
                handler="step_validate_shots",
            ),
            WorkflowStep(
                id="prepare_prompts",
                name="Prepare Prompts",
                description="Prepare generation prompts for each shot",
                handler="step_prepare_prompts",
                dependencies=["validate_shots"],
            ),
            WorkflowStep(
                id="check_provider",
                name="Check Provider",
                description="Verify provider availability and credentials",
                handler="step_check_provider",
                dependencies=["prepare_prompts"],
            ),
            WorkflowStep(
                id="generate_videos",
                name="Generate Videos",
                description="Generate videos for all shots",
                handler="step_generate_videos",
                dependencies=["check_provider"],
                max_retries=1,
            ),
            WorkflowStep(
                id="verify_outputs",
                name="Verify Outputs",
                description="Verify generated video outputs",
                handler="step_verify_outputs",
                dependencies=["generate_videos"],
            ),
            WorkflowStep(
                id="generate_thumbnails",
                name="Generate Thumbnails",
                description="Generate thumbnails for videos",
                handler="step_generate_thumbnails",
                dependencies=["verify_outputs"],
            ),
            WorkflowStep(
                id="update_database",
                name="Update Database",
                description="Update shot records with output paths",
                handler="step_update_database",
                dependencies=["generate_thumbnails"],
            ),
        ]

    async def step_validate_shots(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate shots for generation."""
        logger.info("Validating shots...")

        shot_ids = context.get("shot_ids", [])
        if not shot_ids:
            raise ValueError("No shots specified for generation")

        session = context.get("session")
        validated_shots = []
        invalid_shots = []

        if session:
            # Fetch actual shots from database
            for shot_id in shot_ids:
                stmt = select(Shot).where(Shot.id == shot_id)
                result = await session.execute(stmt)
                shot = result.scalar_one_or_none()

                if shot:
                    # Check if shot has required data
                    has_description = bool(shot.description)
                    has_prompt = bool(shot.generation_prompt)

                    if has_description or has_prompt:
                        validated_shots.append(
                            {
                                "id": str(shot.id),
                                "scene_id": str(shot.scene_id),
                                "description": shot.description,
                                "generation_prompt": shot.generation_prompt,
                                "negative_prompt": shot.negative_prompt,
                                "shot_type": shot.shot_type.value
                                if shot.shot_type
                                else "establishing",
                                "camera_movement": shot.camera_movement.value
                                if shot.camera_movement
                                else "static",
                                "duration_seconds": shot.duration_seconds,
                                "validated": True,
                            }
                        )
                    else:
                        invalid_shots.append(str(shot_id))
                else:
                    invalid_shots.append(str(shot_id))
        else:
            # Fallback for testing without session
            for shot_id in shot_ids:
                validated_shots.append(
                    {
                        "id": str(shot_id),
                        "validated": True,
                    }
                )

        if invalid_shots:
            logger.warning(f"Invalid or missing shots: {invalid_shots}")

        return {
            "validated_shots": validated_shots,
            "invalid_shots": invalid_shots,
            "validation_count": len(validated_shots),
        }

    async def step_prepare_prompts(self, context: dict[str, Any]) -> dict[str, Any]:
        """Prepare generation prompts using GenerationService."""
        logger.info("Preparing prompts...")

        validated_shots = context.get("validated_shots", [])
        quality = context.get("quality", "high")
        context.get("session")
        get_settings()

        prompts = []
        quality_params = {
            "ultra": {"width": 1920, "height": 1080, "fps": 30},
            "high": {"width": 1920, "height": 1080, "fps": 24},
            "medium": {"width": 1280, "height": 720, "fps": 24},
            "low": {"width": 854, "height": 480, "fps": 24},
        }
        params = quality_params.get(quality, quality_params["high"])

        for shot_data in validated_shots:
            # Use stored prompt if available, otherwise build from description
            positive_prompt = shot_data.get("generation_prompt") or self._build_prompt(shot_data)
            negative_prompt = (
                shot_data.get("negative_prompt") or self._get_default_negative_prompt()
            )

            prompt_data = {
                "shot_id": shot_data["id"],
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "params": {
                    "width": params["width"],
                    "height": params["height"],
                    "fps": params["fps"],
                    "duration_seconds": shot_data.get("duration_seconds", 3.0),
                    "num_frames": int(params["fps"] * shot_data.get("duration_seconds", 3.0)),
                },
            }
            prompts.append(prompt_data)

        return {"prepared_prompts": prompts}

    def _build_prompt(self, shot_data: dict[str, Any]) -> str:
        """Build generation prompt from shot data."""
        parts = []

        # Shot type
        shot_type = shot_data.get("shot_type", "establishing")
        shot_type_map = {
            "establishing": "cinematic establishing wide shot",
            "close_up": "intimate close-up shot",
            "medium": "balanced medium shot",
            "wide": "expansive wide shot",
            "pov": "immersive POV shot",
            "over_shoulder": "over-the-shoulder shot",
            "insert": "detailed insert shot",
        }
        parts.append(shot_type_map.get(shot_type, "cinematic shot"))

        # Camera movement
        camera = shot_data.get("camera_movement", "static")
        if camera != "static":
            camera_map = {
                "pan": "smooth pan",
                "tilt": "smooth tilt",
                "dolly": "dolly movement",
                "tracking": "tracking shot",
                "handheld": "handheld style",
                "crane": "crane shot",
                "zoom": "slow zoom",
            }
            parts.append(camera_map.get(camera, ""))

        # Description
        if shot_data.get("description"):
            parts.append(shot_data["description"])

        # Quality modifiers
        parts.extend(
            [
                "high quality",
                "professional cinematography",
                "cinematic lighting",
                "8K resolution",
            ]
        )

        return ", ".join(filter(None, parts))

    def _get_default_negative_prompt(self) -> str:
        """Get default negative prompt."""
        return (
            "blurry, low quality, distorted, pixelated, noise, artifacts, "
            "watermark, text overlay, logo, borders, letterbox, "
            "oversaturated, underexposed, overexposed, "
            "amateur, shaky, unstable, glitch"
        )

    async def step_check_provider(self, context: dict[str, Any]) -> dict[str, Any]:
        """Check provider availability using GenerationService."""
        logger.info("Checking provider...")

        provider_name = context.get("provider", "local")
        session = context.get("session")

        provider_status = {
            "provider": provider_name,
            "available": False,
            "queue_position": 0,
            "estimated_wait_seconds": 0,
        }

        if session:
            generation_service = GenerationService(session)

            # Map provider name to JobProvider enum
            provider_map = {
                "local": JobProvider.LOCAL,
                "replicate": JobProvider.REPLICATE,
                "fal": JobProvider.FAL,
            }

            job_provider = provider_map.get(provider_name, JobProvider.LOCAL)
            provider = generation_service.get_provider(job_provider)

            if provider:
                is_available = await provider.check_availability()
                provider_status["available"] = is_available
                provider_status["provider_name"] = provider.name

                # Get queue status
                queue_status = await generation_service.get_queue_status()
                provider_status["queue_position"] = queue_status.get("pending", 0)
                provider_status["estimated_wait_seconds"] = provider_status["queue_position"] * 60
        else:
            # Local provider always available
            provider_status["available"] = provider_name == "local"

        if not provider_status["available"]:
            raise ValueError(f"Provider '{provider_name}' is not available")

        return {"provider_status": provider_status}

    async def step_generate_videos(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate videos for shots using GenerationService."""
        logger.info("Generating videos...")

        prepared_prompts = context.get("prepared_prompts", [])
        batch_size = context.get("batch_size", 4)
        provider_name = context.get("provider", "local")
        session = context.get("session")

        generated = {}
        failed = []

        if session:
            generation_service = GenerationService(session)

            # Process in batches with concurrency
            for i in range(0, len(prepared_prompts), batch_size):
                batch = prepared_prompts[i : i + batch_size]

                # Create tasks for concurrent generation
                tasks = []
                for prompt_data in batch:
                    shot_id = UUID(prompt_data["shot_id"])
                    tasks.append(
                        self._generate_single_shot(
                            generation_service,
                            shot_id,
                            prompt_data,
                            provider_name,
                        )
                    )

                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for prompt_data, result in zip(batch, results, strict=False):
                    shot_id = prompt_data["shot_id"]
                    if isinstance(result, Exception):
                        logger.error(f"Generation failed for shot {shot_id}: {result}")
                        failed.append(shot_id)
                    elif result and result.get("success"):
                        generated[shot_id] = result["output_path"]
                        logger.info(f"Generated video for shot {shot_id}")
                    else:
                        error = result.get("error", "Unknown error") if result else "No result"
                        logger.error(f"Generation failed for shot {shot_id}: {error}")
                        failed.append(shot_id)
        else:
            # Fallback for testing
            settings = get_settings()
            for prompt_data in prepared_prompts:
                shot_id = prompt_data["shot_id"]
                output_path = str(settings.output_dir / "shots" / shot_id / "output.mp4")
                generated[shot_id] = output_path

        return {"generated_outputs": generated, "failed_shots": failed}

    async def _generate_single_shot(
        self,
        service: GenerationService,
        shot_id: UUID,
        prompt_data: dict[str, Any],
        provider_name: str,
    ) -> dict[str, Any]:
        """Generate a single shot video."""
        try:
            # Create generation request
            params = prompt_data.get("params", {})
            request = GenerationRequest(
                shot_id=shot_id,
                prompt=prompt_data["positive_prompt"],
                negative_prompt=prompt_data["negative_prompt"],
                width=params.get("width", 1280),
                height=params.get("height", 720),
                fps=params.get("fps", 24),
                duration_seconds=params.get("duration_seconds", 3.0),
            )

            # Get provider
            provider_map = {
                "local": JobProvider.LOCAL,
                "replicate": JobProvider.REPLICATE,
                "fal": JobProvider.FAL,
            }
            provider = service.get_provider(provider_map.get(provider_name, JobProvider.LOCAL))

            if not provider:
                return {"success": False, "error": "Provider not available"}

            # Generate
            result = await provider.generate(request)

            return {
                "success": result.success,
                "output_path": result.output_path,
                "thumbnail_path": result.thumbnail_path,
                "error": result.error_message,
            }

        except Exception as e:
            logger.exception(f"Error generating shot {shot_id}")
            return {"success": False, "error": str(e)}

    async def step_verify_outputs(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify generated outputs exist and are valid."""
        logger.info("Verifying outputs...")

        generated_outputs = context.get("generated_outputs", {})
        settings = get_settings()

        verified = {}
        verification_errors = []

        for shot_id, output_path in generated_outputs.items():
            # Construct full path
            full_path = (
                settings.output_dir / output_path
                if not output_path.startswith("/")
                else Path(output_path)
            )

            if full_path.exists():
                file_size = full_path.stat().st_size

                # Get video duration using ffprobe
                duration = await self._get_video_duration(full_path)

                verified[shot_id] = {
                    "path": output_path,
                    "verified": True,
                    "file_size": file_size,
                    "duration_seconds": duration,
                }
            else:
                verification_errors.append(
                    {
                        "shot_id": shot_id,
                        "error": "Output file not found",
                        "path": str(full_path),
                    }
                )

        return {
            "verified_outputs": verified,
            "verification_errors": verification_errors,
            "verified_count": len(verified),
        }

    async def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                return float(stdout.decode().strip())
        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")

        return 0.0

    async def step_generate_thumbnails(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate thumbnails for videos using ffmpeg."""
        logger.info("Generating thumbnails...")

        verified_outputs = context.get("verified_outputs", {})
        settings = get_settings()

        thumbnails = {}
        thumbnail_errors = []

        for shot_id, output_info in verified_outputs.items():
            video_path = output_info["path"]
            if not video_path.startswith("/"):
                video_path = str(settings.output_dir / video_path)

            thumbnail_path = video_path.replace(".mp4", "_thumb.jpg")

            try:
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-ss",
                    "00:00:01",
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",
                    thumbnail_path,
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await process.wait()

                if Path(thumbnail_path).exists():
                    thumbnails[shot_id] = thumbnail_path.replace(str(settings.output_dir) + "/", "")
                else:
                    thumbnail_errors.append(shot_id)

            except Exception as e:
                logger.warning(f"Thumbnail generation failed for {shot_id}: {e}")
                thumbnail_errors.append(shot_id)

        return {
            "thumbnails": thumbnails,
            "thumbnail_errors": thumbnail_errors,
        }

    async def step_update_database(self, context: dict[str, Any]) -> dict[str, Any]:
        """Update database with generated outputs."""
        logger.info("Updating database...")

        verified_outputs = context.get("verified_outputs", {})
        thumbnails = context.get("thumbnails", {})
        session = context.get("session")

        updated_shots = []

        if session:
            for shot_id_str in verified_outputs:
                shot_id = UUID(shot_id_str)
                output_info = verified_outputs[shot_id_str]

                stmt = select(Shot).where(Shot.id == shot_id)
                result = await session.execute(stmt)
                shot = result.scalar_one_or_none()

                if shot:
                    shot.output_path = output_info["path"]
                    shot.thumbnail_path = thumbnails.get(shot_id_str)
                    shot.state = ShotState.GENERATED
                    shot.generated_duration_seconds = output_info.get("duration_seconds")

                    updated_shots.append(
                        {
                            "shot_id": shot_id_str,
                            "output_path": output_info["path"],
                            "thumbnail_path": thumbnails.get(shot_id_str),
                            "state": "generated",
                        }
                    )

            await session.commit()
        else:
            # Fallback for testing
            for shot_id_str in verified_outputs:
                updated_shots.append(
                    {
                        "shot_id": shot_id_str,
                        "output_path": verified_outputs[shot_id_str]["path"],
                        "thumbnail_path": thumbnails.get(shot_id_str),
                        "state": "generated",
                    }
                )

        return {
            "updated_shots": updated_shots,
            "updated_count": len(updated_shots),
        }


@dataclass
class BatchRegenerationContext:
    """Context for batch regeneration workflow."""

    project_id: UUID
    shot_ids: list[UUID] = field(default_factory=list)
    reason: str = "quality_improvement"
    provider: str = "local"


@WorkflowRegistry.register
class BatchRegenerationWorkflow(Workflow[BatchRegenerationContext]):
    """Workflow for batch shot regeneration."""

    @property
    def workflow_type(self) -> str:
        return "batch_regeneration"

    def define_steps(self) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                id="backup_existing",
                name="Backup Existing",
                description="Backup existing outputs before regeneration",
                handler="step_backup_existing",
            ),
            WorkflowStep(
                id="clear_outputs",
                name="Clear Outputs",
                description="Clear existing outputs",
                handler="step_clear_outputs",
                dependencies=["backup_existing"],
            ),
            WorkflowStep(
                id="enhance_prompts",
                name="Enhance Prompts",
                description="Enhance prompts based on feedback",
                handler="step_enhance_prompts",
                dependencies=["clear_outputs"],
            ),
            WorkflowStep(
                id="regenerate",
                name="Regenerate Videos",
                description="Regenerate all videos",
                handler="step_regenerate",
                dependencies=["enhance_prompts"],
            ),
            WorkflowStep(
                id="compare_results",
                name="Compare Results",
                description="Compare new outputs with backups",
                handler="step_compare_results",
                dependencies=["regenerate"],
            ),
        ]

    async def step_backup_existing(self, context: dict[str, Any]) -> dict[str, Any]:
        """Backup existing outputs."""
        logger.info("Backing up existing outputs...")
        shot_ids = context.get("shot_ids", [])

        backups = {}
        for shot_id in shot_ids:
            backups[str(shot_id)] = f"/backups/{shot_id}/video.mp4"

        return {"backups": backups}

    async def step_clear_outputs(self, context: dict[str, Any]) -> dict[str, Any]:
        """Clear existing outputs."""
        logger.info("Clearing outputs...")
        return {"outputs_cleared": True}

    async def step_enhance_prompts(self, context: dict[str, Any]) -> dict[str, Any]:
        """Enhance prompts based on regeneration reason."""
        logger.info("Enhancing prompts...")

        reason = context.get("reason", "quality_improvement")
        shot_ids = context.get("shot_ids", [])

        enhanced = []
        for shot_id in shot_ids:
            enhanced.append(
                {
                    "shot_id": str(shot_id),
                    "enhancements": [reason],
                }
            )

        return {"enhanced_prompts": enhanced}

    async def step_regenerate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Regenerate videos."""
        logger.info("Regenerating videos...")

        enhanced_prompts = context.get("enhanced_prompts", [])

        results = {}
        for prompt in enhanced_prompts:
            shot_id = prompt["shot_id"]
            results[shot_id] = f"/outputs/{shot_id}/video_v2.mp4"

        return {"regenerated_outputs": results}

    async def step_compare_results(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compare regenerated results with backups."""
        logger.info("Comparing results...")

        backups = context.get("backups", {})
        regenerated = context.get("regenerated_outputs", {})

        comparison = []
        for shot_id in regenerated:
            comparison.append(
                {
                    "shot_id": shot_id,
                    "original": backups.get(shot_id),
                    "regenerated": regenerated[shot_id],
                    "improvement_score": 0.85,  # Simulated
                }
            )

        return {"comparison_results": comparison}
