"""Video quality review and scoring service.

Implements the DNA strand master plan's Reviewer Agent capabilities:
- Quality scoring across multiple dimensions
- Physics/consistency checking
- Human escalation triggers
- Regeneration recommendations
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """Quality assessment dimensions."""
    VISUAL_FIDELITY = "visual_fidelity"       # Overall visual quality
    MOTION_COHERENCE = "motion_coherence"      # Natural movement
    CHARACTER_CONSISTENCY = "character_consistency"  # Face/body match
    PROMPT_ADHERENCE = "prompt_adherence"      # Matches description
    TEMPORAL_STABILITY = "temporal_stability"   # No flickering
    PHYSICS_PLAUSIBILITY = "physics_plausibility"  # Realistic physics
    LIGHTING_CONSISTENCY = "lighting_consistency"  # Stable lighting
    AUDIO_SYNC = "audio_sync"                   # Lip sync accuracy


class QualityIssue(str, Enum):
    """Types of quality issues."""
    LOW_RESOLUTION = "low_resolution"
    BLURRY_FRAMES = "blurry_frames"
    FACE_DISTORTION = "face_distortion"
    CHARACTER_DRIFT = "character_drift"
    TEMPORAL_FLICKERING = "temporal_flickering"
    UNNATURAL_MOTION = "unnatural_motion"
    PHYSICS_VIOLATION = "physics_violation"
    LIGHTING_CHANGE = "lighting_change"
    WRONG_CONTENT = "wrong_content"
    MISSING_ELEMENT = "missing_element"
    EXTRA_ELEMENT = "extra_element"
    LIP_SYNC_MISMATCH = "lip_sync_mismatch"
    HAND_ARTIFACT = "hand_artifact"


class EscalationReason(str, Enum):
    """Reasons for escalating to human review."""
    QUALITY_BELOW_THRESHOLD = "quality_below_threshold"
    MULTIPLE_REGENERATIONS = "multiple_regenerations"
    SENSITIVE_CONTENT = "sensitive_content"
    BUDGET_THRESHOLD = "budget_threshold"
    NOVEL_SCENARIO = "novel_scenario"


@dataclass
class QualityScore:
    """Quality score for a single dimension."""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    issues: List[QualityIssue] = field(default_factory=list)
    notes: str = ""


@dataclass 
class VideoReviewResult:
    """Complete review result for a video."""
    video_path: str
    shot_id: Optional[str] = None
    overall_score: float = 0.0
    dimension_scores: List[QualityScore] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    passed: bool = True
    requires_escalation: bool = False
    escalation_reason: Optional[EscalationReason] = None
    recommendations: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_path": self.video_path,
            "shot_id": self.shot_id,
            "overall_score": self.overall_score,
            "dimension_scores": [
                {
                    "dimension": s.dimension.value,
                    "score": s.score,
                    "confidence": s.confidence,
                    "issues": [i.value for i in s.issues],
                    "notes": s.notes,
                }
                for s in self.dimension_scores
            ],
            "issues": self.issues,
            "passed": self.passed,
            "requires_escalation": self.requires_escalation,
            "escalation_reason": self.escalation_reason.value if self.escalation_reason else None,
            "recommendations": self.recommendations,
            "processing_time_seconds": self.processing_time_seconds,
            "metadata": self.metadata,
        }


class VideoQualityReviewer:
    """Service for reviewing video quality and triggering escalations.
    
    Implements the DNA strand master plan's:
    - Quality gating before assembly
    - Physics check
    - Human escalation for edge cases
    - Adaptive thresholds based on context
    """
    
    # Thresholds
    PASS_THRESHOLD = 0.7
    ESCALATION_THRESHOLD = 0.5
    MAX_REGENERATIONS = 3
    
    # Quality tier definitions for adaptive thresholds
    QUALITY_TIERS = {
        "draft": {
            "pass_threshold": 0.55,
            "escalation_threshold": 0.35,
            "max_regenerations": 2,
            "description": "Quick preview, lower standards"
        },
        "preview": {
            "pass_threshold": 0.65,
            "escalation_threshold": 0.45,
            "max_regenerations": 3,
            "description": "Review quality, moderate standards"
        },
        "production": {
            "pass_threshold": 0.75,
            "escalation_threshold": 0.55,
            "max_regenerations": 4,
            "description": "Final output, high standards"
        },
        "master": {
            "pass_threshold": 0.85,
            "escalation_threshold": 0.65,
            "max_regenerations": 5,
            "description": "Theatrical quality, strict standards"
        },
    }
    
    # Weights for overall score calculation
    DIMENSION_WEIGHTS = {
        QualityDimension.VISUAL_FIDELITY: 0.20,
        QualityDimension.MOTION_COHERENCE: 0.15,
        QualityDimension.CHARACTER_CONSISTENCY: 0.20,
        QualityDimension.PROMPT_ADHERENCE: 0.15,
        QualityDimension.TEMPORAL_STABILITY: 0.10,
        QualityDimension.PHYSICS_PLAUSIBILITY: 0.10,
        QualityDimension.LIGHTING_CONSISTENCY: 0.05,
        QualityDimension.AUDIO_SYNC: 0.05,
    }
    
    def __init__(
        self,
        pass_threshold: float = 0.7,
        max_regenerations: int = 3,
    ):
        """Initialize the quality reviewer.
        
        Args:
            pass_threshold: Minimum score to pass review
            max_regenerations: Max regenerations before escalation
        """
        self.pass_threshold = pass_threshold
        self.max_regenerations = max_regenerations
    
    async def review_video(
        self,
        video_path: Union[str, Path],
        prompt: str = "",
        character_references: Optional[List[str]] = None,
        audio_path: Optional[str] = None,
        regeneration_count: int = 0,
    ) -> VideoReviewResult:
        """Review a generated video for quality.
        
        Args:
            video_path: Path to video file
            prompt: Original generation prompt
            character_references: Paths to character reference images
            audio_path: Optional audio file for sync checking
            regeneration_count: Number of previous regenerations
            
        Returns:
            VideoReviewResult with scores and recommendations
        """
        import time
        start_time = time.time()
        
        video_path = Path(video_path)
        
        if not video_path.exists():
            return VideoReviewResult(
                video_path=str(video_path),
                overall_score=0.0,
                passed=False,
                issues=[{"type": "file_not_found", "message": f"Video not found: {video_path}"}],
            )
        
        # Run quality checks
        dimension_scores = []
        all_issues = []
        
        # Visual fidelity check
        visual_score = await self._check_visual_fidelity(video_path)
        dimension_scores.append(visual_score)
        all_issues.extend([{"dimension": visual_score.dimension.value, "issue": i.value} for i in visual_score.issues])
        
        # Motion coherence check
        motion_score = await self._check_motion_coherence(video_path)
        dimension_scores.append(motion_score)
        all_issues.extend([{"dimension": motion_score.dimension.value, "issue": i.value} for i in motion_score.issues])
        
        # Character consistency check
        if character_references:
            char_score = await self._check_character_consistency(video_path, character_references)
        else:
            char_score = QualityScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=0.8,
                confidence=0.5,
                notes="No character references provided",
            )
        dimension_scores.append(char_score)
        all_issues.extend([{"dimension": char_score.dimension.value, "issue": i.value} for i in char_score.issues])
        
        # Prompt adherence check
        prompt_score = await self._check_prompt_adherence(video_path, prompt)
        dimension_scores.append(prompt_score)
        all_issues.extend([{"dimension": prompt_score.dimension.value, "issue": i.value} for i in prompt_score.issues])
        
        # Temporal stability check
        stability_score = await self._check_temporal_stability(video_path)
        dimension_scores.append(stability_score)
        all_issues.extend([{"dimension": stability_score.dimension.value, "issue": i.value} for i in stability_score.issues])
        
        # Physics check
        physics_score = await self._check_physics(video_path)
        dimension_scores.append(physics_score)
        all_issues.extend([{"dimension": physics_score.dimension.value, "issue": i.value} for i in physics_score.issues])
        
        # Audio sync check
        if audio_path:
            sync_score = await self._check_audio_sync(video_path, audio_path)
        else:
            sync_score = QualityScore(
                dimension=QualityDimension.AUDIO_SYNC,
                score=1.0,
                confidence=0.3,
                notes="No audio provided",
            )
        dimension_scores.append(sync_score)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # Determine pass/fail
        passed = overall_score >= self.pass_threshold
        
        # Check for escalation
        requires_escalation = False
        escalation_reason = None
        
        if overall_score < self.ESCALATION_THRESHOLD:
            requires_escalation = True
            escalation_reason = EscalationReason.QUALITY_BELOW_THRESHOLD
        elif regeneration_count >= self.max_regenerations:
            requires_escalation = True
            escalation_reason = EscalationReason.MULTIPLE_REGENERATIONS
        
        # Generate recommendations
        recommendations = self._generate_recommendations(dimension_scores, all_issues)
        
        processing_time = time.time() - start_time
        
        return VideoReviewResult(
            video_path=str(video_path),
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            passed=passed,
            requires_escalation=requires_escalation,
            escalation_reason=escalation_reason,
            recommendations=recommendations,
            processing_time_seconds=processing_time,
            metadata={
                "prompt": prompt[:200] if prompt else "",
                "regeneration_count": regeneration_count,
            },
        )
    
    # Laplacian-variance thresholds calibrated against the 2026-05-14 V0
    # corpus (94 Wan 2.2 T2V FP8 shots, n=10 sample): median 758, mean
    # 1015, min 265, max 2016, stdev 672. Wan 2.2 generates rich textures
    # (fireflies, leaves, fabric) which produce high edge content even
    # when the SCENE is incoherent — meaning sharpness ≠ "watchability."
    # Grant graded V0 a 1/5 ("slop") despite the corpus being sharp by
    # this metric. The slop-driver is temporal/coherence, not spatial
    # sharpness; that will be measured by _check_temporal_stability in
    # a follow-up. For now this dimension correctly distinguishes
    # genuinely BLURRY output (< 30 variance — flat regions or heavy
    # motion blur) from sharp output, regardless of semantic quality.
    #
    # Cap calibrated so V0 median (~758) maps to ~0.76, giving headroom
    # both up (V2_720p should push higher with more detail) and down
    # (a real blur regression should be obvious).
    SHARPNESS_SCORE_CAP: float = 1000.0
    BLURRY_LAPLACIAN_THRESHOLD: float = 30.0

    @staticmethod
    def _sample_frame_paths(video_path: Path, n: int = 5) -> List[Path]:
        """Extract ``n`` evenly-spaced frames from a video into /tmp and
        return their paths. Caller is responsible for unlinking.

        Uses ffmpeg ``-vf select`` (output seek) so it handles av1 GOP
        edge cases that pre-PR-47 broke. Frames are PNG so we don't
        introduce JPEG re-compression artifacts into the sharpness
        measurement (which is itself sensitive to compression).
        """
        import subprocess
        import tempfile

        # Probe duration once
        try:
            dur = float(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", str(video_path)],
                text=True,
            ).strip())
        except Exception as e:
            logger.warning("ffprobe failed for %s: %s", video_path, e)
            return []

        if dur <= 0.1:
            return []

        # Evenly-spaced timestamps; avoid the very first and last frames
        # because they often have decoder artifacts.
        timestamps = [dur * (i + 1) / (n + 1) for i in range(n)]
        tmpdir = Path(tempfile.mkdtemp(prefix="sharpness_"))
        out_paths: List[Path] = []
        for idx, ts in enumerate(timestamps):
            out = tmpdir / f"f{idx:02d}.png"
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error",
                     "-ss", f"{ts:.3f}", "-i", str(video_path),
                     "-update", "1", "-frames:v", "1", str(out)],
                    check=True, timeout=15,
                )
                if out.exists() and out.stat().st_size > 0:
                    out_paths.append(out)
            except Exception as e:
                logger.debug("frame extract @ %.3fs failed: %s", ts, e)
        return out_paths

    @staticmethod
    def _laplacian_variance(image_path: Path) -> float:
        """Compute the variance of a 4-neighbour discrete Laplacian on the
        grayscale image at ``image_path``. Higher = sharper. A flat image
        scores near 0; a sharp photo scores in the hundreds.

        Pure numpy + PIL — no opencv dependency.
        """
        import numpy as np
        from PIL import Image

        with Image.open(image_path) as img:
            arr = np.array(img.convert("L"), dtype=np.float64)

        if arr.shape[0] < 3 or arr.shape[1] < 3:
            return 0.0

        # 3x3 discrete Laplacian kernel [[0,1,0],[1,-4,1],[0,1,0]] applied
        # via slicing (vectorised, no scipy dependency).
        lap = (
            -4.0 * arr[1:-1, 1:-1]
            + arr[:-2, 1:-1] + arr[2:, 1:-1]
            + arr[1:-1, :-2] + arr[1:-1, 2:]
        )
        return float(lap.var())

    async def _check_visual_fidelity(self, video_path: Path) -> QualityScore:
        """Real sharpness measurement via Laplacian variance.

        Replaces the file-size heuristic that was returning made-up scores
        in the 0.6–0.9 band based on bytes-on-disk — caught by the
        2026-05-14 DNA-strand audit as exec-summary item #3.7 stub.

        Strategy: sample 5 evenly-spaced frames, compute the variance of
        a 4-neighbour discrete Laplacian on each (a standard sharpness
        metric — higher variance = more edge content = sharper), average,
        and linearly map to a 0..1 score capped at
        :attr:`SHARPNESS_SCORE_CAP`. Flags ``BLURRY_FRAMES`` when the
        averaged Laplacian variance falls below
        :attr:`BLURRY_LAPLACIAN_THRESHOLD`.

        Confidence reflects how many of the 5 sample frames decoded
        successfully — a video where only 1/5 frames decoded gets a
        low-confidence score the caller can choose to ignore.
        """
        import shutil

        try:
            frame_paths = await asyncio.get_event_loop().run_in_executor(
                None, self._sample_frame_paths, video_path, 5,
            )

            if not frame_paths:
                # Fall back to a low-confidence score so callers can
                # distinguish "no data" from "real low score" — per the
                # feedback_no_silent_fallbacks rule.
                return QualityScore(
                    dimension=QualityDimension.VISUAL_FIDELITY,
                    score=0.5,
                    confidence=0.1,
                    notes="Could not extract any sample frames",
                )

            variances = []
            for p in frame_paths:
                try:
                    variances.append(
                        await asyncio.get_event_loop().run_in_executor(
                            None, self._laplacian_variance, p,
                        )
                    )
                except Exception as e:
                    logger.debug("Laplacian failed for %s: %s", p, e)

            # Best-effort cleanup of /tmp frames
            try:
                shutil.rmtree(frame_paths[0].parent, ignore_errors=True)
            except Exception:
                pass

            if not variances:
                return QualityScore(
                    dimension=QualityDimension.VISUAL_FIDELITY,
                    score=0.5,
                    confidence=0.1,
                    notes="Frames decoded but Laplacian computation failed",
                )

            mean_var = sum(variances) / len(variances)
            score = max(0.0, min(1.0, mean_var / self.SHARPNESS_SCORE_CAP))
            confidence = min(1.0, 0.5 + 0.1 * len(variances))  # 0.6..1.0 by sample count

            issues: List[QualityIssue] = []
            if mean_var < self.BLURRY_LAPLACIAN_THRESHOLD:
                issues.append(QualityIssue.BLURRY_FRAMES)

            return QualityScore(
                dimension=QualityDimension.VISUAL_FIDELITY,
                score=score,
                confidence=confidence,
                issues=issues,
                notes=(
                    f"mean_laplacian_variance={mean_var:.1f} "
                    f"(threshold={self.BLURRY_LAPLACIAN_THRESHOLD}, "
                    f"cap={self.SHARPNESS_SCORE_CAP}, n_samples={len(variances)})"
                ),
            )
        except Exception as e:
            logger.warning("Visual fidelity check failed: %s", e)
            return QualityScore(
                dimension=QualityDimension.VISUAL_FIDELITY,
                score=0.5,
                confidence=0.3,
                notes=str(e),
            )
    
    async def _check_motion_coherence(self, video_path: Path) -> QualityScore:
        """Check motion naturalness."""
        # Would use optical flow analysis or motion prediction models
        return QualityScore(
            dimension=QualityDimension.MOTION_COHERENCE,
            score=0.8,
            confidence=0.5,
            notes="Motion analysis not implemented yet",
        )
    
    # Character consistency thresholds. Metric is the MEAN COSINE SIMILARITY
    # of largest face embeddings across consecutive sampled frames (within-
    # video drift) — high similarity = same person throughout the shot.
    #
    # Cosine sim is mapped to [0, 1] via (sim+1)/2 by face_embedding.py's
    # compute_similarity helper. InsightFace empirics in the mapped space:
    #
    # - Identical face / same person:   sim 0.85-1.00
    # - Same person, different angle:   sim 0.70-0.85
    # - Borderline same-person:         sim 0.60-0.70
    # - Uncorrelated / different person: sim 0.45-0.55  (raw cos sim ~0)
    # - Anti-correlated (true morph):    sim 0.00-0.40
    #
    # Threshold 0.55 sits just above the "uncorrelated different people"
    # band — catches clearly-drifted shots (a shot that lands a different
    # person each frame, or a morphing subject) while letting borderline
    # same-person variation through. Empirically the V0 smoke test showed
    # a same-person shot scoring 0.91 and a borderline shot scoring 0.66,
    # both well above 0.55.
    #
    # The V0 finding: 104/105 V0 shots PASS sharpness + temporal CoV, yet
    # Grant graded them 1/5. The slop driver is semantic identity drift
    # (subjects morphing smoothly between frames). This metric is the one
    # designed to catch exactly that.
    CHARACTER_DRIFT_THRESHOLD: float = 0.55   # below this → flag CHARACTER_DRIFT
    CHARACTER_FRAME_SAMPLES: int = 8           # frames to sample per video
    # Minimum frames-with-faces required to compute drift. With fewer than
    # this many face-bearing frames we report a low-confidence "insufficient
    # data" result rather than scoring noisy.
    MIN_FACE_FRAMES: int = 2

    async def _check_character_consistency(
        self,
        video_path: Path,
        reference_paths: Optional[List[str]] = None,
    ) -> QualityScore:
        """Real character-consistency check via InsightFace face embeddings.

        Replaces the hardcoded 0.75 stub flagged by the 2026-05-14 DNA-strand
        audit. The V0 corpus measurement (PR #58) showed that sharpness and
        temporal-delta CoV pass 104/105 V0 shots Grant graded as slop —
        identity drift is the actual slop driver and requires semantic
        tracking. This is that tracker.

        Strategy:
          1. Sample :attr:`CHARACTER_FRAME_SAMPLES` evenly-spaced frames.
          2. For each frame, run InsightFace `buffalo_l` detection +
             embedding extraction; keep the LARGEST face per frame.
          3. Compute mean cosine similarity across CONSECUTIVE face-
             bearing frames (within-video drift score). High mean
             similarity = consistent identity. Low = morphing.
          4. If ``reference_paths`` provided, also compute mean similarity
             of each frame face to its best-matching reference. Blend
             with drift score (50/50).
          5. Frames with NO detected face are skipped — non-character
             shots (landscapes, props) correctly score high-confidence
             "not applicable" rather than being penalized for legitimately
             having no face.

        Returns CHARACTER_DRIFT issue when mean within-video similarity
        falls below :attr:`CHARACTER_DRIFT_THRESHOLD`.

        Runs on CPU. The buffalo_l model is ~280MB on disk at
        ~/.insightface/models/buffalo_l/. First call performs lazy init
        (~3-5s). Per-frame extraction takes ~50-200ms on CPU.
        """
        import shutil

        try:
            from scenemachine.services.face_embedding import get_face_embedding_service
        except Exception as e:
            logger.warning("face_embedding service import failed: %s", e)
            return QualityScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=0.5,
                confidence=0.2,
                notes=f"face_embedding import failed: {e}",
            )

        try:
            frame_paths = await asyncio.get_event_loop().run_in_executor(
                None, self._sample_frame_paths, video_path, self.CHARACTER_FRAME_SAMPLES,
            )
            if not frame_paths:
                return QualityScore(
                    dimension=QualityDimension.CHARACTER_CONSISTENCY,
                    score=0.5,
                    confidence=0.1,
                    notes="Could not extract any sample frames",
                )

            # Force CPU — main GPU is typically occupied by the generation
            # pipeline; CPU is fast enough for the per-shot scoring (a few
            # frames * a few hundred ms each).
            svc = get_face_embedding_service()
            if svc.gpu_id != -1:
                # Re-instantiate the singleton on CPU. get_face_embedding_service
                # caches; for our purposes we want a CPU instance.
                from scenemachine.services.face_embedding import FaceEmbeddingService
                svc = FaceEmbeddingService(gpu_id=-1)

            def _extract_all() -> List[Any]:
                results = []
                for p in frame_paths:
                    try:
                        results.append(svc.extract_embedding(p, select_largest=True))
                    except Exception as e:
                        logger.debug("face extract failed for %s: %s", p, e)
                        results.append(None)
                return results

            extraction_results = await asyncio.get_event_loop().run_in_executor(
                None, _extract_all,
            )

            # Best-effort tmp cleanup
            try:
                shutil.rmtree(frame_paths[0].parent, ignore_errors=True)
            except Exception:
                pass

            face_embeddings = []
            for r in extraction_results:
                if r is None:
                    continue
                if r.success and r.primary_embedding is not None:
                    face_embeddings.append(r.primary_embedding)

            n_total = len(frame_paths)
            n_faces = len(face_embeddings)

            # Case 1: zero faces — legitimately no characters (landscape,
            # establishing shot, props). High score, low confidence.
            if n_faces == 0:
                return QualityScore(
                    dimension=QualityDimension.CHARACTER_CONSISTENCY,
                    score=0.95,
                    confidence=0.3,
                    notes=f"no faces detected in {n_total} sampled frames (non-character shot)",
                )

            # Case 2: too few face frames to compute drift, no refs
            if n_faces < self.MIN_FACE_FRAMES and not reference_paths:
                return QualityScore(
                    dimension=QualityDimension.CHARACTER_CONSISTENCY,
                    score=0.7,
                    confidence=0.3,
                    notes=f"only {n_faces}/{n_total} frames had faces and no refs given",
                )

            within_video_sim = None
            if n_faces >= 2:
                consecutive_sims = []
                for i in range(len(face_embeddings) - 1):
                    s = svc.compute_similarity(face_embeddings[i], face_embeddings[i + 1])
                    consecutive_sims.append(s)
                within_video_sim = sum(consecutive_sims) / len(consecutive_sims)

            # Reference comparison if provided
            reference_sim = None
            n_refs_used = 0
            if reference_paths:
                def _extract_refs() -> List[Any]:
                    refs = []
                    for r in reference_paths:
                        try:
                            res = svc.extract_embedding(r, select_largest=True)
                            if res.success and res.primary_embedding is not None:
                                refs.append(res.primary_embedding)
                        except Exception as e:
                            logger.debug("ref extract failed for %s: %s", r, e)
                    return refs

                ref_embeddings = await asyncio.get_event_loop().run_in_executor(
                    None, _extract_refs,
                )
                n_refs_used = len(ref_embeddings)
                if ref_embeddings:
                    per_frame_best = []
                    for fe in face_embeddings:
                        sims = [svc.compute_similarity(fe, r) for r in ref_embeddings]
                        if sims:
                            per_frame_best.append(max(sims))
                    if per_frame_best:
                        reference_sim = sum(per_frame_best) / len(per_frame_best)

            # Compose final score
            if within_video_sim is not None and reference_sim is not None:
                score = 0.5 * within_video_sim + 0.5 * reference_sim
                source = f"drift={within_video_sim:.3f} refmatch={reference_sim:.3f}"
            elif within_video_sim is not None:
                score = within_video_sim
                source = f"drift={within_video_sim:.3f}"
            elif reference_sim is not None:
                score = reference_sim
                source = f"refmatch={reference_sim:.3f}"
            else:
                return QualityScore(
                    dimension=QualityDimension.CHARACTER_CONSISTENCY,
                    score=0.5,
                    confidence=0.2,
                    notes=f"insufficient signal: n_faces={n_faces} n_refs={n_refs_used}",
                )

            score = max(0.0, min(1.0, score))
            # Confidence rises with frames-with-faces and reference count
            confidence = min(1.0, 0.4 + 0.08 * n_faces + 0.05 * n_refs_used)

            issues: List[QualityIssue] = []
            # Only flag drift when we actually measured drift (need ≥2 face frames)
            if within_video_sim is not None and within_video_sim < self.CHARACTER_DRIFT_THRESHOLD:
                issues.append(QualityIssue.CHARACTER_DRIFT)

            return QualityScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=score,
                confidence=confidence,
                issues=issues,
                notes=(
                    f"{source} (face_frames={n_faces}/{n_total} "
                    f"n_refs={n_refs_used} threshold={self.CHARACTER_DRIFT_THRESHOLD})"
                ),
            )
        except Exception as e:
            logger.warning(f"Character consistency check failed: {e}")
            return QualityScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=0.5,
                confidence=0.2,
                notes=str(e),
            )
    
    async def _check_prompt_adherence(
        self, 
        video_path: Path, 
        prompt: str,
    ) -> QualityScore:
        """Check if video matches the prompt description."""
        # Would use CLIP or similar vision-language model
        return QualityScore(
            dimension=QualityDimension.PROMPT_ADHERENCE,
            score=0.8 if prompt else 0.5,
            confidence=0.4,
            notes="CLIP analysis not implemented yet",
        )
    
    # Temporal stability thresholds. The metric is the COEFFICIENT OF
    # VARIATION (stdev/mean) of consecutive-frame mean-absolute-difference
    # measurements. A perfectly stable shot has consistent frame-to-frame
    # delta (locked camera + smooth motion); a hallucinatory shot has
    # huge swings in delta as the model invents and re-invents subjects.
    #
    # - Locked photo-real footage:    CoV  0.0–0.2  (very stable)
    # - Smooth narrative motion:      CoV  0.2–0.5
    # - Wan 2.2 reasonable shot:      CoV  0.5–1.0  (target band for v1)
    # - Hallucinatory / morphing:     CoV  1.0–2.0
    # - Catastrophic flicker:         CoV  > 2.0
    #
    # Score is 1 - (CoV / TEMPORAL_COV_CAP), clamped to [0, 1]. CoV=0 → 1.0,
    # CoV at cap → 0.0. Cap calibrated post-V0 measurement; tunable.
    TEMPORAL_COV_CAP: float = 2.0
    UNSTABLE_COV_THRESHOLD: float = 1.0

    @staticmethod
    def _temporal_frame_deltas(frame_paths: List[Path]) -> List[float]:
        """Compute mean absolute pixel difference between each consecutive
        pair of sampled frames (in grayscale). Returns one delta per
        consecutive pair (so N samples → N-1 deltas).

        Pure numpy + PIL. The metric is intentionally simple:
        ``mean(|frame_i - frame_{i+1}|)`` on grayscale arrays. Sudden
        morphs and identity drift produce large deltas; smooth motion
        produces small ones.
        """
        import numpy as np
        from PIL import Image

        deltas: List[float] = []
        prev_arr = None
        for p in frame_paths:
            try:
                with Image.open(p) as img:
                    arr = np.array(img.convert("L"), dtype=np.float32)
            except Exception as e:
                logger.debug("temporal: image read failed %s: %s", p, e)
                continue
            if prev_arr is not None and prev_arr.shape == arr.shape:
                deltas.append(float(np.mean(np.abs(arr - prev_arr))))
            prev_arr = arr
        return deltas

    async def _check_temporal_stability(self, video_path: Path) -> QualityScore:
        """Frame-delta-consistency check via coefficient of variation.

        Replaces the hardcoded 0.85 stub with an actual measurement, but
        with calibration honesty: the V0 baseline (8 random Wan 2.2 T2V
        FP8 shots, 2026-05-14) scores well on this metric — CoV median
        0.18, mean 0.23, max 0.60, all well below the 1.0 unstable
        threshold. Yet Grant graded V0 mp4s a 1/5 "slop."

        What this metric DOES catch:
          * Sudden cuts and flicker
          * Catastrophic frame-rate / temporal artifacts
          * Big bursty deltas (some small, some huge) indicating
            intermittent flash-of-hallucination

        What this metric does NOT catch (V0 evidence):
          * Subtle morphing where subject identity drifts smoothly
          * Subjects re-shaping smoothly between frames
          * Semantic incoherence (a "person" gradually becoming
            something not-a-person)

        Catching the not-caught failure modes requires semantic /
        identity tracking — face-embedding distance across frames
        (for character shots) and CLIP-embedding cosine distance for
        non-character shots. Those are RIB-3.7 follow-up codons.

        Why CoV and not raw mean delta: a shot with sustained smooth
        motion has high mean delta but consistent (low stdev) — that's
        fine. A shot with intermittent flash-of-morph has bursty
        deltas — that this catches.
        """
        import shutil
        try:
            frame_paths = await asyncio.get_event_loop().run_in_executor(
                None, self._sample_frame_paths, video_path, 10,
            )
            if len(frame_paths) < 3:
                return QualityScore(
                    dimension=QualityDimension.TEMPORAL_STABILITY,
                    score=0.5,
                    confidence=0.1,
                    notes=f"Could not extract enough frames (got {len(frame_paths)})",
                )

            deltas = await asyncio.get_event_loop().run_in_executor(
                None, self._temporal_frame_deltas, frame_paths,
            )

            # Best-effort tmp cleanup
            try:
                shutil.rmtree(frame_paths[0].parent, ignore_errors=True)
            except Exception:
                pass

            if len(deltas) < 2:
                return QualityScore(
                    dimension=QualityDimension.TEMPORAL_STABILITY,
                    score=0.5,
                    confidence=0.1,
                    notes="Not enough deltas to compute coefficient of variation",
                )

            mean_d = sum(deltas) / len(deltas)
            if mean_d < 1.0:
                # Essentially-static footage (locked camera, no motion).
                # That's actually GOOD for stability — give a high score.
                return QualityScore(
                    dimension=QualityDimension.TEMPORAL_STABILITY,
                    score=0.95,
                    confidence=0.8,
                    notes=f"mean_delta={mean_d:.3f} (essentially-static; trivially stable)",
                )

            # Sample stdev (Bessel correction)
            n = len(deltas)
            var = sum((x - mean_d) ** 2 for x in deltas) / (n - 1)
            stdev = var ** 0.5
            cov = stdev / mean_d

            score = max(0.0, min(1.0, 1.0 - cov / self.TEMPORAL_COV_CAP))
            confidence = min(1.0, 0.5 + 0.05 * n)

            issues: List[QualityIssue] = []
            if cov > self.UNSTABLE_COV_THRESHOLD:
                issues.append(QualityIssue.TEMPORAL_FLICKERING)

            return QualityScore(
                dimension=QualityDimension.TEMPORAL_STABILITY,
                score=score,
                confidence=confidence,
                issues=issues,
                notes=(
                    f"frame_delta_CoV={cov:.3f} mean={mean_d:.2f} stdev={stdev:.2f} "
                    f"(threshold={self.UNSTABLE_COV_THRESHOLD}, cap={self.TEMPORAL_COV_CAP}, "
                    f"n_deltas={n})"
                ),
            )
        except Exception as e:
            logger.warning("Temporal stability check failed: %s", e)
            return QualityScore(
                dimension=QualityDimension.TEMPORAL_STABILITY,
                score=0.5,
                confidence=0.3,
                notes=str(e),
            )
    
    async def _check_physics(self, video_path: Path) -> QualityScore:
        """Check for physics violations."""
        # Would use physics-aware vision models
        return QualityScore(
            dimension=QualityDimension.PHYSICS_PLAUSIBILITY,
            score=0.8,
            confidence=0.4,
            notes="Physics check not implemented yet",
        )
    
    async def _check_audio_sync(
        self, 
        video_path: Path, 
        audio_path: str,
    ) -> QualityScore:
        """Check audio/video synchronization."""
        # Would analyze lip movements vs audio
        return QualityScore(
            dimension=QualityDimension.AUDIO_SYNC,
            score=0.85,
            confidence=0.5,
            notes="Audio sync analysis not implemented yet",
        )
    
    def _calculate_overall_score(self, scores: List[QualityScore]) -> float:
        """Calculate weighted overall score."""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for score in scores:
            weight = self.DIMENSION_WEIGHTS.get(score.dimension, 0.1)
            # Weight by confidence
            effective_weight = weight * score.confidence
            weighted_sum += score.score * effective_weight
            total_weight += effective_weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _generate_recommendations(
        self, 
        scores: List[QualityScore], 
        issues: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations based on quality issues."""
        recommendations = []
        
        # Find lowest scoring dimensions
        sorted_scores = sorted(scores, key=lambda s: s.score)
        
        for score in sorted_scores[:3]:
            if score.score < self.pass_threshold:
                if score.dimension == QualityDimension.VISUAL_FIDELITY:
                    recommendations.append("Try regenerating with higher quality settings or more steps")
                elif score.dimension == QualityDimension.CHARACTER_CONSISTENCY:
                    recommendations.append("Use stronger character reference embedding (IP-Adapter) or LoRA")
                elif score.dimension == QualityDimension.MOTION_COHERENCE:
                    recommendations.append("Try adjusting motion parameters or using a different motion model")
                elif score.dimension == QualityDimension.TEMPORAL_STABILITY:
                    recommendations.append("Reduce CFG scale or use temporal smoothing LoRA")
        
        # Issue-specific recommendations
        issue_types = [i.get("issue") for i in issues]
        
        if QualityIssue.HAND_ARTIFACT.value in issue_types:
            recommendations.append("Use hand fix LoRA or inpaint hands post-generation")
        
        if QualityIssue.FACE_DISTORTION.value in issue_types:
            recommendations.append("Apply face restoration (GFPGAN/CodeFormer) post-generation")
        
        return recommendations[:5]  # Limit recommendations
    
    async def batch_review(
        self,
        video_paths: List[Union[str, Path]],
        prompts: Optional[List[str]] = None,
    ) -> List[VideoReviewResult]:
        """Review multiple videos in parallel.
        
        Args:
            video_paths: List of video file paths
            prompts: Optional list of prompts (parallel with video_paths)
            
        Returns:
            List of review results
        """
        prompts = prompts or [""] * len(video_paths)
        
        tasks = [
            self.review_video(path, prompt)
            for path, prompt in zip(video_paths, prompts)
        ]
        
        return await asyncio.gather(*tasks)


# Singleton instance
_reviewer: Optional[VideoQualityReviewer] = None


def get_video_quality_reviewer() -> VideoQualityReviewer:
    """Get or create the video quality reviewer singleton."""
    global _reviewer
    if _reviewer is None:
        _reviewer = VideoQualityReviewer()
    return _reviewer
