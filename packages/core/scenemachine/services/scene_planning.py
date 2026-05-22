"""Scene planning service.

Handles scene analysis, shot breakdown generation, and the approval workflow.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.config import get_settings
from scenemachine.models import Project, Scene, Shot
from scenemachine.models.project import ProjectState
from scenemachine.models.scene import SceneState
from scenemachine.models.shot import CameraMovement, ShotState, ShotType

logger = logging.getLogger(__name__)


@dataclass
class ShotSpec:
    """Specification for a shot to be generated."""

    shot_number: str
    sequence_number: int
    shot_type: ShotType
    camera_movement: CameraMovement
    description: str
    dialogue: str | None = None
    action: str | None = None
    character_ids: list[UUID] = field(default_factory=list)
    duration_seconds: float = 3.0
    composition_notes: str | None = None
    lighting_notes: str | None = None


@dataclass
class SceneAnalysis:
    """Analysis of a scene for shot planning."""

    summary: str
    mood: str
    emotional_arc: list[str]
    key_moments: list[dict[str, Any]]
    visual_style_suggestions: list[str]
    pacing: str
    importance: int  # 1-10
    suggested_shot_count: int
    dialogue_heavy: bool
    action_heavy: bool


@dataclass
class ShotBreakdown:
    """Complete shot breakdown for a scene."""

    scene_id: str
    approach: str
    coverage_style: str
    notes: str
    shots: list[ShotSpec]
    estimated_duration: float


class ScenePlanningService:
    """Service for scene analysis and shot planning.

    Handles:
    - Scene analysis from screenplay content
    - Automatic shot breakdown generation
    - Shot type and camera movement suggestions
    - User editing and approval workflow
    """

    # Coverage styles for different scene types
    COVERAGE_STYLES = {
        "dialogue": "classical coverage with master and coverage shots",
        "action": "dynamic coverage with tracking and reaction shots",
        "emotional": "intimate coverage with close-ups and reaction shots",
        "establishing": "wide establishing shots with environmental details",
        "montage": "quick cuts with varied shot types",
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize scene planning service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()

    async def get_project_scenes(
        self,
        project_id: UUID,
        include_shots: bool = False,
    ) -> list[Scene]:
        """Get all scenes for a project.

        Args:
            project_id: Project UUID
            include_shots: Whether to load shots

        Returns:
            List of scenes ordered by sequence
        """
        # Always selectinload shots — the IPC handler accesses scene.shots
        # for the shotCount field even when include_shots=False, and
        # async lazy loads raise MissingGreenlet from an IPC session.
        # ``include_shots`` is kept as a parameter for callers that want
        # to skip the full shot serialization in the response.
        stmt = (
            select(Scene)
            .where(Scene.project_id == project_id)
            .order_by(Scene.sequence_number)
            .options(selectinload(Scene.shots))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_scene(
        self,
        scene_id: UUID,
        include_shots: bool = True,
    ) -> Scene | None:
        """Get a scene by ID.

        Args:
            scene_id: Scene UUID
            include_shots: Whether to load shots

        Returns:
            Scene or None
        """
        stmt = select(Scene).where(Scene.id == scene_id)

        if include_shots:
            stmt = stmt.options(selectinload(Scene.shots))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def analyze_scene(self, scene_id: UUID) -> SceneAnalysis:
        """Analyze a scene and generate planning insights.

        Args:
            scene_id: Scene UUID

        Returns:
            SceneAnalysis with insights

        Raises:
            ValueError: If scene not found
        """
        scene = await self.get_scene(scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        # Analyze scene content
        analysis = self._analyze_scene_content(scene)

        # Store analysis
        scene.analysis = {
            "summary": analysis.summary,
            "mood": analysis.mood,
            "emotional_arc": analysis.emotional_arc,
            "key_moments": analysis.key_moments,
            "visual_style_suggestions": analysis.visual_style_suggestions,
            "pacing": analysis.pacing,
            "importance": analysis.importance,
        }

        await self.session.commit()

        return analysis

    def _analyze_scene_content(self, scene: Scene) -> SceneAnalysis:
        """Analyze scene content to determine shot planning approach."""
        content = scene.raw_content.lower() if scene.raw_content else ""
        action_lines = scene.action_lines or []

        # Count dialogue vs action
        dialogue_count = content.count("\n") // 4  # Rough estimate
        action_count = len(action_lines)

        dialogue_heavy = dialogue_count > action_count
        action_heavy = action_count > dialogue_count * 2

        # Determine mood from keywords
        mood = self._determine_mood(content)

        # Determine pacing
        pacing = self._determine_pacing(content, action_heavy, dialogue_heavy)

        # Extract key moments from action lines
        key_moments = self._extract_key_moments(action_lines)

        # Generate emotional arc
        emotional_arc = self._generate_emotional_arc(content, key_moments)

        # Visual style suggestions based on scene type and time
        visual_suggestions = self._suggest_visual_style(scene, mood)

        # Estimate importance based on character count and dialogue
        importance = self._estimate_importance(scene, dialogue_count, action_count)

        # Suggest shot count based on content
        suggested_shots = self._suggest_shot_count(dialogue_count, action_count, importance)

        # Generate summary
        summary = self._generate_scene_summary(scene, key_moments)

        return SceneAnalysis(
            summary=summary,
            mood=mood,
            emotional_arc=emotional_arc,
            key_moments=key_moments,
            visual_style_suggestions=visual_suggestions,
            pacing=pacing,
            importance=importance,
            suggested_shot_count=suggested_shots,
            dialogue_heavy=dialogue_heavy,
            action_heavy=action_heavy,
        )

    def _determine_mood(self, content: str) -> str:
        """Determine scene mood from content."""
        mood_keywords = {
            "tense": ["gun", "threat", "danger", "fear", "nervous", "slowly"],
            "romantic": ["love", "kiss", "embrace", "tender", "heart"],
            "comedic": ["laugh", "funny", "joke", "smile", "grin"],
            "dramatic": ["cry", "tears", "shout", "argument", "angry"],
            "mysterious": ["shadow", "dark", "secret", "hidden", "whisper"],
            "action": ["run", "fight", "chase", "explosion", "crash"],
            "somber": ["funeral", "death", "grave", "sad", "mourn"],
            "joyful": ["celebrate", "happy", "excited", "cheer", "party"],
        }

        mood_scores: dict[str, int] = {}
        for mood, keywords in mood_keywords.items():
            score = sum(content.count(kw) for kw in keywords)
            if score > 0:
                mood_scores[mood] = score

        return max(mood_scores, key=mood_scores.get) if mood_scores else "neutral"

    def _determine_pacing(self, content: str, action_heavy: bool, dialogue_heavy: bool) -> str:
        """Determine scene pacing."""
        if action_heavy:
            return "fast-paced with quick cuts"
        elif dialogue_heavy:
            return "measured with deliberate pauses"
        elif "slowly" in content or "quiet" in content:
            return "slow and contemplative"
        else:
            return "moderate with natural rhythm"

    def _extract_key_moments(self, action_lines: list[str]) -> list[dict[str, Any]]:
        """Extract key moments from action lines."""
        key_moments = []

        high_importance_keywords = [
            "reveals",
            "discovers",
            "enters",
            "exits",
            "pulls",
            "grabs",
            "suddenly",
            "finally",
            "realizes",
            "screams",
            "kisses",
            "dies",
        ]

        medium_importance_keywords = [
            "looks",
            "turns",
            "walks",
            "sits",
            "stands",
            "opens",
            "closes",
        ]

        for i, line in enumerate(action_lines):
            line_lower = line.lower()

            importance = "low"
            if any(kw in line_lower for kw in high_importance_keywords):
                importance = "high"
            elif any(kw in line_lower for kw in medium_importance_keywords):
                importance = "medium"

            if importance != "low":
                key_moments.append(
                    {
                        "description": line[:100],
                        "importance": importance,
                        "line_index": i,
                    }
                )

        return key_moments[:10]  # Limit to 10 key moments

    def _generate_emotional_arc(self, content: str, key_moments: list[dict]) -> list[str]:
        """Generate emotional arc for the scene."""
        emotions = []

        # Start emotion based on opening
        if key_moments:
            first_moment = key_moments[0]["description"].lower()
            if "enter" in first_moment:
                emotions.append("anticipation")
            else:
                emotions.append("curiosity")
        else:
            emotions.append("neutral")

        # Middle emotions based on content
        if "conflict" in content or "argument" in content:
            emotions.append("tension")
        if "reveal" in content or "discover" in content:
            emotions.append("surprise")
        if "decision" in content or "choose" in content:
            emotions.append("conflict")

        # Ending emotion
        if "leave" in content or "exit" in content:
            emotions.append("resolution")
        elif "cliffhanger" in content or "suddenly" in content:
            emotions.append("suspense")
        else:
            emotions.append("conclusion")

        return emotions if len(emotions) > 1 else ["neutral", "neutral"]

    def _suggest_visual_style(self, scene: Scene, mood: str) -> list[str]:
        """Suggest visual style based on scene attributes."""
        suggestions = []

        # Time of day suggestions
        time_styles = {
            "night": "low-key lighting with practical sources",
            "dawn": "soft golden light with long shadows",
            "dusk": "warm orange tones with silhouettes",
            "day": "natural motivated lighting",
        }
        time_key = scene.time_of_day.value.lower()
        if time_key in time_styles:
            suggestions.append(time_styles[time_key])

        # Location type suggestions
        if scene.scene_type.value == "interior":
            suggestions.append("controlled interior lighting")
        else:
            suggestions.append("natural exterior lighting with fill")

        # Mood-based suggestions
        mood_styles = {
            "tense": "high contrast with deep shadows",
            "romantic": "soft diffused light with warm tones",
            "comedic": "bright even lighting",
            "dramatic": "chiaroscuro lighting",
            "mysterious": "pools of light in darkness",
            "action": "dynamic lighting with movement",
        }
        if mood in mood_styles:
            suggestions.append(mood_styles[mood])

        return suggestions

    def _estimate_importance(self, scene: Scene, dialogue_count: int, action_count: int) -> int:
        """Estimate scene importance on 1-10 scale."""
        # Base importance
        importance = 5

        # Adjust for character count
        char_count = len(scene.character_ids) if scene.character_ids else 0
        if char_count > 3:
            importance += 1
        elif char_count == 0:
            importance -= 1

        # Adjust for dialogue
        if dialogue_count > 10:
            importance += 2
        elif dialogue_count > 5:
            importance += 1

        # Adjust for action
        if action_count > 5:
            importance += 1

        return min(10, max(1, importance))

    def _suggest_shot_count(self, dialogue_count: int, action_count: int, importance: int) -> int:
        """Suggest number of shots for scene."""
        # Base shot count
        base_shots = 4

        # Add shots for dialogue (roughly 2 shots per dialogue exchange)
        dialogue_shots = dialogue_count // 2

        # Add shots for action
        action_shots = action_count

        # Adjust for importance
        importance_factor = importance / 5  # 1.0 for importance 5

        total = int((base_shots + dialogue_shots + action_shots) * importance_factor)

        return min(20, max(3, total))  # Clamp between 3 and 20

    def _generate_scene_summary(self, scene: Scene, key_moments: list[dict]) -> str:
        """Generate a summary of the scene."""
        moment_descs = [m["description"] for m in key_moments[:3]]

        if moment_descs:
            return f"Scene at {scene.location}: {'; '.join(moment_descs)}"
        else:
            return f"Scene at {scene.location} ({scene.time_of_day.value})"

    async def generate_shot_breakdown(
        self,
        scene_id: UUID,
        regenerate: bool = False,
    ) -> ShotBreakdown:
        """Generate a shot breakdown for a scene.

        Args:
            scene_id: Scene UUID
            regenerate: If True, regenerate even if breakdown exists

        Returns:
            ShotBreakdown with shot specifications

        Raises:
            ValueError: If scene not found
        """
        scene = await self.get_scene(scene_id, include_shots=True)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        # Check if breakdown already exists
        if scene.shots and not regenerate:
            return self._scene_to_breakdown(scene)

        # First analyze the scene if not done
        if not scene.analysis:
            await self.analyze_scene(scene_id)
            scene = await self.get_scene(scene_id)

        # Generate shot breakdown
        analysis = SceneAnalysis(
            summary=scene.analysis.get("summary", ""),
            mood=scene.analysis.get("mood", "neutral"),
            emotional_arc=scene.analysis.get("emotional_arc", []),
            key_moments=scene.analysis.get("key_moments", []),
            visual_style_suggestions=scene.analysis.get("visual_style_suggestions", []),
            pacing=scene.analysis.get("pacing", "moderate"),
            importance=scene.analysis.get("importance", 5),
            suggested_shot_count=len(scene.shots) if scene.shots else 6,
            dialogue_heavy=False,
            action_heavy=False,
        )

        # Generate shots
        shots = self._generate_shots(scene, analysis)

        # Determine coverage style
        coverage_style = self._determine_coverage_style(analysis)

        # Calculate estimated duration
        estimated_duration = sum(s.duration_seconds for s in shots)

        # Create breakdown
        breakdown = ShotBreakdown(
            scene_id=str(scene_id),
            approach=self._generate_approach_description(analysis),
            coverage_style=coverage_style,
            notes=f"Generated based on {analysis.mood} mood with {analysis.pacing}",
            shots=shots,
            estimated_duration=estimated_duration,
        )

        # Delete existing shots if regenerating
        if regenerate and scene.shots:
            for shot in scene.shots:
                await self.session.delete(shot)
            await self.session.flush()

        # Create shot records
        for shot_spec in shots:
            shot = Shot(
                scene_id=scene.id,
                shot_number=shot_spec.shot_number,
                sequence_number=shot_spec.sequence_number,
                shot_type=shot_spec.shot_type,
                camera_movement=shot_spec.camera_movement,
                description=shot_spec.description,
                dialogue=shot_spec.dialogue,
                action=shot_spec.action,
                character_ids=shot_spec.character_ids,
                duration_seconds=shot_spec.duration_seconds,
                composition_notes=shot_spec.composition_notes,
                lighting_notes=shot_spec.lighting_notes,
                state=ShotState.PLANNED,
            )
            self.session.add(shot)

        # Update scene
        scene.shot_breakdown = {
            "approach": breakdown.approach,
            "shot_count": len(shots),
            "coverage_style": coverage_style,
            "notes": breakdown.notes,
        }
        scene.state = SceneState.PLANNED
        scene.estimated_duration_seconds = estimated_duration

        await self.session.commit()

        logger.info(f"Generated shot breakdown for scene {scene_id}: {len(shots)} shots")

        return breakdown

    def _generate_shots(self, scene: Scene, analysis: SceneAnalysis) -> list[ShotSpec]:
        """Generate individual shots for a scene."""
        shots: list[ShotSpec] = []
        shot_num = 1

        character_ids = scene.character_ids or []

        # 1. Establishing shot (if exterior or new location)
        if scene.scene_type.value in ("exterior", "interior_exterior"):
            shots.append(
                ShotSpec(
                    shot_number=f"{scene.scene_number}-{shot_num}",
                    sequence_number=shot_num,
                    shot_type=ShotType.ESTABLISHING,
                    camera_movement=CameraMovement.STATIC,
                    description=f"Establishing shot of {scene.location}",
                    duration_seconds=4.0,
                    composition_notes="Wide angle, full environment visible",
                    lighting_notes=analysis.visual_style_suggestions[0]
                    if analysis.visual_style_suggestions
                    else None,
                )
            )
            shot_num += 1
        else:
            # Interior - start with wide shot
            shots.append(
                ShotSpec(
                    shot_number=f"{scene.scene_number}-{shot_num}",
                    sequence_number=shot_num,
                    shot_type=ShotType.WIDE,
                    camera_movement=CameraMovement.STATIC,
                    description=f"Wide shot of {scene.location} interior",
                    character_ids=character_ids[:3],
                    duration_seconds=3.0,
                )
            )
            shot_num += 1

        # 2. Character introduction shots
        for _i, char_id in enumerate(character_ids[:2]):  # Main characters
            shots.append(
                ShotSpec(
                    shot_number=f"{scene.scene_number}-{shot_num}",
                    sequence_number=shot_num,
                    shot_type=ShotType.MEDIUM,
                    camera_movement=CameraMovement.STATIC,
                    description="Character introduction",
                    character_ids=[char_id],
                    duration_seconds=2.5,
                )
            )
            shot_num += 1

        # 3. Coverage for key moments
        for moment in analysis.key_moments[:5]:
            shot_type, movement = self._suggest_shot_for_moment(moment)
            shots.append(
                ShotSpec(
                    shot_number=f"{scene.scene_number}-{shot_num}",
                    sequence_number=shot_num,
                    shot_type=shot_type,
                    camera_movement=movement,
                    description=moment["description"],
                    action=moment["description"],
                    character_ids=character_ids[:2] if character_ids else [],
                    duration_seconds=3.0 if moment["importance"] == "high" else 2.0,
                )
            )
            shot_num += 1

        # 4. Reaction shots (if dialogue heavy or emotional)
        if analysis.mood in ("tense", "dramatic", "emotional"):
            for char_id in character_ids[:2]:
                shots.append(
                    ShotSpec(
                        shot_number=f"{scene.scene_number}-{shot_num}",
                        sequence_number=shot_num,
                        shot_type=ShotType.CLOSE_UP,
                        camera_movement=CameraMovement.STATIC,
                        description="Reaction shot",
                        character_ids=[char_id],
                        duration_seconds=2.0,
                        composition_notes="Focus on facial expression",
                    )
                )
                shot_num += 1

        # 5. Two-shot for dialogue (if multiple characters)
        if len(character_ids) >= 2:
            shots.append(
                ShotSpec(
                    shot_number=f"{scene.scene_number}-{shot_num}",
                    sequence_number=shot_num,
                    shot_type=ShotType.TWO_SHOT,
                    camera_movement=CameraMovement.STATIC,
                    description="Two-shot for dialogue exchange",
                    character_ids=character_ids[:2],
                    duration_seconds=4.0,
                )
            )
            shot_num += 1

        # 6. Closing shot
        closing_type = (
            ShotType.WIDE if analysis.mood in ("somber", "mysterious") else ShotType.MEDIUM
        )
        shots.append(
            ShotSpec(
                shot_number=f"{scene.scene_number}-{shot_num}",
                sequence_number=shot_num,
                shot_type=closing_type,
                camera_movement=CameraMovement.DOLLY
                if analysis.pacing == "slow and contemplative"
                else CameraMovement.STATIC,
                description="Scene closing shot",
                character_ids=character_ids[:1] if character_ids else [],
                duration_seconds=3.0,
            )
        )

        return shots

    def _suggest_shot_for_moment(self, moment: dict[str, Any]) -> tuple[ShotType, CameraMovement]:
        """Suggest shot type and movement for a key moment."""
        desc = moment.get("description", "").lower()
        importance = moment.get("importance", "medium")

        # High importance moments get close-ups
        if importance == "high":
            if "reveal" in desc or "discover" in desc:
                return ShotType.CLOSE_UP, CameraMovement.DOLLY
            elif "enter" in desc or "exit" in desc:
                return ShotType.MEDIUM, CameraMovement.TRACKING
            else:
                return ShotType.CLOSE_UP, CameraMovement.STATIC

        # Medium importance
        if "look" in desc or "turn" in desc:
            return ShotType.MEDIUM_CLOSE_UP, CameraMovement.STATIC
        elif "walk" in desc or "move" in desc:
            return ShotType.MEDIUM, CameraMovement.TRACKING
        else:
            return ShotType.MEDIUM, CameraMovement.STATIC

    def _determine_coverage_style(self, analysis: SceneAnalysis) -> str:
        """Determine coverage style based on analysis."""
        if analysis.action_heavy:
            return self.COVERAGE_STYLES["action"]
        elif analysis.dialogue_heavy:
            return self.COVERAGE_STYLES["dialogue"]
        elif analysis.mood in ("romantic", "dramatic"):
            return self.COVERAGE_STYLES["emotional"]
        else:
            return self.COVERAGE_STYLES["dialogue"]

    def _generate_approach_description(self, analysis: SceneAnalysis) -> str:
        """Generate a description of the shooting approach."""
        return (
            f"Coverage approach for {analysis.mood} scene with {analysis.pacing}. "
            f"Emphasis on {', '.join(analysis.visual_style_suggestions[:2]) if analysis.visual_style_suggestions else 'standard coverage'}."
        )

    def _scene_to_breakdown(self, scene: Scene) -> ShotBreakdown:
        """Convert existing scene with shots to breakdown."""
        shots = [
            ShotSpec(
                shot_number=s.shot_number,
                sequence_number=s.sequence_number,
                shot_type=s.shot_type,
                camera_movement=s.camera_movement,
                description=s.description,
                dialogue=s.dialogue,
                action=s.action,
                character_ids=s.character_ids or [],
                duration_seconds=s.duration_seconds,
                composition_notes=s.composition_notes,
                lighting_notes=s.lighting_notes,
            )
            for s in scene.shots
        ]

        breakdown_data = scene.shot_breakdown or {}

        return ShotBreakdown(
            scene_id=str(scene.id),
            approach=breakdown_data.get("approach", ""),
            coverage_style=breakdown_data.get("coverage_style", ""),
            notes=breakdown_data.get("notes", ""),
            shots=shots,
            estimated_duration=scene.estimated_duration_seconds
            or sum(s.duration_seconds for s in shots),
        )

    async def update_shot(
        self,
        shot_id: UUID,
        shot_type: ShotType | None = None,
        camera_movement: CameraMovement | None = None,
        description: str | None = None,
        dialogue: str | None = None,
        action: str | None = None,
        duration_seconds: float | None = None,
        composition_notes: str | None = None,
        lighting_notes: str | None = None,
    ) -> Shot:
        """Update a shot's specification.

        Args:
            shot_id: Shot UUID
            shot_type: New shot type
            camera_movement: New camera movement
            description: New description
            dialogue: New dialogue
            action: New action
            duration_seconds: New duration
            composition_notes: New composition notes
            lighting_notes: New lighting notes

        Returns:
            Updated shot
        """
        stmt = select(Shot).where(Shot.id == shot_id)
        result = await self.session.execute(stmt)
        shot = result.scalar_one_or_none()

        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        if shot.state == ShotState.APPROVED:
            raise ValueError("Cannot modify an approved shot")

        if shot_type is not None:
            shot.shot_type = shot_type
        if camera_movement is not None:
            shot.camera_movement = camera_movement
        if description is not None:
            shot.description = description
        if dialogue is not None:
            shot.dialogue = dialogue
        if action is not None:
            shot.action = action
        if duration_seconds is not None:
            shot.duration_seconds = duration_seconds
        if composition_notes is not None:
            shot.composition_notes = composition_notes
        if lighting_notes is not None:
            shot.lighting_notes = lighting_notes

        await self.session.commit()
        await self.session.refresh(shot)

        return shot

    async def delete_shot(self, shot_id: UUID) -> bool:
        """Delete a shot.

        Args:
            shot_id: Shot UUID

        Returns:
            True if deleted
        """
        stmt = select(Shot).where(Shot.id == shot_id)
        result = await self.session.execute(stmt)
        shot = result.scalar_one_or_none()

        if not shot:
            return False

        if shot.state == ShotState.APPROVED:
            raise ValueError("Cannot delete an approved shot")

        await self.session.delete(shot)
        await self.session.commit()

        return True

    async def add_shot(
        self,
        scene_id: UUID,
        shot_type: ShotType,
        description: str,
        camera_movement: CameraMovement = CameraMovement.STATIC,
        duration_seconds: float = 3.0,
        after_shot_id: UUID | None = None,
    ) -> Shot:
        """Add a new shot to a scene.

        Args:
            scene_id: Scene UUID
            shot_type: Shot type
            description: Shot description
            camera_movement: Camera movement
            duration_seconds: Duration
            after_shot_id: Insert after this shot (None for end)

        Returns:
            Created shot
        """
        scene = await self.get_scene(scene_id, include_shots=True)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        # Determine sequence number
        if after_shot_id:
            after_shot = next((s for s in scene.shots if s.id == after_shot_id), None)
            if after_shot:
                sequence = after_shot.sequence_number + 1
                # Shift subsequent shots
                for shot in scene.shots:
                    if shot.sequence_number >= sequence:
                        shot.sequence_number += 1
            else:
                sequence = len(scene.shots) + 1
        else:
            sequence = len(scene.shots) + 1

        shot = Shot(
            scene_id=scene.id,
            shot_number=f"{scene.scene_number}-{sequence}",
            sequence_number=sequence,
            shot_type=shot_type,
            camera_movement=camera_movement,
            description=description,
            duration_seconds=duration_seconds,
            state=ShotState.PLANNED,
        )

        self.session.add(shot)
        await self.session.commit()
        await self.session.refresh(shot)

        return shot

    async def approve_shot_breakdown(self, scene_id: UUID) -> Scene:
        """Approve the shot breakdown for a scene.

        Args:
            scene_id: Scene UUID

        Returns:
            Updated scene
        """
        scene = await self.get_scene(scene_id, include_shots=True)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        if not scene.shots:
            raise ValueError("Scene has no shots to approve")

        scene.shot_breakdown_approved = True
        scene.state = SceneState.PLAN_APPROVED

        await self.session.commit()
        await self.session.refresh(scene)

        # Check if all scenes are approved
        await self._check_all_scenes_approved(scene.project_id)

        logger.info(f"Approved shot breakdown for scene {scene_id}")
        return scene

    async def _check_all_scenes_approved(self, project_id: UUID) -> None:
        """Check if all scenes have approved shot breakdowns."""
        scenes = await self.get_project_scenes(project_id)

        if not scenes:
            return

        all_approved = all(s.shot_breakdown_approved for s in scenes)

        if all_approved:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.session.execute(stmt)
            project = result.scalar_one_or_none()

            if project and project.state == ProjectState.SCENES_PLANNING:
                project.state = ProjectState.SCENES_APPROVED
                await self.session.commit()
                logger.info(f"All scenes approved for project {project_id}")

    async def get_shot(self, shot_id: UUID) -> Shot | None:
        """Get a shot by ID."""
        stmt = select(Shot).where(Shot.id == shot_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


async def get_scene_planning_service(session: AsyncSession) -> ScenePlanningService:
    """Factory function for ScenePlanningService."""
    return ScenePlanningService(session)
