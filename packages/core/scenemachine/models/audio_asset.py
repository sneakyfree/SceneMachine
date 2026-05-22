"""Audio asset model for sound effects and music tracks."""

from enum import StrEnum

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from .base import ArrayType, Base, JSONType, TimestampMixin, UUIDMixin


class AudioAssetType(StrEnum):
    """Types of audio assets."""

    SOUND_EFFECT = "sfx"
    MUSIC = "music"


class AudioAsset(Base, UUIDMixin, TimestampMixin):
    """An audio asset (sound effect or music track).

    Supports both system-provided and user-uploaded audio.
    """

    __tablename__ = "audio_assets"

    # Asset type and identification
    asset_type: Mapped[AudioAssetType] = mapped_column(
        SAEnum(AudioAssetType, name="audio_asset_type"),
        nullable=False,
    )

    # Basic metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # File information
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Waveform data for visualization (can be generated)
    waveform_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Categorization
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ArrayType(String), nullable=True)

    # Music-specific fields
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood: Mapped[list[str] | None] = mapped_column(ArrayType(String), nullable=True)
    key: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Musical key (C, Am, etc.)

    # User preferences
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Ownership
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # License info
    license_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_info: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    @property
    def is_sound_effect(self) -> bool:
        """Check if this is a sound effect."""
        return self.asset_type == AudioAssetType.SOUND_EFFECT

    @property
    def is_music(self) -> bool:
        """Check if this is a music track."""
        return self.asset_type == AudioAssetType.MUSIC

    @property
    def duration_display(self) -> str:
        """Human-readable duration."""
        if self.duration_seconds < 1:
            return f"{int(self.duration_seconds * 1000)}ms"
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        if minutes > 0:
            return f"{minutes}:{seconds:02d}"
        return f"{seconds}s"

    @property
    def file_size_display(self) -> str | None:
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
        return f"<AudioAsset(id={self.id}, type={self.asset_type.value}, name='{self.name}')>"


# Pre-defined categories for organization

SOUND_EFFECT_CATEGORIES = {
    "ambience": ["Nature", "Urban", "Indoor", "Weather"],
    "foley": ["Footsteps", "Clothing", "Doors", "Props"],
    "impacts": ["Hits", "Crashes", "Explosions", "Glass"],
    "whooshes": ["Swishes", "Swooshes", "Transitions"],
    "risers": ["Tension", "Horror", "Action"],
    "ui": ["Clicks", "Notifications", "Error"],
    "vehicles": ["Cars", "Motorcycles", "Aircraft"],
    "weapons": ["Guns", "Swords", "Punches"],
    "animals": ["Dogs", "Cats", "Birds", "Wildlife"],
    "voice": ["Crowds", "Reactions", "Vocalizations"],
}

MUSIC_GENRES = [
    "Cinematic",
    "Ambient",
    "Electronic",
    "Orchestral",
    "Acoustic",
    "Pop",
    "Rock",
    "Jazz",
    "Classical",
    "World",
]

MUSIC_MOODS = [
    "Epic",
    "Dramatic",
    "Tense",
    "Peaceful",
    "Romantic",
    "Mysterious",
    "Action",
    "Sad",
    "Happy",
    "Inspiring",
]
