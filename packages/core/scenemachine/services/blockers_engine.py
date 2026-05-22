"""Blockers and Unlockers Engine.

Implements the DNA strand master plan's Blockers/Unlockers system:
- Identifies issues that block or risk generation quality
- Provides prioritized fixes with effort/impact analysis
- Supports the "Why Not + What To Do Next" pattern
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class BlockerSeverity(StrEnum):
    """Severity levels for blockers."""

    CRITICAL = "critical"  # Blocks generation entirely
    HIGH = "high"  # Major quality risk
    MEDIUM = "medium"  # Notable issue
    LOW = "low"  # Minor polish item


class BlockerCategory(StrEnum):
    """Categories of blockers."""

    CHARACTER_MISSING = "character_missing"
    CHARACTER_INCOMPLETE = "character_incomplete"
    FORMAT_ERROR = "format_error"
    RESOURCE_INSUFFICIENT = "resource_insufficient"
    CONTENT_POLICY = "content_policy"
    QUALITY_RISK = "quality_risk"
    TECHNICAL = "technical"
    CONSISTENCY = "consistency"
    AUDIO = "audio"


class UnlockerPriority(StrEnum):
    """Priority levels for fixing blockers."""

    QUICK_WIN = "quick_win"  # < 5 minutes
    THIRTY_DAYS = "30_days"  # Moderate effort
    NINETY_DAYS = "90_days"  # Major effort


class UnlockerEffort(StrEnum):
    """Effort levels for fixes."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Unlocker:
    """A suggested fix for a blocker."""

    action: str
    priority: UnlockerPriority
    effort: UnlockerEffort
    impact_description: str
    auto_suggest: bool = False  # Can AI do this automatically?
    estimated_minutes: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "priority": self.priority.value,
            "effort": self.effort.value,
            "impact_description": self.impact_description,
            "auto_suggest": self.auto_suggest,
            "estimated_minutes": self.estimated_minutes,
        }


@dataclass
class Blocker:
    """A blocker that prevents or risks generation quality."""

    blocker_id: str
    severity: BlockerSeverity
    category: BlockerCategory
    description: str
    affected_shots: list[str] = field(default_factory=list)
    affected_characters: list[str] = field(default_factory=list)
    affected_scenes: list[str] = field(default_factory=list)
    unlocker: Unlocker | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocker_id": self.blocker_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "description": self.description,
            "affected_shots": self.affected_shots,
            "affected_characters": self.affected_characters,
            "affected_scenes": self.affected_scenes,
            "unlocker": self.unlocker.to_dict() if self.unlocker else None,
            "metadata": self.metadata,
        }


@dataclass
class BlockerAnalysis:
    """Complete blocker analysis for a project."""

    project_id: str | None
    blockers: list[Blocker] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    can_proceed: bool = True  # False if any critical blockers
    estimated_fix_time_minutes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "blockers": [b.to_dict() for b in self.blockers],
            "summary": {
                "critical_count": self.critical_count,
                "high_count": self.high_count,
                "medium_count": self.medium_count,
                "low_count": self.low_count,
                "total_count": len(self.blockers),
                "can_proceed": self.can_proceed,
                "estimated_fix_time_minutes": self.estimated_fix_time_minutes,
            },
            "blockers_by_severity": {
                "critical": [
                    b.to_dict() for b in self.blockers if b.severity == BlockerSeverity.CRITICAL
                ],
                "high": [b.to_dict() for b in self.blockers if b.severity == BlockerSeverity.HIGH],
                "medium": [
                    b.to_dict() for b in self.blockers if b.severity == BlockerSeverity.MEDIUM
                ],
                "low": [b.to_dict() for b in self.blockers if b.severity == BlockerSeverity.LOW],
            },
        }


