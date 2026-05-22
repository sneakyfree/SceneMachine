"""
Assembler Agent - Video assembly and export.

Responsibilities:
- Concatenate clips into scenes
- Apply transitions between clips
- Mix audio tracks
- Export final movie
"""

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from scenemachine.agents.base import (
    ActionContext,
    ActionResult,
    ActionStatus,
    AgentType,
    BaseAgent,
)

logger = logging.getLogger(__name__)


class AssemblerAgent(BaseAgent):
    """
    Agent responsible for assembling clips and exporting movies.

    Autonomous actions:
    - assemble_scene: Combine shots into a scene
    - apply_transitions: Add transitions between clips
    - mix_audio: Mix dialogue, music, and SFX
    - normalize_audio: Level audio tracks

    Requires approval:
    - export_final: Approve final movie export
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.ASSEMBLER

    @property
    def capabilities(self) -> list[str]:
        return [
            "assemble_scene",
            "assemble_movie",
            "apply_transitions",
            "mix_audio",
            "normalize_audio",
            "export_final",
        ]

    @property
    def requires_approval(self) -> list[str]:
        return ["export_final"]

    async def _execute_action(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """Execute assembly actions."""
        if action_name == "assemble_scene":
            return await self._assemble_scene(context, **kwargs)
        elif action_name == "assemble_movie":
            return await self._assemble_movie(context, **kwargs)
        elif action_name == "apply_transitions":
            return await self._apply_transitions(context, **kwargs)
        elif action_name == "mix_audio":
            return await self._mix_audio(context, **kwargs)
        elif action_name == "export_final":
            return await self._export_final(context, **kwargs)
        else:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"Unknown action: {action_name}",
            )

    async def _assemble_scene(
        self,
        context: ActionContext,
        scene_id: UUID,
        shot_paths: list[str],
        output_path: str,
    ) -> ActionResult:
        """Assemble shots into a scene."""
        try:
            from scenemachine.utils.ffmpeg import FFmpeg

            ffmpeg = FFmpeg()
            await ffmpeg.ensure_available()

            # Convert to Path objects
            input_paths = [Path(p) for p in shot_paths]
            output = Path(output_path)

            # Concatenate videos
            await ffmpeg.concatenate_videos(input_paths, output)

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=output.exists(),
                output={
                    "scene_id": str(scene_id),
                    "output_path": str(output),
                    "shot_count": len(shot_paths),
                },
                confidence=0.9 if output.exists() else 0.0,
            )
        except Exception as e:
            logger.exception(f"Scene assembly failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    async def _assemble_movie(
        self,
        context: ActionContext,
        project_id: UUID,
        scene_paths: list[str],
        output_path: str,
    ) -> ActionResult:
        """Assemble scenes into a complete movie."""
        try:
            from scenemachine.utils.ffmpeg import FFmpeg

            ffmpeg = FFmpeg()
            await ffmpeg.ensure_available()

            input_paths = [Path(p) for p in scene_paths]
            output = Path(output_path)

            await ffmpeg.concatenate_videos(input_paths, output)

            # Get duration
            if output.exists():
                duration = await ffmpeg.get_duration(output)
            else:
                duration = 0

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=output.exists(),
                output={
                    "project_id": str(project_id),
                    "output_path": str(output),
                    "scene_count": len(scene_paths),
                    "duration_seconds": duration,
                },
                confidence=0.9 if output.exists() else 0.0,
            )
        except Exception as e:
            logger.exception(f"Movie assembly failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    async def _apply_transitions(
        self,
        context: ActionContext,
        video_path: str,
        transition_type: str = "dissolve",
        duration_seconds: float = 0.5,
    ) -> ActionResult:
        """Apply transitions between clips."""
        # This would use FFmpeg filter_complex in production
        # For now, return mock success

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "video_path": video_path,
                "transition_type": transition_type,
                "duration": duration_seconds,
            },
            confidence=0.8,
        )

    async def _mix_audio(
        self,
        context: ActionContext,
        video_path: str,
        audio_tracks: list[dict[str, Any]],
        output_path: str,
    ) -> ActionResult:
        """Mix multiple audio tracks with video."""
        # This would use FFmpeg audio mixing in production

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "output_path": output_path,
                "track_count": len(audio_tracks),
            },
            confidence=0.85,
        )

    async def _export_final(
        self,
        context: ActionContext,
        project_id: UUID,
        input_path: str,
        output_path: str,
        format: str = "mp4_h264",
        quality: str = "high",
    ) -> ActionResult:
        """Export final movie with specified settings."""
        try:
            from scenemachine.utils.ffmpeg import FFmpeg

            ffmpeg = FFmpeg()
            await ffmpeg.ensure_available()

            input_p = Path(input_path)
            output_p = Path(output_path)

            if not input_p.exists():
                return ActionResult(
                    action_id=context.session_id,
                    status=ActionStatus.FAILED,
                    success=False,
                    error_message=f"Input file not found: {input_path}",
                )

            # Copy for now (would transcode in production)
            import shutil
            shutil.copy(input_p, output_p)

            file_size = output_p.stat().st_size if output_p.exists() else 0

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=output_p.exists(),
                output={
                    "project_id": str(project_id),
                    "output_path": str(output_p),
                    "format": format,
                    "quality": quality,
                    "file_size_bytes": file_size,
                },
                confidence=0.95 if output_p.exists() else 0.0,
            )
        except Exception as e:
            logger.exception(f"Export failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    # ============================================================
    # S-P2-02: Assembler Agent Intelligence
    # ============================================================

    # Scene type to transition mapping for intelligent selection
    SCENE_TRANSITION_MAP: dict[str, list[str]] = {
        "dialogue": ["dissolve", "crossfade", "fade"],
        "action": ["wiperight", "wipeleft", "slideleft", "slideright"],
        "montage": ["circleopen", "circleclose", "fadeblack", "radial"],
        "flashback": ["fadewhite", "fadeblack", "pixelize"],
        "dream": ["zoomin", "radial", "fadewhite", "smoothdown"],
        "tension": ["wipeup", "wipedown", "slideleft", "slideright"],
        "reveal": ["circleopen", "zoomin", "radial"],
        "ending": ["fadeblack", "fadewhite", "dissolve"],
        "default": ["dissolve", "crossfade"],
    }

    # Mood-based audio mix presets
    AUDIO_MIX_PRESETS: dict[str, dict[str, float]] = {
        "dramatic": {"dialogue": 0.0, "music": -6.0, "sfx": -12.0},
        "action": {"dialogue": 0.0, "music": -3.0, "sfx": -6.0},
        "quiet": {"dialogue": 0.0, "music": -15.0, "sfx": -18.0},
        "musical": {"dialogue": -6.0, "music": 0.0, "sfx": -12.0},
        "ambient": {"dialogue": 0.0, "music": -12.0, "sfx": -3.0},
        "default": {"dialogue": 0.0, "music": -9.0, "sfx": -12.0},
    }

    async def analyze_assembly_plan(
        self,
        context: ActionContext,
        scenes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze scenes and create an intelligent assembly plan.

        S-P2-02: Provides smart recommendations for:
        - Optimal transition types between scenes
        - Audio mix balancing
        - Pacing adjustments

        Args:
            context: Action context
            scenes: List of scene dicts with metadata

        Returns:
            Assembly plan with recommendations
        """
        plan = {
            "scene_count": len(scenes),
            "transitions": [],
            "audio_mix": [],
            "pacing_notes": [],
            "estimated_duration": 0.0,
        }

        for i, scene in enumerate(scenes):
            scene_type = scene.get("type", "default")
            scene_duration = scene.get("duration", 3.0)
            mood = scene.get("mood", "default")

            plan["estimated_duration"] += scene_duration

            # Determine transition to next scene
            if i < len(scenes) - 1:
                next_scene = scenes[i + 1]
                transition = self._select_intelligent_transition(
                    scene, next_scene
                )
                plan["transitions"].append({
                    "from_scene": i,
                    "to_scene": i + 1,
                    "transition_type": transition["type"],
                    "duration": transition["duration"],
                    "reason": transition["reason"],
                })

            # Audio mix recommendation
            audio_preset = self.AUDIO_MIX_PRESETS.get(
                mood, self.AUDIO_MIX_PRESETS["default"]
            )
            plan["audio_mix"].append({
                "scene_index": i,
                "preset": mood if mood in self.AUDIO_MIX_PRESETS else "default",
                "levels": audio_preset,
            })

            # Pacing analysis
            if scene_duration < 2.0 and scene_type not in ["action", "montage"]:
                plan["pacing_notes"].append({
                    "scene_index": i,
                    "issue": "short_scene",
                    "recommendation": "Consider extending or combining with adjacent scene",
                })
            elif scene_duration > 30.0:
                plan["pacing_notes"].append({
                    "scene_index": i,
                    "issue": "long_scene",
                    "recommendation": "Consider adding b-roll or cutaways",
                })

        return plan

    def _select_intelligent_transition(
        self,
        current_scene: dict[str, Any],
        next_scene: dict[str, Any],
    ) -> dict[str, Any]:
        """Select the best transition between two scenes.

        Uses scene metadata to choose contextually appropriate transitions.
        """
        current_type = current_scene.get("type", "default")
        next_type = next_scene.get("type", "default")
        current_mood = current_scene.get("mood", "neutral")
        next_mood = next_scene.get("mood", "neutral")

        # Special case: ending scenes
        if next_type == "ending" or next_scene.get("is_final", False):
            return {
                "type": "fadeblack",
                "duration": 1.5,
                "reason": "Final scene, using fade to black for closure",
            }

        # Special case: flashback/dream transitions
        if next_type in ["flashback", "dream"]:
            return {
                "type": "fadewhite",
                "duration": 1.0,
                "reason": f"Transitioning to {next_type} sequence",
            }

        # Mood change detection
        mood_change = current_mood != next_mood

        # Select from appropriate transition pool
        if mood_change:
            # Stronger transition for mood changes
            if current_type in ["action", "tension"]:
                return {
                    "type": "wiperight",
                    "duration": 0.4,
                    "reason": "Quick transition for mood shift from intense scene",
                }
            else:
                return {
                    "type": "dissolve",
                    "duration": 0.8,
                    "reason": "Smooth dissolve for mood transition",
                }

        # Same mood - use scene-type appropriate transition
        transition_pool = self.SCENE_TRANSITION_MAP.get(
            current_type, self.SCENE_TRANSITION_MAP["default"]
        )

        import random
        selected = random.choice(transition_pool)

        # Adjust duration based on scene type
        if current_type in ["action", "montage"]:
            duration = 0.3
        elif current_type in ["dialogue", "quiet"]:
            duration = 0.7
        else:
            duration = 0.5

        return {
            "type": selected,
            "duration": duration,
            "reason": f"Standard {current_type} scene transition",
        }

    async def optimize_audio_levels(
        self,
        context: ActionContext,
        audio_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Optimize audio levels across the movie.

        Analyzes audio characteristics and recommends
        level adjustments for consistent output.

        Args:
            context: Action context
            audio_analysis: Dict with audio track analysis

        Returns:
            Optimization recommendations
        """
        tracks = audio_analysis.get("tracks", [])

        optimizations = {
            "adjustments": [],
            "normalization_target_lufs": -14.0,  # Standard streaming loudness
            "peak_limiter_ceiling": -1.0,  # dB
        }

        for track in tracks:
            track_id = track.get("id", "unknown")
            track_type = track.get("type", "unknown")
            current_lufs = track.get("lufs", -20.0)
            peak_db = track.get("peak_db", -3.0)

            # Calculate needed adjustment
            target_lufs = self.AUDIO_MIX_PRESETS["default"].get(
                track_type, 0.0
            )
            adjustment = target_lufs - current_lufs

            optimizations["adjustments"].append({
                "track_id": track_id,
                "track_type": track_type,
                "current_lufs": current_lufs,
                "target_lufs": target_lufs,
                "gain_adjustment_db": adjustment,
                "needs_limiting": peak_db > -3.0,
            })

        return optimizations

    async def suggest_cuts(
        self,
        context: ActionContext,
        scene_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Suggest edit points and cuts for a scene.

        Analyzes scene content to recommend optimal cut points
        for pacing and visual flow.

        Args:
            context: Action context
            scene_metadata: Scene information with shot details

        Returns:
            Cut suggestions with timestamps
        """
        shots = scene_metadata.get("shots", [])
        target_pace = scene_metadata.get("target_pace", "medium")

        # Pace-based shot duration targets
        pace_targets = {
            "fast": {"min": 1.0, "max": 3.0, "avg": 2.0},
            "medium": {"min": 2.0, "max": 6.0, "avg": 4.0},
            "slow": {"min": 4.0, "max": 12.0, "avg": 8.0},
        }

        target = pace_targets.get(target_pace, pace_targets["medium"])

        suggestions = {
            "target_pace": target_pace,
            "target_shot_duration": target,
            "shot_modifications": [],
        }

        for i, shot in enumerate(shots):
            duration = shot.get("duration", 3.0)
            shot_type = shot.get("type", "medium")

            modification = {"shot_index": i, "recommendations": []}

            # Too short
            if duration < target["min"]:
                modification["recommendations"].append({
                    "issue": "too_short",
                    "action": "extend",
                    "target_duration": target["avg"],
                    "reason": f"Shot is {duration:.1f}s, below {target['min']:.1f}s minimum for {target_pace} pace",
                })

            # Too long
            elif duration > target["max"]:
                modification["recommendations"].append({
                    "issue": "too_long",
                    "action": "split_or_trim",
                    "suggested_splits": int(duration / target["avg"]),
                    "reason": f"Shot is {duration:.1f}s, exceeds {target['max']:.1f}s maximum for {target_pace} pace",
                })

            # Wide shots can be longer
            if shot_type == "wide" and duration < 4.0:
                modification["recommendations"].append({
                    "issue": "establishing_shot_short",
                    "action": "consider_extending",
                    "reason": "Wide/establishing shots benefit from longer duration",
                })

            # Close-ups should be shorter
            if shot_type == "closeup" and duration > 5.0:
                modification["recommendations"].append({
                    "issue": "closeup_too_long",
                    "action": "consider_trimming",
                    "reason": "Close-up shots can feel awkward if held too long",
                })

            if modification["recommendations"]:
                suggestions["shot_modifications"].append(modification)

        suggestions["total_modifications_suggested"] = len(suggestions["shot_modifications"])

        return suggestions
