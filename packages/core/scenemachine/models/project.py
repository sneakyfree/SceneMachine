"""Project model - the root entity for SceneMachine productions."""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .character import Character
    from .scene import Scene
    from .screenplay import Screenplay
    from .share import ProjectShare


class ProjectState(str, Enum):
    """Project workflow states.

    Projects progress through these states sequentially, with user approval
    required at key gates. Users can always return to previous states.
    """

    EMPTY = "empty"  # Just created, no screenplay
    SCREENPLAY_UPLOADED = "screenplay_uploaded"  # Screenplay uploaded, not parsed
    SCREENPLAY_PARSED = "screenplay_parsed"  # Screenplay parsed successfully
    PLAN_GENERATED = "plan_generated"  # Movie plan generated
    PLAN_APPROVED = "plan_approved"  # User approved the plan
    CHARACTERS_IN_PROGRESS = "characters_in_progress"  # Working on character lab
    CHARACTERS_LOCKED = "characters_locked"  # All characters locked
    SCENES_PLANNING = "scenes_planning"  # Planning individual scenes
    SCENES_APPROVED = "scenes_approved"  # All scene plans approved
    GENERATING = "generating"  # Generation in progress
    GENERATION_COMPLETE = "generation_complete"  # All scenes generated
    ASSEMBLY_IN_PROGRESS = "assembly_in_progress"  # Assembling final movie
    COMPLETE = "complete"  # Project complete
    EXPORTED = "exported"  # Final export created


class Project(Base, UUIDMixin, TimestampMixin):
    """A SceneMachine project representing a single movie production.

    A project progresses through defined states, each requiring user
    approval before advancing. Users can always return to previous states.
    """

    __tablename__ = "projects"

    # Basic metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # State management
    state: Mapped[ProjectState] = mapped_column(
        SAEnum(ProjectState, name="project_state"),
        default=ProjectState.EMPTY,
        nullable=False,
    )

    # Settings and preferences (JSON blob for flexibility)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Example settings structure:
    # {
    #     "visual_style": "cinematic",
    #     "aspect_ratio": "16:9",
    #     "frame_rate": 24,
    #     "resolution": "1920x1080",
    #     "color_palette": {...},
    #     "default_model": "local",
    #     "quality_tier": "high"
    # }

    # Relationships
    screenplay: Mapped[Optional["Screenplay"]] = relationship(
        "Screenplay",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    characters: Mapped[List["Character"]] = relationship(
        "Character",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    scenes: Mapped[List["Scene"]] = relationship(
        "Scene",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Scene.sequence_number",
    )
    shares: Mapped[List["ProjectShare"]] = relationship(
        "ProjectShare",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    @property
    def can_advance(self) -> bool:
        """Check if project can advance to next state."""
        if self.state == ProjectState.EMPTY:
            return self.screenplay is not None

        if self.state == ProjectState.SCREENPLAY_UPLOADED:
            return self.screenplay is not None and self.screenplay.is_parsed

        if self.state == ProjectState.SCREENPLAY_PARSED:
            return self.screenplay is not None and self.screenplay.movie_plan is not None

        if self.state == ProjectState.PLAN_GENERATED:
            return self.screenplay is not None and self.screenplay.movie_plan_approved

        if self.state == ProjectState.CHARACTERS_IN_PROGRESS:
            return len(self.characters) > 0 and all(c.is_locked for c in self.characters)

        if self.state == ProjectState.SCENES_PLANNING:
            return len(self.scenes) > 0 and all(s.shot_breakdown_approved for s in self.scenes)

        return False

    @property
    def character_count(self) -> int:
        """Number of characters in project."""
        return len(self.characters)

    @property
    def scene_count(self) -> int:
        """Number of scenes in project."""
        return len(self.scenes)

    @property
    def locked_character_count(self) -> int:
        """Number of locked characters."""
        return sum(1 for c in self.characters if c.is_locked)

    @property
    def approved_scene_count(self) -> int:
        """Number of approved scenes."""
        return sum(1 for s in self.scenes if s.shot_breakdown_approved)

    def __repr__(self) -> str:
        """String representation."""
        return f"<Project(id={self.id}, name='{self.name}', state={self.state.value})>"
