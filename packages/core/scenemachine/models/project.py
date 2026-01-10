"""
Project Model

A SceneMachine project representing a single movie production.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin, JSONType

if TYPE_CHECKING:
    from scenemachine.models.screenplay import Screenplay
    from scenemachine.models.character import Character
    from scenemachine.models.scene import Scene
    from scenemachine.models.share import ProjectShare
    from scenemachine.models.export_history import ExportHistory
    from scenemachine.models.user import User


class ProjectState(str, Enum):
    """
    Project workflow states.

    A project progresses through these states linearly, though users
    can always return to previous states to make changes.
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
    """
    A SceneMachine project representing a single movie production.

    A project progresses through defined states, each requiring user
    approval before advancing. Users can always return to previous states.

    Attributes:
        name: User-provided project name
        description: Optional project description
        state: Current workflow state
        settings: Project-specific settings (JSON)
        screenplay: Associated screenplay (one-to-one)
        characters: Characters in the project
        scenes: Scenes in the project
    """

    __tablename__ = "projects"

    # Owner (foreign key to User)
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Nullable for backward compatibility with existing projects
        index=True,
    )

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
    settings: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    # Settings structure:
    # {
    #     "visual_style": {
    #         "aspect_ratio": "16:9",
    #         "color_palette": "warm",
    #         "lighting_preference": "natural"
    #     },
    #     "generation": {
    #         "quality_preset": "high",
    #         "preferred_provider": "local",
    #         "max_concurrent_jobs": 2
    #     },
    #     "export": {
    #         "format": "mp4",
    #         "resolution": "1920x1080",
    #         "frame_rate": 24
    #     }
    # }

    # Relationships
    screenplay: Mapped[Optional["Screenplay"]] = relationship(
        "Screenplay",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    characters: Mapped[list["Character"]] = relationship(
        "Character",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    scenes: Mapped[list["Scene"]] = relationship(
        "Scene",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Scene.sequence_number",
    )
    shares: Mapped[list["ProjectShare"]] = relationship(
        "ProjectShare",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    export_history: Mapped[list["ExportHistory"]] = relationship(
        "ExportHistory",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="projects",
        foreign_keys=[owner_id],
    )

    @property
    def can_advance(self) -> bool:
        """
        Check if project can advance to the next state.

        Returns True if all requirements for the current state are met.
        """
        state_validators: dict[ProjectState, bool] = {
            ProjectState.EMPTY: self.screenplay is not None,
            ProjectState.SCREENPLAY_UPLOADED: (
                self.screenplay is not None and self.screenplay.is_parsed
            ),
            ProjectState.SCREENPLAY_PARSED: (
                self.screenplay is not None and self.screenplay.movie_plan is not None
            ),
            ProjectState.PLAN_GENERATED: (
                self.screenplay is not None and self.screenplay.movie_plan_approved
            ),
            ProjectState.PLAN_APPROVED: len(self.characters) > 0,
            ProjectState.CHARACTERS_IN_PROGRESS: all(c.is_locked for c in self.characters),
            ProjectState.CHARACTERS_LOCKED: len(self.scenes) > 0,
            ProjectState.SCENES_PLANNING: all(s.shot_breakdown_approved for s in self.scenes),
            ProjectState.SCENES_APPROVED: True,  # Can always start generating
            ProjectState.GENERATING: all(s.state.value == "approved" for s in self.scenes),
            ProjectState.GENERATION_COMPLETE: True,  # Can always start assembly
            ProjectState.ASSEMBLY_IN_PROGRESS: True,  # Completion is manual
            ProjectState.COMPLETE: True,  # Can always export
            ProjectState.EXPORTED: False,  # Final state
        }
        return state_validators.get(self.state, False)

    @property
    def next_state(self) -> Optional[ProjectState]:
        """Get the next logical state in the workflow."""
        state_order = list(ProjectState)
        try:
            current_index = state_order.index(self.state)
            if current_index < len(state_order) - 1:
                return state_order[current_index + 1]
        except ValueError:
            pass
        return None

    @property
    def progress_percentage(self) -> int:
        """Calculate overall project completion percentage."""
        state_progress: dict[ProjectState, int] = {
            ProjectState.EMPTY: 0,
            ProjectState.SCREENPLAY_UPLOADED: 5,
            ProjectState.SCREENPLAY_PARSED: 10,
            ProjectState.PLAN_GENERATED: 15,
            ProjectState.PLAN_APPROVED: 20,
            ProjectState.CHARACTERS_IN_PROGRESS: 30,
            ProjectState.CHARACTERS_LOCKED: 40,
            ProjectState.SCENES_PLANNING: 50,
            ProjectState.SCENES_APPROVED: 60,
            ProjectState.GENERATING: 75,
            ProjectState.GENERATION_COMPLETE: 85,
            ProjectState.ASSEMBLY_IN_PROGRESS: 95,
            ProjectState.COMPLETE: 100,
            ProjectState.EXPORTED: 100,
        }
        return state_progress.get(self.state, 0)

    def __repr__(self) -> str:
        """String representation."""
        return f"<Project(id={self.id}, name='{self.name}', state={self.state.value})>"
