"""
Shot Model

An individual shot within a scene.
"""

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import ArrayType, Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from scenemachine.models.generation_job import GenerationJob
    from scenemachine.models.scene import Scene


class ShotType(StrEnum):
    """Standard cinematography shot types."""

    ESTABLISHING = "establishing"  # Wide shot to establish location
    WIDE = "wide"  # Full environment visible
    FULL = "full"  # Character from head to toe
    MEDIUM = "medium"  # Character from waist up
    MEDIUM_CLOSE_UP = "medium_close_up"  # Character from chest up
    CLOSE_UP = "close_up"  # Face fills frame
    EXTREME_CLOSE_UP = "extreme_close_up"  # Detail shot (eyes, hands)
    OVER_THE_SHOULDER = "over_the_shoulder"  # OTS dialogue shot
    POV = "pov"  # Point of view
    TWO_SHOT = "two_shot"  # Two characters in frame
    GROUP = "group"  # Multiple characters
    INSERT = "insert"  # Detail insert (object, text)
    CUTAWAY = "cutaway"  # Reaction or b-roll
    AERIAL = "aerial"  # Drone/helicopter view
    LOW_ANGLE = "low_angle"  # Looking up at subject
    HIGH_ANGLE = "high_angle"  # Looking down at subject
    DUTCH_ANGLE = "dutch_angle"  # Tilted frame


class CameraMovement(StrEnum):
    """Camera movement types."""

    STATIC = "static"  # No movement
    PAN = "pan"  # Horizontal rotation
    TILT = "tilt"  # Vertical rotation
    DOLLY = "dolly"  # Move toward/away from subject
    TRUCK = "truck"  # Move parallel to subject
    CRANE = "crane"  # Vertical movement
    HANDHELD = "handheld"  # Organic handheld movement
    STEADICAM = "steadicam"  # Smooth following movement
    ZOOM = "zoom"  # Optical zoom
    RACK_FOCUS = "rack_focus"  # Shift focus between subjects
    TRACKING = "tracking"  # Follow subject movement
    PUSH_IN = "push_in"  # Slow dolly toward subject
    PULL_OUT = "pull_out"  # Slow dolly away from subject
    WHIP_PAN = "whip_pan"  # Fast pan creating motion blur
    ORBIT = "orbit"  # Circle around subject


class ShotState(StrEnum):
    """Shot generation workflow states."""

    PLANNED = "planned"  # Shot defined but not generated
    QUEUED = "queued"  # In generation queue
    GENERATING = "generating"  # Currently being generated
    GENERATED = "generated"  # Generation complete
    FAILED = "failed"  # Generation failed
    REVIEW = "review"  # User reviewing output
    APPROVED = "approved"  # User approved
    REJECTED = "rejected"  # User rejected, needs regeneration
    REGENERATING = "regenerating"  # Being regenerated after rejection


