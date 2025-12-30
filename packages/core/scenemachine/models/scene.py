"""Scene model - represents scenes from the screenplay with generation plans."""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .project import Project
    from .shot import Shot


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
    CONTINUOUS = "continuous"  # Same time as previous scene
    LATER = "later"  # Later in the same day
    SAME = "same"  # Same time as previous scene


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
    """A scene from the screenplay with generation plan and status.

    Scenes are the primary unit of generation, broken down into
    individual shots that are generated and assembled.
    """

    __tablename__ = "scenes"

    # Foreign key to project
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
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
    time_of_day: Mapped[TimeOfDay] = mapped_column(
        SAEnum(TimeOfDay, name="time_of_day"),
        nullable=False,
    )

    # Scene content (from screenplay)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    action_lines: Mapped[List[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )

    # Characters in scene (UUIDs of Character records)
    character_ids: Mapped[List[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), default=list, nullable=False
    )

    # Scene analysis (AI-generated)
    analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "summary": "John confronts his former partner about the missing money.",
    #     "mood": "tense",
    #     "emotional_arc": ["curiosity", "suspicion", "anger", "resignation"],
    #     "key_moments": [
    #         {"description": "John enters", "importance": "medium"},
    #         {"description": "The reveal", "importance": "high"}
    #     ],
    #     "visual_style_suggestions": ["low-key lighting", "tight framing"],
    #     "pacing": "slow build to climax",
    #     "importance": 8,  # 1-10 scale
    #     "connections": {
    #         "setup_for": ["scene_15"],
    #         "payoff_from": ["scene_3", "scene_7"]
    #     }
    # }

    # Shot breakdown (AI-generated, user-editable)
    shot_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure stored in separate Shot records, this is for the overall breakdown
    # {
    #     "approach": "dialogue-driven with reaction shots",
    #     "shot_count": 12,
    #     "coverage_style": "classical",
    #     "notes": "Focus on facial expressions during confrontation"
    # }

    shot_breakdown_approved: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Generation settings (can override project defaults)
    generation_settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "model": "specific_model_id",
    #     "quality_tier": "high",
    #     "style_preset": "noir",
    #     "lighting_override": "low-key",
    #     "color_grade": "desaturated"
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
    shots: Mapped[List["Shot"]] = relationship(
        "Shot",
        back_populates="scene",
        cascade="all, delete-orphan",
        order_by="Shot.sequence_number",
    )

    @property
    def heading(self) -> str:
        """Generate standard scene heading."""
        type_map = {
            SceneType.INTERIOR: "INT.",
            SceneType.EXTERIOR: "EXT.",
            SceneType.INTERIOR_EXTERIOR: "INT./EXT.",
        }
        type_str = type_map[self.scene_type]
        return f"{type_str} {self.location.upper()} - {self.time_of_day.value.upper()}"

    @property
    def shot_count(self) -> int:
        """Number of shots in scene."""
        return len(self.shots)

    @property
    def completed_shot_count(self) -> int:
        """Number of approved shots."""
        from .shot import ShotState

        return sum(1 for shot in self.shots if shot.state == ShotState.APPROVED)

    @property
    def generation_progress(self) -> float:
        """Generation progress as percentage (0-100)."""
        if not self.shots:
            return 0.0
        return (self.completed_shot_count / len(self.shots)) * 100

    def __repr__(self) -> str:
        """String representation."""
        return f"<Scene(id={self.id}, number='{self.scene_number}', heading='{self.heading}')>"
