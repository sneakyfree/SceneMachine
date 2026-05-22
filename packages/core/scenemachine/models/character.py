"""
Character Model

A character in the screenplay with associated likeness definition.
This is a critical model for the Character Laboratory system.
"""

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scenemachine.models.base import ArrayType, Base, JSONType, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from scenemachine.models.asset import Asset
    from scenemachine.models.project import Project


class CharacterGender(StrEnum):
    """Character gender options."""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    UNSPECIFIED = "unspecified"


class CharacterLockState(StrEnum):
    """
    Character lock workflow states.

    Characters progress through these states as the user defines
    and refines their appearance in the Character Laboratory.
    """

    UNDEFINED = "undefined"  # No information provided
    DRAFT = "draft"  # User has started defining
    REFERENCE_UPLOADED = "reference_uploaded"  # Reference images uploaded
    GENERATING = "generating"  # Generating likeness options
    REVIEW = "review"  # User reviewing generated options
    LOCKED = "locked"  # Likeness locked, approved for generation


class Character(Base, UUIDMixin, TimestampMixin):
    """
    A character in the screenplay with associated likeness definition.

    Characters progress through a workflow from undefined to locked,
    with the user approving the final likeness before generation begins.
    This ensures visual consistency across all generated scenes.

    Attributes:
        project_id: Foreign key to the parent project
        name: User-editable display name
        screenplay_name: Original name as it appears in the screenplay
        description: User-provided character description
        age_range_min/max: Approximate age range
        gender: Character gender
        physical_description: Structured physical attributes (JSON)
        personality_traits: List of personality trait keywords
        voice_description: Description for future TTS integration
        lock_state: Current state in the lock workflow
        locked_likeness: Final approved likeness definition (JSON)
        scene_count: Number of scenes this character appears in
        dialogue_count: Number of dialogue lines
        is_protagonist: Whether this is a main character
        consent_status: Ethics and consent tracking (JSON)
    """

    __tablename__ = "characters"

    # Foreign key to project
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Character identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    screenplay_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Character metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_range_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_range_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[CharacterGender] = mapped_column(
        SAEnum(CharacterGender, name="character_gender"),
        default=CharacterGender.UNSPECIFIED,
        nullable=False,
    )

    # Physical description (structured for AI prompting)
    physical_description: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "hair_color": "brown",
    #     "hair_style": "short, wavy",
    #     "hair_length": "short",
    #     "eye_color": "blue",
    #     "skin_tone": "fair",
    #     "ethnicity": "Caucasian",
    #     "height": "tall",
    #     "build": "athletic",
    #     "facial_features": {
    #         "face_shape": "oval",
    #         "nose": "straight",
    #         "lips": "full",
    #         "jawline": "strong"
    #     },
    #     "distinguishing_features": ["scar on left cheek", "always wears glasses"],
    #     "clothing_style": "business casual",
    #     "signature_accessories": ["vintage watch", "leather bag"],
    #     "additional_notes": "Has a warm, approachable demeanor"
    # }

    # Personality and voice (for AI understanding)
    personality_traits: Mapped[list[str] | None] = mapped_column(ArrayType(String), nullable=True)
    voice_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lock state
    lock_state: Mapped[CharacterLockState] = mapped_column(
        SAEnum(CharacterLockState, name="character_lock_state"),
        default=CharacterLockState.UNDEFINED,
        nullable=False,
    )

    # Locked likeness definition (set when state becomes LOCKED)
    locked_likeness: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "primary_reference_asset_id": "uuid",
    #     "secondary_reference_asset_ids": ["uuid", "uuid"],
    #     "generation_prompt": "A 35-year-old woman with...",
    #     "negative_prompt": "cartoon, anime, deformed...",
    #     "face_embedding_path": "path/to/embedding.pt",
    #     "lora_path": "path/to/character_lora.safetensors",
    #     "consistency_settings": {
    #         "face_strength": 0.8,
    #         "style_strength": 0.6,
    #         "pose_flexibility": "medium"
    #     },
    #     "approved_variations": [
    #         {
    #             "expression": "neutral",
    #             "angle": "front",
    #             "asset_id": "uuid"
    #         },
    #         {
    #             "expression": "smiling",
    #             "angle": "three_quarter",
    #             "asset_id": "uuid"
    #         }
    #     ],
    #     "locked_at": "2024-01-15T10:30:00Z",
    #     "locked_by_user": true,
    #     "lock_version": 1
    # }

    # Importance metrics (for prioritization)
    scene_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dialogue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_protagonist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Ethics and consent
    consent_status: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Structure:
    # {
    #     "likeness_type": "original",  # "original", "self", "licensed", "public_figure"
    #     "is_real_person": false,
    #     "consent_obtained": null,
    #     "consent_document_path": null,
    #     "likeness_rights_confirmed": false,
    #     "age_verified": true,
    #     "content_restrictions": [],
    #     "notes": "Completely original character design"
    # }

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    reference_assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="character",
        cascade="all, delete-orphan",
        foreign_keys="Asset.character_id",
    )

    @property
    def is_locked(self) -> bool:
        """Check if character likeness is locked."""
        return self.lock_state == CharacterLockState.LOCKED

    @property
    def display_name(self) -> str:
        """User-friendly display name."""
        return self.name if self.name != self.screenplay_name else self.screenplay_name

    @property
    def age_display(self) -> str | None:
        """Format age range for display."""
        if self.age_range_min is not None and self.age_range_max is not None:
            if self.age_range_min == self.age_range_max:
                return str(self.age_range_min)
            return f"{self.age_range_min}-{self.age_range_max}"
        elif self.age_range_min is not None:
            return f"{self.age_range_min}+"
        elif self.age_range_max is not None:
            return f"Under {self.age_range_max}"
        return None

    @property
    def importance_score(self) -> float:
        """
        Calculate character importance score for prioritization.

        Higher scores indicate more important characters that should
        be prioritized in the Character Laboratory workflow.
        """
        score = 0.0

        # Protagonist bonus
        if self.is_protagonist:
            score += 50.0

        # Scene presence
        score += min(self.scene_count * 2, 30)  # Cap at 30 points

        # Dialogue importance
        score += min(self.dialogue_count * 0.5, 20)  # Cap at 20 points

        return score

    @property
    def lock_progress_percentage(self) -> int:
        """Calculate progress towards being locked."""
        progress_map: dict[CharacterLockState, int] = {
            CharacterLockState.UNDEFINED: 0,
            CharacterLockState.DRAFT: 20,
            CharacterLockState.REFERENCE_UPLOADED: 40,
            CharacterLockState.GENERATING: 60,
            CharacterLockState.REVIEW: 80,
            CharacterLockState.LOCKED: 100,
        }
        return progress_map.get(self.lock_state, 0)

    def can_transition_to(self, new_state: CharacterLockState) -> bool:
        """Check if transition to new state is valid."""
        valid_transitions: dict[CharacterLockState, list[CharacterLockState]] = {
            CharacterLockState.UNDEFINED: [CharacterLockState.DRAFT],
            CharacterLockState.DRAFT: [
                CharacterLockState.REFERENCE_UPLOADED,
                CharacterLockState.GENERATING,
            ],
            CharacterLockState.REFERENCE_UPLOADED: [
                CharacterLockState.GENERATING,
                CharacterLockState.DRAFT,
            ],
            CharacterLockState.GENERATING: [
                CharacterLockState.REVIEW,
                CharacterLockState.DRAFT,
            ],
            CharacterLockState.REVIEW: [
                CharacterLockState.LOCKED,
                CharacterLockState.GENERATING,
                CharacterLockState.DRAFT,
            ],
            CharacterLockState.LOCKED: [CharacterLockState.DRAFT],  # Can unlock to make changes
        }
        return new_state in valid_transitions.get(self.lock_state, [])

    def __repr__(self) -> str:
        """String representation."""
        return f"<Character(id={self.id}, name='{self.name}', lock_state={self.lock_state.value})>"
