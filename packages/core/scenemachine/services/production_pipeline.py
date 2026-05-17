"""Production pipeline service for end-to-end movie generation.

Integrates all components from screenplay to final video:
1. Screenplay parsing and shot list generation
2. Character preparation (references, voices)
3. Blocker resolution
4. Video generation with quality gating
5. Audio generation (TTS)
6. Lip-sync application
7. Assembly into final movie
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class PipelineStage(StrEnum):
    """Pipeline processing stages."""

    INITIALIZED = "initialized"
    PARSING = "parsing"
    SHOT_BREAKDOWN = "shot_breakdown"
    CHARACTER_PREP = "character_prep"
    BLOCKER_CHECK = "blocker_check"
    VIDEO_GENERATION = "video_generation"
    QUALITY_REVIEW = "quality_review"
    AUDIO_GENERATION = "audio_generation"
    LIP_SYNC = "lip_sync"
    ASSEMBLY = "assembly"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class PipelineMode(StrEnum):
    """Pipeline execution modes."""

    FULL_AUTO = "full_auto"  # Run everything automatically
    STEP_BY_STEP = "step_by_step"  # Pause after each stage
    PREVIEW = "preview"  # Generate first scene only
    VALIDATE = "validate"  # Parse and check blockers only


@dataclass
class ShotGenerationStatus:
    """Status of individual shot generation."""

    shot_id: str
    scene_id: str
    status: str  # queued, generating, reviewing, completed, failed
    quality_score: float = 0.0
    regeneration_count: int = 0
    video_path: str | None = None
    audio_path: str | None = None
    error: str | None = None
    # Full per-dimension quality review result (review_video().to_dict()).
    # Populated when the review path runs successfully so the UI / audit
    # view can show which dimensions failed without re-running the
    # (CPU/disk-heavy) review.
    quality_review: dict[str, Any] | None = None


@dataclass
class PipelineProgress:
    """Progress update for pipeline execution."""

    stage: PipelineStage
    percent: float
    message: str
    current_shot: str | None = None
    shots_completed: int = 0
    shots_total: int = 0
    estimated_time_remaining: float | None = None


@dataclass
class PipelineResult:
    """Final result of pipeline execution."""

    project_id: str
    success: bool
    stage: PipelineStage
    output_path: str | None = None
    total_shots: int = 0
    completed_shots: int = 0
    failed_shots: int = 0
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    processing_time_seconds: float = 0.0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    shot_statuses: list[ShotGenerationStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "success": self.success,
            "stage": self.stage.value,
            "output_path": self.output_path,
            "summary": {
                "total_shots": self.total_shots,
                "completed_shots": self.completed_shots,
                "failed_shots": self.failed_shots,
                "total_duration_seconds": self.total_duration_seconds,
                "total_cost_usd": self.total_cost_usd,
                "processing_time_seconds": self.processing_time_seconds,
            },
            "error": self.error,
            "warnings": self.warnings,
        }


# Type for progress callbacks
ProgressCallback = Callable[[PipelineProgress], Any]


class ProductionPipeline:
    """Full production pipeline for screenplay-to-movie generation.

    Implements the DNA strand master plan's end-to-end workflow:
    - Upload a script → Click "Generate Movie" → Download a finished film

    Features:
    - Automatic blocker detection and resolution suggestions
    - Quality gating with regeneration
    - Human approval gates for sensitive operations
    - Cost tracking and budget limits
    - Parallel shot generation
    - Progress streaming
    """

    # Configuration
    DEFAULT_MAX_PARALLEL = 2
    DEFAULT_QUALITY_THRESHOLD = 0.7
    DEFAULT_BUDGET_LIMIT = 100.0  # USD

    def __init__(
        self,
        project_id: str,
        output_dir: Path | None = None,
        max_parallel: int = 2,
        quality_threshold: float = 0.7,
        budget_limit: float = 100.0,
    ) -> None:
        """Initialize the production pipeline.

        Args:
            project_id: Unique project identifier
            output_dir: Directory for output files
            max_parallel: Maximum parallel generations
            quality_threshold: Minimum quality score to pass
            budget_limit: Maximum budget in USD
        """
        self.project_id = project_id
        self.output_dir = output_dir or Path(f"/tmp/scenemachine/projects/{project_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.max_parallel = max_parallel
        self.quality_threshold = quality_threshold
        self.budget_limit = budget_limit

        # State
        self.stage = PipelineStage.INITIALIZED
        self.screenplay_data: dict[str, Any] | None = None
        self.shot_list: dict[str, Any] | None = None
        self.characters: list[dict[str, Any]] = []
        self.blockers: list[dict[str, Any]] = []
        self.shot_statuses: dict[str, ShotGenerationStatus] = {}

        # Tracking
        self.total_cost: float = 0.0
        self.start_time: datetime | None = None

        # Progress callback
        self._progress_callback: ProgressCallback | None = None

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set progress callback for streaming updates."""
        self._progress_callback = callback

    async def _emit_progress(
        self,
        stage: PipelineStage,
        percent: float,
        message: str,
        current_shot: str | None = None,
    ) -> None:
        """Emit progress update."""
        if self._progress_callback:
            progress = PipelineProgress(
                stage=stage,
                percent=percent,
                message=message,
                current_shot=current_shot,
                shots_completed=sum(
                    1 for s in self.shot_statuses.values() if s.status == "completed"
                ),
                shots_total=len(self.shot_statuses),
            )
            await self._progress_callback(progress)

    async def run(
        self,
        screenplay_path: str | Path,
        file_format: str,
        mode: PipelineMode = PipelineMode.FULL_AUTO,
    ) -> PipelineResult:
        """Run the full production pipeline.

        Args:
            screenplay_path: Path to screenplay file
            file_format: File format (fountain, pdf, fdx)
            mode: Execution mode

        Returns:
            PipelineResult with output and statistics
        """
        self.start_time = datetime.utcnow()

        try:
            # Stage 1: Parse screenplay
            await self._emit_progress(PipelineStage.PARSING, 5, "Parsing screenplay...")
            self.stage = PipelineStage.PARSING

            parse_result = await self._parse_screenplay(screenplay_path, file_format)
            if not parse_result:
                return self._failure("Failed to parse screenplay")
            await self._snapshot_stage("after_parse", "Screenplay parsed and structured")

            # Stage 2: Generate shot breakdown
            await self._emit_progress(
                PipelineStage.SHOT_BREAKDOWN, 15, "Generating shot breakdown..."
            )
            self.stage = PipelineStage.SHOT_BREAKDOWN

            shot_result = await self._generate_shot_list()
            if not shot_result:
                return self._failure("Failed to generate shot list")
            await self._snapshot_stage("after_shot_breakdown", "Shot list generated")

            # Stage 3: Check blockers
            await self._emit_progress(PipelineStage.BLOCKER_CHECK, 20, "Checking for blockers...")
            self.stage = PipelineStage.BLOCKER_CHECK

            blockers = await self._check_blockers()

            # Check for critical blockers
            critical_blockers = [b for b in blockers if b.get("severity") == "critical"]
            if critical_blockers:
                return PipelineResult(
                    project_id=self.project_id,
                    success=False,
                    stage=PipelineStage.BLOCKER_CHECK,
                    error=f"{len(critical_blockers)} critical blockers prevent generation",
                    warnings=[b.get("description", "") for b in critical_blockers],
                )

            # If validation mode, stop here
            if mode == PipelineMode.VALIDATE:
                return PipelineResult(
                    project_id=self.project_id,
                    success=True,
                    stage=PipelineStage.BLOCKER_CHECK,
                    total_shots=len(self.shot_statuses),
                    warnings=[
                        b.get("description", "")
                        for b in self.blockers
                        if b.get("severity") in ("high", "medium")
                    ],
                )

            # Stage 4: Prepare characters
            await self._emit_progress(PipelineStage.CHARACTER_PREP, 25, "Preparing characters...")
            self.stage = PipelineStage.CHARACTER_PREP

            await self._prepare_characters()
            await self._snapshot_stage("after_character_prep", "Characters prepared")

            # Stage 5: Generate videos
            await self._emit_progress(PipelineStage.VIDEO_GENERATION, 30, "Generating videos...")
            self.stage = PipelineStage.VIDEO_GENERATION

            # If preview mode, only do first scene
            shots_to_generate = list(self.shot_statuses.values())
            if mode == PipelineMode.PREVIEW:
                shots_to_generate = shots_to_generate[:3]  # First 3 shots

            await self._generate_videos(shots_to_generate)
            await self._snapshot_stage("after_video_generation", "Videos generated")

            # Stage 6: Generate audio
            await self._emit_progress(PipelineStage.AUDIO_GENERATION, 70, "Generating audio...")
            self.stage = PipelineStage.AUDIO_GENERATION

            await self._generate_audio(shots_to_generate)

            # Stage 7: Apply lip sync
            await self._emit_progress(PipelineStage.LIP_SYNC, 80, "Applying lip sync...")
            self.stage = PipelineStage.LIP_SYNC

            await self._apply_lip_sync(shots_to_generate)

            # Stage 8: Assembly
            await self._emit_progress(PipelineStage.ASSEMBLY, 90, "Assembling final video...")
            self.stage = PipelineStage.ASSEMBLY

            output_path = await self._assemble_movie(shots_to_generate)
            await self._snapshot_stage("after_assembly", "Final movie assembled")

            # Complete
            self.stage = PipelineStage.COMPLETED
            await self._emit_progress(PipelineStage.COMPLETED, 100, "Complete!")

            processing_time = (datetime.utcnow() - self.start_time).total_seconds()

            return PipelineResult(
                project_id=self.project_id,
                success=True,
                stage=PipelineStage.COMPLETED,
                output_path=output_path,
                total_shots=len(self.shot_statuses),
                completed_shots=sum(
                    1 for s in self.shot_statuses.values() if s.status == "completed"
                ),
                failed_shots=sum(1 for s in self.shot_statuses.values() if s.status == "failed"),
                total_cost_usd=self.total_cost,
                processing_time_seconds=processing_time,
                shot_statuses=list(self.shot_statuses.values()),
            )

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            return self._failure(str(e))

    async def _snapshot_stage(self, label: str, description: str) -> None:
        """Persist an immutable snapshot at a stage boundary.

        Each stage transition captures the in-memory project state
        (screenplay_data, shot_list, characters, shot_statuses) so the
        Audit view can reconstruct exactly what the pipeline knew at
        every milestone. Best-effort — a snapshot failure must never
        kill an in-flight pipeline. Loud log, no swallow.

        Wired during the 2026-05-14 audit (exec summary item #3): the
        Audit view in the explainability dashboard was silently empty
        because no caller was creating snapshots. The
        ``SnapshotService.create_snapshot`` method existed but had no
        invocations anywhere in the codebase.
        """
        try:
            from uuid import UUID as _UUID

            from scenemachine.services.snapshots import SnapshotService

            try:
                project_uuid = _UUID(str(self.project_id))
            except (ValueError, AttributeError):
                # project_id isn't a UUID (e.g. test harness uses
                # synthetic string ids). Skip snapshot rather than fake
                # one — the audit log would be misleading.
                logger.debug("snapshot: skipping non-UUID project_id=%s", self.project_id)
                return

            shots_data: list[dict[str, Any]] = []
            for s in self.shot_statuses.values():
                shots_data.append(
                    {
                        "shot_id": s.shot_id,
                        "scene_id": s.scene_id,
                        "status": s.status,
                        "quality_score": s.quality_score,
                        "video_path": s.video_path,
                        "audio_path": s.audio_path,
                        "error": s.error,
                    }
                )

            service = SnapshotService()
            snap = await service.create_snapshot(
                project_id=project_uuid,
                project_data={
                    "project_id": str(self.project_id),
                    "stage": self.stage.value,
                    "total_cost_usd": self.total_cost,
                },
                scenes_data=(self.shot_list or {}).get("scenes", []),
                characters_data=self.characters or [],
                shots_data=shots_data,
                label=label,
                description=description,
            )
            logger.info(
                "snapshot %s: %s (%d shots, %d chars, %d scenes)",
                snap.id,
                label,
                len(shots_data),
                len(self.characters or []),
                len((self.shot_list or {}).get("scenes", [])),
            )
        except Exception as e:  # pragma: no cover — defensive
            # Best-effort. Per feedback_no_silent_fallbacks: loud log, no swallow.
            logger.exception(
                "snapshot creation failed at stage %s (label=%s): %s "
                "— pipeline continues; audit history will be incomplete",
                self.stage.value,
                label,
                e,
            )

    def _failure(self, error: str) -> PipelineResult:
        """Create failure result."""
        processing_time = 0.0
        if self.start_time:
            processing_time = (datetime.utcnow() - self.start_time).total_seconds()

        return PipelineResult(
            project_id=self.project_id,
            success=False,
            stage=self.stage,
            error=error,
            processing_time_seconds=processing_time,
            shot_statuses=list(self.shot_statuses.values()),
        )

    async def _parse_screenplay(
        self,
        path: str | Path,
        format: str,
    ) -> bool:
        """Parse screenplay file."""
        try:
            from scenemachine.parsers import FDXParser, FountainParser, PDFParser

            path = Path(path)

            if format.lower() == "fountain":
                with open(path) as f:
                    parser = FountainParser()
                    self.screenplay_data = parser.parse(f.read())
            elif format.lower() == "pdf":
                parser = PDFParser()
                self.screenplay_data = parser.parse(str(path))
            elif format.lower() == "fdx":
                parser = FDXParser()
                self.screenplay_data = parser.parse(str(path))
            else:
                return False

            return self.screenplay_data is not None

        except Exception as e:
            logger.exception(f"Parse error: {e}")
            return False

    async def _generate_shot_list(self) -> bool:
        """Generate shot breakdown."""
        try:
            from scenemachine.services.shot_list_generator import ShotListGenerator

            generator = ShotListGenerator()
            self.shot_list = generator.generate(self.screenplay_data)

            # Initialize shot statuses
            for scene in self.shot_list.get("scenes", []):
                for shot in scene.get("shots", []):
                    shot_id = shot.get("shot_id")
                    self.shot_statuses[shot_id] = ShotGenerationStatus(
                        shot_id=shot_id,
                        scene_id=scene.get("scene_number", ""),
                        status="queued",
                    )

            return True

        except Exception as e:
            logger.exception(f"Shot list error: {e}")
            return False

    async def _check_blockers(self) -> list[dict[str, Any]]:
        """Check for generation blockers."""
        try:
            from scenemachine.services.blockers_engine import BlockersEngine

            engine = BlockersEngine()

            shots = [
                shot
                for scene in self.shot_list.get("scenes", [])
                for shot in scene.get("shots", [])
            ]

            result = engine.analyze_project(
                characters=self.characters,
                scenes=self.shot_list.get("scenes", []),
                shots=shots,
            )

            self.blockers = result.get("blockers", [])
            return self.blockers

        except Exception as e:
            logger.exception(f"Blocker check error: {e}")
            return []

    async def _prepare_characters(self) -> None:
        """Prepare character references and voices."""
        # Extract characters from shot list
        self.characters = self.shot_list.get("characters", [])

        # In production, would generate reference images and assign voices
        logger.info(f"Prepared {len(self.characters)} characters")

    async def _generate_videos(
        self,
        shots: list[ShotGenerationStatus],
    ) -> None:
        """Generate videos for shots, routing each through StackRouter.

        Shots are grouped by scene_id and processed **sequentially within
        a scene** so the previous shot's last frame is available to seed
        the next shot via I2V (StackRouter routing rule #3). Scenes run
        in parallel up to ``self.max_parallel`` concurrent scenes.

        After a shot succeeds, its last frame is extracted via ffmpeg
        into the ComfyUI input directory and passed as
        ``prev_shot_last_frame`` to ``route_shot`` for the next shot in
        the same scene. The router picks I2V whenever this frame is
        available AND the shot has no character references (which would
        otherwise route to Animate — character ID outranks continuity).
        """
        from scenemachine.config import get_settings
        from scenemachine.generators.base import (
            GenerationRequest,
            get_provider_registry,
        )
        from scenemachine.models.generation_job import JobProvider
        from scenemachine.services.stack_router import route_shot
        from scenemachine.services.video_quality_reviewer import get_video_quality_reviewer

        reviewer = get_video_quality_reviewer()

        # Scene-level concurrency: each scene's shots run sequentially
        # (for continuity), but multiple scenes can run concurrently.
        scene_semaphore = asyncio.Semaphore(self.max_parallel)

        # Resolve provider ONCE from the global registry (no per-shot import
        # churn). Loud failure here is correct — the silent placeholder
        # fallback the previous implementation had was the root cause of
        # ~every prior "the pipeline ran but the videos are empty" report.
        provider_type = JobProvider.LOCAL
        registry = get_provider_registry()
        provider_impl = registry.get_provider(provider_type)
        if provider_impl is None:
            available = sorted(p.value for p in registry.list_providers())
            err = (
                f"No {provider_type.value} provider registered. "
                f"Available: {available or '(none)'}. "
                "Ensure ProviderRegistry was set up at startup."
            )
            logger.error(err)
            for shot in shots:
                shot.status = "failed"
                shot.error = err
            return

        # Build a stable character_id -> reference_image_path map from
        # whatever the earlier pipeline stage prepared.
        character_ref_paths: dict[str, str] = {}
        for c in self.characters or []:
            cid = c.get("id") or c.get("character_id")
            ref = c.get("reference_image_path") or c.get("ref_image")
            if cid and ref:
                character_ref_paths[str(cid)] = str(ref)

        settings = get_settings()
        comfyui_input_dir = Path(
            getattr(settings, "comfyui_input_dir", None) or "/opt/ai/comfyui/input"
        )
        comfyui_input_dir.mkdir(parents=True, exist_ok=True)

        async def extract_last_frame(
            video_path: str, shot_id: str, duration_s: float
        ) -> str | None:
            """Extract the last frame of the shot's mp4 into ComfyUI's input
            dir. Returns the filename (relative to ComfyUI input dir) on
            success, None on failure. Failure is logged but never raised —
            continuity is best-effort; if the frame extraction fails the
            next shot just falls back to T2V routing.
            """
            try:
                from scenemachine.utils.ffmpeg import get_ffmpeg

                ffmpeg = get_ffmpeg()
                vp = Path(video_path)
                if not vp.exists():
                    logger.warning("continuity: source mp4 missing: %s", vp)
                    return None
                fname = f"continuity_{shot_id}.jpg"
                out = comfyui_input_dir / fname
                # Negative timestamp = "0.1 s before EOF" — robust to the
                # container vs frames/fps duration mismatch that bit us
                # during the 2026-05-14 overnight RADAR_LOVE_2 +
                # IMPOSSIBLE_FULL run: requested duration_s was 3.0 but
                # av1_nvenc container duration was 2.875, so the prior
                # ``duration_s - 0.1 = 2.9`` landed past EOF and produced
                # an empty jpg. Result: every continuity extraction
                # silently failed and the I2V routing path was dead in
                # practice. ``-sseof -0.1`` doesn't need the actual
                # duration; ffmpeg handles the seek-from-end math.
                await ffmpeg.extract_frame(
                    video_path=vp,
                    output_path=out,
                    timestamp=-0.1,
                    quality=2,
                )
                logger.info("continuity: extracted last frame -> %s", out)
                return fname
            except Exception as e:
                logger.warning(
                    "continuity frame extraction failed for shot %s: %s "
                    "(next shot will route T2V instead of I2V)",
                    shot_id,
                    e,
                )
                return None

        # Group shots by scene_id so we can process each scene's shots
        # sequentially. Preserve the original order within each scene
        # (the shot_list generator already sorts by sequence_number).
        scenes_to_shots: dict[str, list[ShotGenerationStatus]] = {}
        for shot in shots:
            scenes_to_shots.setdefault(shot.scene_id or "_no_scene_", []).append(shot)

        async def generate_shot(
            shot: ShotGenerationStatus,
            prev_shot_last_frame: str | None,
        ) -> str | None:
            """Generate one shot. Returns the next shot's
            ``prev_shot_last_frame`` (None if generation failed or last-frame
            extraction failed — both are treated as no-continuity).
            """
            shot.status = "generating"
            shot_index = shots.index(shot)
            await self._emit_progress(
                PipelineStage.VIDEO_GENERATION,
                30 + (40 * shot_index / len(shots)),
                f"Generating shot {shot.shot_id}",
                current_shot=shot.shot_id,
            )

            try:
                shot_data = self._get_shot_data(shot.shot_id)
                if not shot_data:
                    shot.status = "failed"
                    shot.error = "Shot data not found in shot list"
                    return None

                prompt = self._build_generation_prompt(shot_data)

                # Pick the right stack for this shot — now WITH continuity
                # from the previous shot's last frame when available.
                decision = route_shot(
                    shot_data,
                    prev_shot_last_frame=prev_shot_last_frame,
                    character_ref_paths=character_ref_paths,
                )

                # Build the provider-facing request.
                try:
                    shot_uuid = UUID(str(shot.shot_id))
                except (ValueError, AttributeError):
                    shot_uuid = uuid4()

                extra_params = {"model_id": decision.model_id}
                extra_params.update(decision.extra_params or {})
                shot_extra = shot_data.get("extra_params")
                if isinstance(shot_extra, dict):
                    extra_params.update(shot_extra)

                # Plumb num_inference_steps + guidance_scale from shot_data
                # when present. Previously these always took the dataclass
                # defaults (50 steps, 7.5 cfg) which silently overrode any
                # per-shot or per-model preference. Found during 2026-05-14
                # overnight RADAR_LOVE_2 run when a launcher-level step
                # reduction wasn't reaching the workflow.
                _steps = shot_data.get("num_inference_steps")
                _cfg = shot_data.get("guidance_scale")
                _req_kwargs = {}
                if _steps is not None:
                    _req_kwargs["num_inference_steps"] = int(_steps)
                if _cfg is not None:
                    _req_kwargs["guidance_scale"] = float(_cfg)

                request = GenerationRequest(
                    shot_id=shot_uuid,
                    prompt=prompt,
                    negative_prompt=shot_data.get("negative_prompt", "") or "",
                    width=int(shot_data.get("width", 768)),
                    height=int(shot_data.get("height", 432)),
                    fps=int(shot_data.get("fps", 24)),
                    duration_seconds=float(shot_data.get("duration_seconds", 3.0)),
                    seed=shot_data.get("seed"),
                    input_image_path=decision.input_image_path,
                    character_references=decision.character_references,
                    extra_params=extra_params,
                    **_req_kwargs,
                )

                logger.info(
                    "shot %s -> %s (%s)",
                    shot.shot_id,
                    decision.model_id,
                    decision.reason,
                )

                # Real provider call — no silent fallback. If the provider
                # fails, the failure surfaces on the shot.
                result = await provider_impl.generate(request)

                if not result.success:
                    shot.status = "failed"
                    shot.error = result.error_message or (
                        f"provider returned success=False (code={result.error_code})"
                    )
                    logger.warning(
                        "shot %s generation failed: %s",
                        shot.shot_id,
                        shot.error,
                    )
                    return None

                # Provider returns settings-dir-relative output_path
                # (e.g. "shots/<uuid>/output.mp4"). Resolve to absolute.
                if result.output_path:
                    abs_path = settings.output_dir / result.output_path
                    shot.video_path = str(abs_path)
                self.total_cost += float(result.cost_usd or 0.0)
                shot.quality_score = (result.metadata or {}).get("quality_score", 0.8)

                # Quality review (regeneration loop). Pre-2026-05-14 this
                # path was a silent no-op: review_video returns a
                # VideoReviewResult dataclass and the old code accessed
                # it as if it were a dict, raising AttributeError on
                # every call which got swallowed by the bare except.
                # Per the feedback_no_silent_fallbacks rule earned the
                # same day, this now correctly reads the dataclass and
                # surfaces any review failure at WARNING level.
                if shot.video_path and Path(shot.video_path).exists():
                    try:
                        # Pull prompt + character references off shot_data
                        # so the 7 review dimensions get real signal where
                        # they can. char_refs is optional and currently
                        # absent in V0 — the metric handles None gracefully.
                        char_refs = shot_data.get("character_references")
                        prompt_text = shot_data.get("prompt") or shot_data.get("description") or ""
                        review = await reviewer.review_video(
                            shot.video_path,
                            prompt=prompt_text,
                            character_references=char_refs,
                            regeneration_count=shot.regeneration_count,
                        )
                        shot.quality_score = review.overall_score
                        # Cache the full per-dimension breakdown on the shot
                        # so the UI / audit view can show what failed and
                        # why. Avoids re-running the (expensive) review.
                        with contextlib.suppress(Exception):
                            shot.quality_review = review.to_dict()
                        if (
                            shot.quality_score < self.quality_threshold
                            and shot.regeneration_count < 2
                        ):
                            shot.regeneration_count += 1
                            logger.info(
                                "shot %s quality %.3f below threshold %.3f, "
                                "regenerating (attempt %s, issues=%s)",
                                shot.shot_id,
                                shot.quality_score,
                                self.quality_threshold,
                                shot.regeneration_count,
                                [i.get("issue") for i in (review.issues or [])][:5],
                            )
                            # Re-run with the same prev_shot_last_frame
                            return await generate_shot(shot, prev_shot_last_frame)
                    except Exception as review_err:
                        # Was logger.debug pre-fix — silent failure. Now
                        # WARNING so a real review crash surfaces. Pipeline
                        # continues with the provider-reported quality
                        # score (which lacks our 3 real measurements).
                        logger.warning(
                            "quality review failed for shot %s: %s; "
                            "falling back to provider-reported score %.3f",
                            shot.shot_id,
                            review_err,
                            shot.quality_score,
                            exc_info=True,
                        )

                shot.status = "completed"

                # Extract last frame for the NEXT shot's continuity. Done
                # AFTER quality review so we don't waste extraction on a
                # shot that's about to be regenerated.
                if shot.video_path:
                    return await extract_last_frame(
                        shot.video_path,
                        str(shot.shot_id),
                        float(shot_data.get("duration_seconds", 3.0)),
                    )
                return None

            except Exception as e:
                logger.exception("failed to generate shot %s", shot.shot_id)
                shot.status = "failed"
                shot.error = str(e)
                return None

        async def generate_scene(
            scene_id: str,
            scene_shots: list[ShotGenerationStatus],
        ) -> None:
            """Process one scene's shots SEQUENTIALLY so each can seed the
            next via I2V continuity. Scenes run in parallel up to
            ``self.max_parallel`` concurrent scenes."""
            async with scene_semaphore:
                prev_frame: str | None = None
                for shot in scene_shots:
                    prev_frame = await generate_shot(shot, prev_frame)

        await asyncio.gather(
            *[
                generate_scene(scene_id, scene_shots)
                for scene_id, scene_shots in scenes_to_shots.items()
            ]
        )

    async def _generate_audio(
        self,
        shots: list[ShotGenerationStatus],
    ) -> None:
        """Generate dialogue audio for shots using AudioService."""
        try:
            from scenemachine.db import get_db_manager
            from scenemachine.services.audio import AudioService, TTSProvider

            db_manager = get_db_manager()

            async with db_manager.session() as session:
                audio_service = AudioService(session)
                await audio_service.initialize_providers()

                # Determine best available TTS provider
                available = await audio_service.get_available_providers()
                tts_provider = TTSProvider.MOCK

                for pref in [TTSProvider.ELEVENLABS, TTSProvider.OPENAI, TTSProvider.MOCK]:
                    if any(p["provider"] == pref.value and p["available"] for p in available):
                        tts_provider = pref
                        break

                logger.info(f"Using TTS provider: {tts_provider.value}")

                for shot in shots:
                    shot_data = self._get_shot_data(shot.shot_id)

                    if shot_data and shot_data.get("dialogue"):
                        dialogue = shot_data["dialogue"]
                        text = dialogue.get("text", "")

                        if not text.strip():
                            continue

                        # Use character voice if assigned, otherwise default
                        voice_id = dialogue.get("voice_id", "mock-male-1")

                        try:
                            result = await audio_service.generate_speech(
                                text=text,
                                voice_id=voice_id,
                                provider=tts_provider,
                                speed=dialogue.get("speed", 1.0),
                            )

                            if result.success:
                                shot.audio_path = result.audio_path
                                self.total_cost += result.cost_usd or 0.0
                            else:
                                logger.warning(
                                    f"TTS failed for shot {shot.shot_id}: {result.error_message}"
                                )
                        except Exception as tts_err:
                            logger.warning(f"TTS error for shot {shot.shot_id}: {tts_err}")

        except Exception as e:
            logger.warning(f"Audio generation stage failed (non-fatal): {e}")
            # Audio generation failure is non-fatal; pipeline continues without dialogue

    async def _apply_lip_sync(
        self,
        shots: list[ShotGenerationStatus],
    ) -> None:
        """Apply lip sync to shots that have both audio and video."""
        try:
            from scenemachine.services.lipsync import LipSyncProvider, get_lip_sync_service

            service = get_lip_sync_service()
            await service.initialize_providers()

            # Determine best available lip sync provider
            available = await service.get_available_providers()
            ls_provider = LipSyncProvider.MOCK

            for pref in [LipSyncProvider.LATENTSYNC, LipSyncProvider.RHUBARB, LipSyncProvider.MOCK]:
                if any(p["provider"] == pref.value and p["available"] for p in available):
                    ls_provider = pref
                    break

            logger.info(f"Using lip sync provider: {ls_provider.value}")

            for shot in shots:
                if shot.audio_path and shot.video_path:
                    try:
                        output_path = str(
                            Path(shot.video_path).parent
                            / f"{Path(shot.video_path).stem}_lipsync.mp4"
                        )

                        result = await service.apply_to_video(
                            video_path=shot.video_path,
                            audio_path=shot.audio_path,
                            output_path=output_path,
                            provider=ls_provider,
                        )

                        if result.success and result.output_video_path:
                            shot.video_path = result.output_video_path
                            logger.info(f"Applied lip sync to shot {shot.shot_id}")
                        else:
                            logger.warning(
                                f"Lip sync failed for {shot.shot_id}: {result.error_message}"
                            )
                    except Exception as ls_err:
                        logger.warning(f"Lip sync error for {shot.shot_id}: {ls_err}")

        except Exception as e:
            logger.warning(f"Lip sync stage failed (non-fatal): {e}")

    async def _assemble_movie(
        self,
        shots: list[ShotGenerationStatus],
    ) -> str:
        """Assemble final movie from shots using ffmpeg concat.

        Tries two strategies in order:
          1. concat demuxer with ``-c copy`` (fast, lossless, ~2000× realtime)
          2. concat filter with libx264 re-encode (slow but tolerant of
             stream-level inconsistencies that break the demuxer)

        On both failures, returns an empty mp4 with a loud error rather than
        the previous silent "fallback to first shot" behavior, which was
        misleading: a 47-shot run that 'finished' with a 3-second mp4
        masquerading as the final movie.

        Found 2026-05-14 overnight: the demuxer path returned non-zero from
        ``asyncio.create_subprocess_exec`` in production while the literally
        identical command succeeded from a shell. Manual concat after the
        fact recovered the real movie. The re-encode filter fallback below
        means future runs degrade to slow-but-correct instead of fast-but-
        wrong, and the full stderr is logged so the next operator can see
        what ffmpeg actually complained about.
        """
        output_path = self.output_dir / f"output_{self.project_id}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        video_paths = [
            shot.video_path
            for shot in shots
            if shot.status == "completed" and shot.video_path and Path(shot.video_path).exists()
        ]

        if not video_paths:
            logger.warning("No completed shot videos to assemble")
            output_path.write_bytes(b"")
            return str(output_path)

        if len(video_paths) == 1:
            import shutil

            shutil.copy2(video_paths[0], output_path)
            logger.info(f"Single shot assembled: {output_path}")
            return str(output_path)

        # Strategy 1: concat demuxer with stream copy (fast path)
        concat_file = self.output_dir / "concat_list.txt"
        try:
            with open(concat_file, "w") as f:
                for vp in video_paths:
                    escaped = vp.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            demuxer_cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(output_path),
            ]
            logger.info(
                "assembling %d shots via concat demuxer (-c copy) -> %s",
                len(video_paths),
                output_path,
            )
            proc = await asyncio.create_subprocess_exec(
                *demuxer_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                logger.info(
                    "assembled %d shots into %s (concat demuxer)",
                    len(video_paths),
                    output_path,
                )
                return str(output_path)

            stderr_text = stderr.decode(errors="replace")
            logger.error(
                "concat demuxer FAILED (rc=%s); full stderr (last 4 KB):\n%s",
                proc.returncode,
                stderr_text[-4096:],
            )

            # Strategy 2: concat FILTER with libx264 re-encode (slow but
            # tolerant). Builds an inline filter graph instead of an external
            # listing — no concat_list.txt path quoting concerns. CPU encode
            # so it doesn't fight the GPU pipeline for VRAM.
            n = len(video_paths)
            input_args: list[str] = []
            for vp in video_paths:
                input_args.extend(["-i", vp])
            stream_specs = "".join(f"[{i}:v:0]" for i in range(n))
            filter_complex = f"{stream_specs}concat=n={n}:v=1:a=0[outv]"
            filter_cmd = [
                "ffmpeg",
                "-y",
                *input_args,
                "-filter_complex",
                filter_complex,
                "-map",
                "[outv]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ]
            logger.info(
                "retrying assembly via concat filter + libx264 re-encode "
                "(slow but tolerant of stream-level mismatches)",
            )
            proc2 = await asyncio.create_subprocess_exec(
                *filter_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr2 = await proc2.communicate()

            if proc2.returncode == 0:
                logger.info(
                    "assembled %d shots into %s (concat filter re-encode)",
                    len(video_paths),
                    output_path,
                )
                return str(output_path)

            logger.error(
                "concat filter re-encode ALSO failed (rc=%s); stderr (last 4 KB):\n%s",
                proc2.returncode,
                stderr2.decode(errors="replace")[-4096:],
            )
            # No silent first-shot fallback — write an empty placeholder so
            # the caller sees the failure clearly instead of getting a 3-sec
            # movie that looks like success.
            output_path.write_bytes(b"")

        except Exception as e:
            logger.exception("Assembly error: %s", e)
            output_path.write_bytes(b"")
        finally:
            concat_file.unlink(missing_ok=True)

        return str(output_path)

    def _build_generation_prompt(self, shot_data: dict[str, Any]) -> str:
        """Build a video generation prompt from shot data.

        Combines shot description, camera movement, characters, and mood
        into a cohesive prompt for the video generation provider.
        """
        parts = []

        # Core shot description
        description = shot_data.get("description", "")
        if description:
            parts.append(description)

        # Camera information
        shot_type = shot_data.get("shot_type", "")
        camera_movement = shot_data.get("camera_movement", "")
        camera_angle = shot_data.get("camera_angle", "")

        camera_parts = [p for p in [shot_type, camera_movement, camera_angle] if p]
        if camera_parts:
            parts.append(f"Camera: {', '.join(camera_parts)}")

        # Characters in shot
        characters = shot_data.get("characters", [])
        if characters:
            char_names = [c.get("name", c) if isinstance(c, dict) else str(c) for c in characters]
            parts.append(f"Characters: {', '.join(char_names)}")

        # Mood/atmosphere
        mood = shot_data.get("mood", "") or shot_data.get("atmosphere", "")
        if mood:
            parts.append(f"Mood: {mood}")

        # Lighting
        lighting = shot_data.get("lighting", "")
        if lighting:
            parts.append(f"Lighting: {lighting}")

        return ". ".join(parts) if parts else "A cinematic shot"

    def _get_shot_data(self, shot_id: str) -> dict[str, Any] | None:
        """Get shot data from shot list."""
        if not self.shot_list:
            return None

        for scene in self.shot_list.get("scenes", []):
            for shot in scene.get("shots", []):
                if shot.get("shot_id") == shot_id:
                    return shot

        return None

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline status."""
        return {
            "project_id": self.project_id,
            "stage": self.stage.value,
            "shots": {
                shot_id: {
                    "status": status.status,
                    "quality_score": status.quality_score,
                    "regeneration_count": status.regeneration_count,
                }
                for shot_id, status in self.shot_statuses.items()
            },
            "total_cost": self.total_cost,
            "budget_remaining": self.budget_limit - self.total_cost,
        }


def create_production_pipeline(
    project_id: str,
    **kwargs,
) -> ProductionPipeline:
    """Create a new production pipeline instance."""
    return ProductionPipeline(project_id, **kwargs)
