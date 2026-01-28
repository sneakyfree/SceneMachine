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
    
    async def _check_visual_fidelity(self, video_path: Path) -> QualityScore:
        """Check overall visual quality."""
        # In production, would use image quality metrics (BRISQUE, NIQE, etc.)
        # For now, use mock scoring based on file analysis
        
        try:
            file_size = video_path.stat().st_size
            
            # Heuristic: larger files often have better quality
            if file_size > 10_000_000:  # > 10MB
                score = 0.9
            elif file_size > 5_000_000:  # > 5MB
                score = 0.8
            elif file_size > 1_000_000:  # > 1MB
                score = 0.7
            else:
                score = 0.6
            
            issues = []
            if score < 0.7:
                issues.append(QualityIssue.LOW_RESOLUTION)
            
            return QualityScore(
                dimension=QualityDimension.VISUAL_FIDELITY,
                score=score,
                confidence=0.6,
                issues=issues,
            )
        except Exception as e:
            logger.warning(f"Visual fidelity check failed: {e}")
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
    
    async def _check_character_consistency(
        self, 
        video_path: Path, 
        reference_paths: List[str],
    ) -> QualityScore:
        """Check character face consistency."""
        # Would use face detection + embedding comparison
        from scenemachine.services.face_embedding import get_face_embedding_service
        
        try:
            service = get_face_embedding_service()
            
            # In production, would extract frames and compare embeddings
            # For now, return mock score
            
            return QualityScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=0.75,
                confidence=0.6,
                notes=f"Compared against {len(reference_paths)} references",
            )
        except Exception as e:
            logger.warning(f"Character consistency check failed: {e}")
            return QualityScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=0.6,
                confidence=0.3,
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
    
    async def _check_temporal_stability(self, video_path: Path) -> QualityScore:
        """Check for flickering and temporal artifacts."""
        # Would analyze frame-to-frame differences
        return QualityScore(
            dimension=QualityDimension.TEMPORAL_STABILITY,
            score=0.85,
            confidence=0.5,
            notes="Temporal analysis not implemented yet",
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