class BlockersEngine:
    """Engine for detecting blockers and suggesting unlockers.

    This implements the DNA strand master plan's requirements:
    - Identify what's blocking generation
    - Explain "why not" clearly
    - Provide prioritized "what to do next" actions
    - Support bounded agentic fixes (auto_suggest)
    """

    def __init__(self) -> None:
        """Initialize the blockers engine."""
        pass

    def analyze_project(
        self,
        characters: list[dict[str, Any]],
        scenes: list[dict[str, Any]],
        shots: list[dict[str, Any]],
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a project for blockers.

        Args:
            characters: List of character definitions
            scenes: List of scene breakdowns
            shots: Combined list of shots (or extracted from scenes)
            settings: Project generation settings

        Returns:
            BlockerAnalysis as dictionary
        """
        analysis = BlockerAnalysis(project_id=None)

        # Check character blockers
        char_blockers = self._check_character_blockers(characters, shots)
        analysis.blockers.extend(char_blockers)

        # Check scene blockers
        scene_blockers = self._check_scene_blockers(scenes)
        analysis.blockers.extend(scene_blockers)

        # Check shot blockers
        shot_blockers = self._check_shot_blockers(shots)
        analysis.blockers.extend(shot_blockers)

        # Check audio/voice blockers
        audio_blockers = self._check_audio_blockers(characters, shots)
        analysis.blockers.extend(audio_blockers)

        # Check technical blockers
        if settings:
            tech_blockers = self._check_technical_blockers(settings)
            analysis.blockers.extend(tech_blockers)

        # Calculate counts
        analysis.critical_count = sum(
            1 for b in analysis.blockers if b.severity == BlockerSeverity.CRITICAL
        )
        analysis.high_count = sum(
            1 for b in analysis.blockers if b.severity == BlockerSeverity.HIGH
        )
        analysis.medium_count = sum(
            1 for b in analysis.blockers if b.severity == BlockerSeverity.MEDIUM
        )
        analysis.low_count = sum(1 for b in analysis.blockers if b.severity == BlockerSeverity.LOW)

        # Determine if can proceed
        analysis.can_proceed = analysis.critical_count == 0

        # Estimate fix time
        analysis.estimated_fix_time_minutes = sum(
            b.unlocker.estimated_minutes if b.unlocker else 10 for b in analysis.blockers
        )

        return analysis.to_dict()

    def _check_character_blockers(
        self, characters: list[dict[str, Any]], shots: list[dict[str, Any]]
    ) -> list[Blocker]:
        """Check for character-related blockers."""
        blockers = []

        # Get all characters referenced in shots
        shot_characters = set()
        for shot in shots:
            for char in shot.get("characters_in_frame", []):
                shot_characters.add(char.upper())
            if shot.get("dialogue"):
                shot_characters.add(shot["dialogue"].get("character", "").upper())

        # Build character lookup
        defined_characters = {c.get("name", "").upper(): c for c in characters}

        # Check for missing characters
        for char_name in shot_characters:
            if char_name and char_name not in defined_characters:
                affected_shots = [
                    shot.get("shot_id")
                    for shot in shots
                    if char_name in [c.upper() for c in shot.get("characters_in_frame", [])]
                    or (shot.get("dialogue", {}).get("character", "").upper() == char_name)
                ]

                blockers.append(
                    Blocker(
                        blocker_id=f"char_missing_{char_name.lower()}",
                        severity=BlockerSeverity.CRITICAL,
                        category=BlockerCategory.CHARACTER_MISSING,
                        description=f"Character '{char_name}' is referenced but not defined",
                        affected_shots=affected_shots,
                        affected_characters=[char_name],
                        unlocker=Unlocker(
                            action=f"Add character '{char_name}' in Character Laboratory",
                            priority=UnlockerPriority.QUICK_WIN,
                            effort=UnlockerEffort.LOW,
                            impact_description="Required for generation to proceed",
                            estimated_minutes=2,
                        ),
                    )
                )

        # Check for characters without reference images
        for char_name, char_data in defined_characters.items():
            if char_name in shot_characters:
                has_reference = (
                    char_data.get("reference_image_id")
                    or char_data.get("face_embedding_path")
                    or char_data.get("appearance_locked")
                )

                if not has_reference:
                    blockers.append(
                        Blocker(
                            blocker_id=f"char_no_ref_{char_name.lower()}",
                            severity=BlockerSeverity.HIGH,
                            category=BlockerCategory.CHARACTER_INCOMPLETE,
                            description=f"Character '{char_name}' has no reference image",
                            affected_characters=[char_name],
                            unlocker=Unlocker(
                                action=f"Upload reference image OR generate with AI for '{char_name}'",
                                priority=UnlockerPriority.QUICK_WIN,
                                effort=UnlockerEffort.LOW,
                                impact_description="Improves character consistency across shots",
                                auto_suggest=True,
                                estimated_minutes=2,
                            ),
                        )
                    )

        return blockers

    def _check_scene_blockers(self, scenes: list[dict[str, Any]]) -> list[Blocker]:
        """Check for scene-related blockers."""
        blockers = []

        for scene in scenes:
            scene_id = scene.get("scene_id", "unknown")

            # Check for missing location
            if not scene.get("location"):
                blockers.append(
                    Blocker(
                        blocker_id=f"scene_no_location_{scene_id}",
                        severity=BlockerSeverity.MEDIUM,
                        category=BlockerCategory.FORMAT_ERROR,
                        description=f"Scene {scene_id} has no location specified",
                        affected_scenes=[scene_id],
                        unlocker=Unlocker(
                            action="Specify location in scene heading",
                            priority=UnlockerPriority.QUICK_WIN,
                            effort=UnlockerEffort.LOW,
                            impact_description="Improves visual prompt generation",
                            estimated_minutes=1,
                        ),
                    )
                )

            # Check for empty scenes
            shots = scene.get("shots", [])
            if not shots:
                blockers.append(
                    Blocker(
                        blocker_id=f"scene_empty_{scene_id}",
                        severity=BlockerSeverity.HIGH,
                        category=BlockerCategory.FORMAT_ERROR,
                        description=f"Scene {scene_id} has no shots",
                        affected_scenes=[scene_id],
                        unlocker=Unlocker(
                            action="Add action or dialogue to scene",
                            priority=UnlockerPriority.QUICK_WIN,
                            effort=UnlockerEffort.MEDIUM,
                            impact_description="Required for scene to generate",
                            estimated_minutes=5,
                        ),
                    )
                )

        return blockers

    def _check_shot_blockers(self, shots: list[dict[str, Any]]) -> list[Blocker]:
        """Check for shot-related blockers."""
        blockers = []
        low_confidence_shots = []

        for shot in shots:
            shot_id = shot.get("shot_id", "unknown")
            confidence = shot.get("confidence", 1.0)

            # Check for low confidence
            if confidence < 0.6:
                low_confidence_shots.append(shot_id)

            # Check for missing visual prompt
            if not shot.get("visual_prompt"):
                blockers.append(
                    Blocker(
                        blocker_id=f"shot_no_prompt_{shot_id}",
                        severity=BlockerSeverity.CRITICAL,
                        category=BlockerCategory.FORMAT_ERROR,
                        description=f"Shot {shot_id} has no visual description",
                        affected_shots=[shot_id],
                        unlocker=Unlocker(
                            action="Add visual description for shot",
                            priority=UnlockerPriority.QUICK_WIN,
                            effort=UnlockerEffort.LOW,
                            impact_description="Required for video generation",
                            estimated_minutes=2,
                        ),
                    )
                )

            # Check for unknowns
            unknowns = shot.get("unknowns", [])
            if unknowns:
                blockers.append(
                    Blocker(
                        blocker_id=f"shot_unknowns_{shot_id}",
                        severity=BlockerSeverity.LOW,
                        category=BlockerCategory.QUALITY_RISK,
                        description=f"Shot {shot_id} has unresolved details: {', '.join(unknowns)}",
                        affected_shots=[shot_id],
                        metadata={"unknowns": unknowns},
                        unlocker=Unlocker(
                            action="Review and clarify shot details",
                            priority=UnlockerPriority.QUICK_WIN,
                            effort=UnlockerEffort.LOW,
                            impact_description="Improves generation quality",
                            estimated_minutes=2,
                        ),
                    )
                )

        # Aggregate low confidence shots
        if low_confidence_shots:
            blockers.append(
                Blocker(
                    blocker_id="shots_low_confidence",
                    severity=BlockerSeverity.MEDIUM,
                    category=BlockerCategory.QUALITY_RISK,
                    description=f"{len(low_confidence_shots)} shots have low confidence (<0.6) prompts",
                    affected_shots=low_confidence_shots,
                    unlocker=Unlocker(
                        action="Review and refine low-confidence shot prompts",
                        priority=UnlockerPriority.THIRTY_DAYS,
                        effort=UnlockerEffort.MEDIUM,
                        impact_description="Reduces generation failures",
                        estimated_minutes=30,
                    ),
                )
            )

        return blockers

    def _check_audio_blockers(
        self, characters: list[dict[str, Any]], shots: list[dict[str, Any]]
    ) -> list[Blocker]:
        """Check for audio/voice-related blockers."""
        blockers = []

        # Get characters with dialogue
        dialogue_characters = set()
        for shot in shots:
            if shot.get("dialogue"):
                dialogue_characters.add(shot["dialogue"].get("character", "").upper())

        # Check for missing voice profiles
        char_lookup = {c.get("name", "").upper(): c for c in characters}

        for char_name in dialogue_characters:
            if char_name in char_lookup:
                char = char_lookup[char_name]
                has_voice = char.get("voice_profile") or char.get("voice_clone_path")

                if not has_voice:
                    blockers.append(
                        Blocker(
                            blocker_id=f"char_no_voice_{char_name.lower()}",
                            severity=BlockerSeverity.HIGH,
                            category=BlockerCategory.AUDIO,
                            description=f"Character '{char_name}' has dialogue but no voice profile",
                            affected_characters=[char_name],
                            unlocker=Unlocker(
                                action=f"Select voice profile OR upload sample for '{char_name}'",
                                priority=UnlockerPriority.QUICK_WIN,
                                effort=UnlockerEffort.LOW,
                                impact_description="Required for dialogue generation",
                                estimated_minutes=5,
                            ),
                        )
                    )

        return blockers

    def _check_technical_blockers(self, settings: dict[str, Any]) -> list[Blocker]:
        """Check for technical blockers."""
        blockers = []

        # Check compute settings
        compute_mode = settings.get("compute_mode")
        if compute_mode == "local":
            gpu_vram = settings.get("gpu_vram_gb", 0)
            if gpu_vram < 8:
                blockers.append(
                    Blocker(
                        blocker_id="tech_low_vram",
                        severity=BlockerSeverity.HIGH,
                        category=BlockerCategory.RESOURCE_INSUFFICIENT,
                        description=f"Local GPU has {gpu_vram}GB VRAM, minimum 8GB required",
                        unlocker=Unlocker(
                            action="Switch to cloud compute or upgrade GPU",
                            priority=UnlockerPriority.NINETY_DAYS,
                            effort=UnlockerEffort.HIGH,
                            impact_description="Required for local video generation",
                            estimated_minutes=0,
                        ),
                    )
                )

        return blockers

    def get_prioritized_fixes(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Get prioritized list of fixes from analysis.

        Args:
            analysis: Output from analyze_project

        Returns:
            List of fixes ordered by priority
        """
        fixes = []

        for blocker in analysis.get("blockers", []):
            if blocker.get("unlocker"):
                fixes.append(
                    {
                        "blocker_id": blocker["blocker_id"],
                        "severity": blocker["severity"],
                        "category": blocker["category"],
                        "description": blocker["description"],
                        "fix": blocker["unlocker"],
                    }
                )

        # Sort by severity then by priority
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        priority_order = {"quick_win": 0, "30_days": 1, "90_days": 2}

        fixes.sort(
            key=lambda f: (
                severity_order.get(f["severity"], 99),
                priority_order.get(f["fix"]["priority"], 99),
            )
        )

        return fixes


def analyze_blockers(
    characters: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    shots: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function to analyze blockers.

    Args:
        characters: Character definitions
        scenes: Scene breakdowns
        shots: Shot list
        settings: Project settings

    Returns:
        Blocker analysis
    """
    engine = BlockersEngine()
    return engine.analyze_project(characters, scenes, shots, settings)
