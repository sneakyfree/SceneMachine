"""Character model - represents characters with likeness definitions."""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .asset import Asset
    from .project import Project


class CharacterGender(str, Enum):
    """Character gender options."""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    UNSPECIFIED = "unspecified"


class CharacterLockState(str, Enum):
    """Character lock workflow states.

    Characters progress through these states as the user defines
    and refines their visual appearance.
    """

    UNDEFINED = "undefined"  # No information provided
    DRAFT = "draft"  # User has started defining
    REFERENCE_UPLOADED = "reference_uploaded"  # Reference images uploaded
    GENERATING = "generating"  # Generating likeness options
    REVIEW = "review"  # User reviewing generated options
    LOCKED = "locked"  # Likeness locked and approved


class Character(Base, UUIDMixin, TimestampMixin):
    """A character in the screenplay with associated likeness definition.

    Characters progress through a workflow from undefined to locked,
    with the user approving the final likeness before generation begins.

    The Character Laboratory is central to ensuring visual consistency
    across all generated scenes.
    """

    __tablename__ = "characters"

    # Foreign key to project
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Character identification (from screenplay)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    screenplay_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Character metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    age_range_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_range_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[CharacterGender] = mapped_column(
        SAEnum(CharacterGender, name="character_gender"),
        default=CharacterGender.UNSPECIFIED,
        nullable=False,
    )

    # Physical description (structured for AI prompting)
    physical_description: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "hair_color": "brown",
    #     "hair_style": "short, wavy",
    #     "eye_color": "blue",
    #     "skin_tone": "fair",
    #     "height": "tall",
    #     "build": "athletic",
    #     "distinguishing_features": ["scar on left cheek", "always wears glasses"],
    #     "clothing_style": "business casual",
    #     "additional_notes": "..."
    # }

    # Personality and voice (for AI understanding)
    personality_traits: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    voice_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # TTS Voice assignment
    voice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    voice_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    voice_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Lock state
    lock_state: Mapped[CharacterLockState] = mapped_column(
        SAEnum(CharacterLockState, name="character_lock_state"),
        default=CharacterLockState.UNDEFINED,
        nullable=False,
    )

    # Locked likeness definition (set when state becomes LOCKED)
    locked_likeness: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "primary_reference_asset_id": "uuid",
    #     "secondary_reference_asset_ids": ["uuid", "uuid"],
    #     "generation_prompt": "A tall man with brown wavy hair...",
    #     "negative_prompt": "cartoon, anime, deformed...",
    #     "lora_path": "path/to/character_lora.safetensors",
    #     "embedding_path": "path/to/character_embedding.pt",
    #     "locked_at": "2024-01-15T10:30:00Z",
    #     "locked_by_user": true
    # }

    # Importance metrics (for prioritization)
    scene_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dialogue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_protagonist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Ethics and consent
    consent_status: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "is_real_person": false,
    #     "consent_obtained": null,
    #     "consent_document_path": null,
    #     "likeness_rights_confirmed": false,
    #     "notes": "Original fictional character"
    # }

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    reference_assets: Mapped[List["Asset"]] = relationship(
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
    def age_range_display(self) -> Optional[str]:
        """Human-readable age range."""
        if self.age_range_min is not None and self.age_range_max is not None:
            if self.age_range_min == self.age_range_max:
                return str(self.age_range_min)
            return f"{self.age_range_min}-{self.age_range_max}"
        if self.age_range_min is not None:
            return f"{self.age_range_min}+"
        if self.age_range_max is not None:
            return f"up to {self.age_range_max}"
        return None

    @property
    def reference_asset_count(self) -> int:
        """Number of reference assets uploaded."""
        return len(self.reference_assets)

    def __repr__(self) -> str:
        """String representation."""
        return f"<Character(id={self.id}, name='{self.name}', state={self.lock_state.value})>"