class Shot(Base, UUIDMixin, TimestampMixin):
    """
    An individual shot within a scene.

    Shots are the atomic unit of generation. Each shot produces
    a video clip that will be assembled into the final scene.

    Attributes:
        scene_id: Foreign key to parent scene
        shot_number: Shot identifier (e.g., "1A", "1B")
        sequence_number: Order within scene
        shot_type: Type of shot (close-up, wide, etc.)
        camera_movement: Camera movement type
        description: Visual description for generation
        dialogue: Any dialogue in this shot
        action: Action description
        character_ids: Characters visible in shot
        composition_notes: Framing/composition guidance
        lighting_notes: Lighting guidance
        generation_prompt: Final prompt for generation
        negative_prompt: Negative prompt for generation
        duration_seconds: Target duration
        state: Current workflow state
        output_video_path: Path to generated video
        output_thumbnail_path: Path to thumbnail
        generation_metadata: Generation details (JSON)
        user_notes: User feedback/notes
        rating: User rating (1-5)
    """

    __tablename__ = "shots"

    # Foreign key to scene
    scene_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Shot identification
    shot_number: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Shot specification
    shot_type: Mapped[ShotType] = mapped_column(
        SAEnum(ShotType, name="shot_type"),
        nullable=False,
    )
    camera_movement: Mapped[CameraMovement] = mapped_column(
        SAEnum(CameraMovement, name="camera_movement"),
        default=CameraMovement.STATIC,
        nullable=False,
    )

    # Content description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    dialogue: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Characters in shot (UUIDs) - stored as JSON array for SQLite compatibility
    character_ids: Mapped[list[UUID]] = mapped_column(
        ArrayType(String), default=list, nullable=False
    )

    # Visual specification
    composition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lighting_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation prompts (computed/refined)
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional generation parameters
    generation_params: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "seed": 12345,
    #     "cfg_scale": 7.5,
    #     "steps": 50,
    #     "sampler": "euler_a",
    #     "style_preset": "cinematic",
    #     "motion_amount": 0.5,
    #     "character_embeddings": ["uuid1", "uuid2"],
    #     "reference_images": ["path1", "path2"]
    # }

    # Timing
    duration_seconds: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    actual_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timeline editing fields
    timeline_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeline_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timeline_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transition_type: Mapped[str | None] = mapped_column(String(50), default="cut", nullable=True)
    transition_duration: Mapped[float | None] = mapped_column(Float, default=0.5, nullable=True)

    # State
    state: Mapped[ShotState] = mapped_column(
        SAEnum(ShotState, name="shot_state"),
        default=ShotState.PLANNED,
        nullable=False,
    )

    # Generated output paths (relative to project directory)
    output_video_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_frames_dir: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Generation metadata
    generation_metadata: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "model_used": "wan2.1",
    #     "provider": "local",
    #     "seed": 12345,
    #     "steps": 50,
    #     "cfg_scale": 7.5,
    #     "generation_time_seconds": 120,
    #     "attempts": 1,
    #     "cost_estimate_usd": 0.05,
    #     "resolution": "1920x1080",
    #     "frame_rate": 24,
    #     "total_frames": 72,
    #     "started_at": "2024-01-15T10:30:00Z",
    #     "completed_at": "2024-01-15T10:32:00Z",
    #     "error_message": null
    # }

    # User feedback
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Version tracking (for regenerations)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="shots")
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        "GenerationJob",
        back_populates="shot",
        cascade="all, delete-orphan",
    )

    @property
    def is_generated(self) -> bool:
        """Check if shot has been generated."""
        return self.state in (
            ShotState.GENERATED,
            ShotState.REVIEW,
            ShotState.APPROVED,
        )

    @property
    def is_approved(self) -> bool:
        """Check if shot is approved."""
        return self.state == ShotState.APPROVED

    @property
    def needs_regeneration(self) -> bool:
        """Check if shot needs regeneration."""
        return self.state in (ShotState.REJECTED, ShotState.FAILED)

    @property
    def has_output(self) -> bool:
        """Check if shot has generated output."""
        return self.output_video_path is not None

    @property
    def display_label(self) -> str:
        """User-friendly label for the shot."""
        return f"Shot {self.shot_number} - {self.shot_type.value.replace('_', ' ').title()}"

    @property
    def generation_cost(self) -> float | None:
        """Get cost of generation if available."""
        if self.generation_metadata:
            return self.generation_metadata.get("cost_estimate_usd")
        return None

    def can_transition_to(self, new_state: ShotState) -> bool:
        """Check if transition to new state is valid."""
        valid_transitions: dict[ShotState, list[ShotState]] = {
            ShotState.PLANNED: [ShotState.QUEUED],
            ShotState.QUEUED: [ShotState.GENERATING, ShotState.PLANNED],
            ShotState.GENERATING: [ShotState.GENERATED, ShotState.FAILED],
            ShotState.GENERATED: [ShotState.REVIEW, ShotState.REGENERATING],
            ShotState.FAILED: [ShotState.QUEUED, ShotState.PLANNED],
            ShotState.REVIEW: [ShotState.APPROVED, ShotState.REJECTED],
            ShotState.APPROVED: [ShotState.REVIEW, ShotState.REGENERATING],
            ShotState.REJECTED: [ShotState.REGENERATING, ShotState.PLANNED],
            ShotState.REGENERATING: [ShotState.QUEUED],
        }
        return new_state in valid_transitions.get(self.state, [])

    def get_full_prompt(self) -> str:
        """
        Construct the full generation prompt.

        Combines description, action, dialogue context, and visual notes
        into a comprehensive prompt for the generation model.
        """
        parts = []

        # Shot type and movement
        parts.append(f"{self.shot_type.value.replace('_', ' ')} shot")
        if self.camera_movement != CameraMovement.STATIC:
            parts.append(f"with {self.camera_movement.value.replace('_', ' ')} movement")

        # Main description
        if self.description:
            parts.append(self.description)

        # Action
        if self.action:
            parts.append(f"Action: {self.action}")

        # Composition
        if self.composition_notes:
            parts.append(f"Composition: {self.composition_notes}")

        # Lighting
        if self.lighting_notes:
            parts.append(f"Lighting: {self.lighting_notes}")

        # Color
        if self.color_notes:
            parts.append(f"Color: {self.color_notes}")

        return ". ".join(parts)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Shot(id={self.id}, "
            f"number='{self.shot_number}', "
            f"type={self.shot_type.value}, "
            f"state={self.state.value})>"
        )
