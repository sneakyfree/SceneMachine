"""Asset model - represents files and media associated with projects."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .character import Character


class AssetType(str, Enum):
    """Types of assets stored in the system."""

    # Character-related
    CHARACTER_REFERENCE = "character_reference"  # User-uploaded reference image
    CHARACTER_GENERATED = "character_generated"  # AI-generated character image
    CHARACTER_LORA = "character_lora"  # Trained LoRA for character
    CHARACTER_EMBEDDING = "character_embedding"  # Trained embedding for character

    # Scene-related
    SCENE_REFERENCE = "scene_reference"  # Reference image for scene
    SCENE_STORYBOARD = "scene_storyboard"  # Storyboard frame

    # Generation outputs
    SHOT_VIDEO = "shot_video"  # Generated shot video
    SHOT_THUMBNAIL = "shot_thumbnail"  # Thumbnail for shot
    SHOT_PREVIEW = "shot_preview"  # Preview/draft generation

    # Export outputs
    SCENE_RENDER = "scene_render"  # Assembled scene video
    FINAL_MOVIE = "final_movie"  # Final exported movie

    # Miscellaneous
    AUDIO = "audio"  # Audio file
    OTHER = "other"  # Other asset type


class AssetStatus(str, Enum):
    """Asset processing status."""

    PENDING = "pending"  # Awaiting processing
    PROCESSING = "processing"  # Currently being processed
    READY = "ready"  # Ready for use
    FAILED = "failed"  # Processing failed
    ARCHIVED = "archived"  # No longer active


class Asset(Base, UUIDMixin, TimestampMixin):
    """A file or media asset associated with a project.

    Assets include reference images, generated content, trained models,
    and exported files.
    """

    __tablename__ = "assets"

    # Optional foreign key to character (for character-related assets)
    character_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Asset identification
    asset_type: Mapped[AssetType] = mapped_column(
        SAEnum(AssetType, name="asset_type"),
        nullable=False,
    )
    status: Mapped[AssetStatus] = mapped_column(
        SAEnum(AssetStatus, name="asset_status"),
        default=AssetStatus.PENDING,
        nullable=False,
    )

    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Media metadata (for images/video)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Description and notes
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Generation metadata (if asset was generated)
    generation_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure:
    # {
    #     "model": "model_id",
    #     "prompt": "...",
    #     "seed": 12345,
    #     "generation_time_seconds": 60,
    #     "source_asset_id": "uuid"  # If derived from another asset
    # }

    # Relationships
    character: Mapped[Optional["Character"]] = relationship(
        "Character",
        back_populates="reference_assets",
        foreign_keys=[character_id],
    )

    @property
    def is_image(self) -> bool:
        """Check if asset is an image."""
        if self.mime_type:
            return self.mime_type.startswith("image/")
        return self.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))

    @property
    def is_video(self) -> bool:
        """Check if asset is a video."""
        if self.mime_type:
            return self.mime_type.startswith("video/")
        return self.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm", ".mkv"))

    @property
    def is_ready(self) -> bool:
        """Check if asset is ready for use."""
        return self.status == AssetStatus.READY

    @property
    def dimensions(self) -> Optional[str]:
        """Get dimensions string (e.g., '1920x1080')."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None

    @property
    def file_size_display(self) -> Optional[str]:
        """Human-readable file size."""
        if self.file_size_bytes is None:
            return None
        size = self.file_size_bytes
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def __repr__(self) -> str:
        """String representation."""
        return f"<Asset(id={self.id}, type={self.asset_type.value}, filename='{self.filename}')>"
