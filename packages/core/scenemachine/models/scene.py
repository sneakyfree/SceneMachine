"""
Scene Model

A scene from the screenplay with generation plan and status.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin, JSONType, ArrayType

if TYPE_CHECKING:
    from scenemachine.models.project import Project
    from scenemachine.models.shot import Shot


class SceneType(str, Enum):
    """Scene type classification based on location."""

    INTERIOR = "interior"  # INT.
    EXTERIOR = "exterior"  # EXT.
    INTERIOR_EXTERIOR = "interior_exterior"  # INT./EXT.


class TimeOfDay(str, Enum):
    """Time of day for scene lighting and mood."""

    DAY = "day"
    NIGHT = "night"
    DAWN = "dawn"
    DUSK = "dusk"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    CONTINUOUS = "continuous"  # Continues from previous scene
    LATER = "later"  # Later in the same day
    SAME = "same"  # Same time as previous scene
    MOMENTS_LATER = "moments_later"


class SceneState(str, Enum):
    """Scene workflow states."""

    PARSED = "parsed"  # Extracted from screenplay
    PLANNED = "planned"  # Shot breakdown generated
    PLAN_APPROVED = "plan_approved"  # User approved shot breakdown
    GENERATING = "generating"  # Generation in progress
    GENERATED = "generated"  # All shots generated
    REVIEW = "review"  # User reviewing generated content
    APPROVED = "approved"  # User approved final scene
    LOCKED = "locked"  # Scene locked for assembly


class Scene(Base, UUIDMixin, TimestampMixin):
    """
    A scene from the screenplay with generation plan and status.

    Scenes are extracted from the parsed screenplay and broken down
    into individual shots for generation.

    Attributes:
        project_id: Foreign key to the parent project
        scene_number: Scene number as it appears in screenplay
        sequence_number: Order in the movie (for sorting)
        scene_type: Interior, exterior, or both
        location: Scene location description
        time_of_day: Lighting/mood indicator
        raw_content: Original scene text from screenplay
        action_lines: Extracted action descriptions
        character_ids: UUIDs of characters in this scene
        analysis: AI-generated scene analysis (JSON)
        shot_breakdown: AI-generated shot breakdown (JSON)
        shot_breakdown_approved: Whether user approved the breakdown
        generation_settings: Scene-specific generation settings
        estimated_duration_seconds: Planned duration
        actual_duration_seconds: Final duration after generation
        state: Current workflow state
    """

    __tablename__ = "scenes"

    # Foreign key to project
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scene identification
    scene_number: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Scene header information
    scene_type: Mapped[SceneType] = mapped_column(
        SAEnum(SceneType, name="scene_type"),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    sub_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time_of_day: Mapped[TimeOfDay] = mapped_column(
        SAEnum(TimeOfDay, name="time_of_day"),
        nullable=False,
    )

    # Scene content (from screenplay)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    action_lines: Mapped[list[str]] = mapped_column(
        ArrayType(Text), default=list, nullable=False
    )
    dialogue_blocks: Mapped[Optional[list]] = mapped_column(JSONType, nullable=True)
    # Dialogue blocks structure:
    # [
    #     {
    #         "character": "SARAH",
    #         "parenthetical": "(nervously)",
    #         "text": "I don't think this is a good idea."
    #     }
    # ]

    # Characters in scene (UUIDs) - stored as JSON array for SQLite compatibility
    character_ids: Mapped[list[UUID]] = mapped_column(
        ArrayType(String), default=list, nullable=False
    )

    # Scene analysis (AI-generated)
    analysis: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "summary": "Sarah confronts her fears...",
    #     "mood": "tense",
    #     "emotional_arc": ["curiosity", "fear", "relief"],
    #     "emotional_beats": [
    #         {
    #             "moment": "Sarah enters",
    #             "emotion": "apprehension",
    #             "intensity": 6
    #         }
    #     ],
    #     "key_moments": [
    #         {
    #             "description": "The revelation",
    #             "importance": "high",
    #             "suggested_emphasis": "close-up on Sarah's reaction"
    #         }
    #     ],
    #     "visual_style_suggestions": {
    #         "lighting": "low-key, dramatic shadows",
    #         "color_palette": "cool blues and grays",
    #         "camera_style": "steady, deliberate movements"
    #     },
    #     "pacing": "slow build to climax",
    #     "importance": 8,
    #     "themes": ["confrontation", "truth"],
    #     "subtext": "Sarah's internal struggle with trust"
    # }

    # Shot breakdown (AI-generated, user-editable)
    shot_breakdown: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    shot_breakdown_approved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Shot breakdown structure:
    # {
    #     "version": 1,
    #     "total_shots": 5,
    #     "estimated_duration_seconds": 45,
    #     "shots": [
    #         {
    #             "shot_number": "1A",
    #             "shot_type": "establishing",
    #             "camera_movement": "static",
    #             "duration_seconds": 3,
    #             "description": "Wide shot of the coffee shop exterior",
    #             "characters_visible": [],
    #             "dialogue": null,
    #             "action": "Establish location and time of day",
    #             "notes": "Use warm morning light"
    #         },
    #         {
    #             "shot_number": "1B",
    #             "shot_type": "medium",
    #             "camera_movement": "tracking",
    #             "duration_seconds": 5,
    #             "description": "Follow Sarah as she enters",
    #             "characters_visible": ["SARAH"],
    #             "dialogue": null,
    #             "action": "Sarah enters looking around nervously",
    #             "notes": "Capture her apprehension"
    #         }
    #     ],
    #     "generation_metadata": {
    #         "model": "claude-3-opus",
    #         "generated_at": "2024-01-15T10:30:00Z"
    #     }
    # }

    # Generation settings (can override project defaults)
    generation_settings: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "quality_preset": "high",
    #     "style_override": null,
    #     "lighting_preset": "natural",
    #     "aspect_ratio": "16:9",
    #     "frame_rate": 24,
    #     "priority": "normal"
    # }

    # Timing
    estimated_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    actual_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # State
    state: Mapped[SceneState] = mapped_column(
        SAEnum(SceneState, name="scene_state"),
        default=SceneState.PARSED,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    shots: Mapped[list["Shot"]] = relationship(
        "Shot",
        back_populates="scene",
        cascade="all, delete-orphan",
        order_by="Shot.sequence_number",
    )

    @property
    def heading(self) -> str:
        """Generate standard scene heading."""
        type_str = {
            SceneType.INTERIOR: "INT.",
            SceneType.EXTERIOR: "EXT.",
            SceneType.INTERIOR_EXTERIOR: "INT./EXT.",
        }[self.scene_type]

        location_str = self.location.upper()
        if self.sub_location:
            location_str = f"{location_str} - {self.sub_location.upper()}"

        return f"{type_str} {location_str} - {self.time_of_day.value.upper()}"

    @property
    def shot_count(self) -> int:
        """Get number of shots in breakdown."""
        if self.shot_breakdown:
            return self.shot_breakdown.get("total_shots", len(self.shots))
        return len(self.shots)

    @property
    def is_ready_for_generation(self) -> bool:
        """Check if scene is ready for generation."""
        return (
            self.state == SceneState.PLAN_APPROVED
            and self.shot_breakdown is not None
            and self.shot_breakdown_approved
        )

    @property
    def generation_progress(self) -> float:
        """Calculate generation progress as percentage."""
        if not self.shots:
            return 0.0

        completed_states = {"generated", "approved", "locked"}
        completed = sum(1 for s in self.shots if s.state.value in completed_states)
        return (completed / len(self.shots)) * 100

    @property
    def all_shots_approved(self) -> bool:
        """Check if all shots are approved."""
        if not self.shots:
            return False
        return all(s.state.value in ("approved", "locked") for s in self.shots)

    def can_transition_to(self, new_state: SceneState) -> bool:
        """Check if transition to new state is valid."""
        valid_transitions: dict[SceneState, list[SceneState]] = {
            SceneState.PARSED: [SceneState.PLANNED],
            SceneState.PLANNED: [SceneState.PLAN_APPROVED, SceneState.PARSED],
            SceneState.PLAN_APPROVED: [SceneState.GENERATING, SceneState.PLANNED],
            SceneState.GENERATING: [SceneState.GENERATED, SceneState.PLAN_APPROVED],
            SceneState.GENERATED: [SceneState.REVIEW, SceneState.GENERATING],
            SceneState.REVIEW: [SceneState.APPROVED, SceneState.GENERATING],
            SceneState.APPROVED: [SceneState.LOCKED, SceneState.REVIEW],
            SceneState.LOCKED: [SceneState.APPROVED],  # Can unlock for changes
        }
        return new_state in valid_transitions.get(self.state, [])

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Scene(id={self.id}, "
            f"number='{self.scene_number}', "
            f"location='{self.location}', "
            f"state={self.state.value})>"
        )
