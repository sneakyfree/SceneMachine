"""User settings model for persistent configuration."""

import base64
import os
from enum import StrEnum
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from scenemachine.models.base import Base, TimestampMixin, UUIDMixin


class LLMProvider(StrEnum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class VideoProvider(StrEnum):
    """Supported video generation providers."""

    LOCAL = "local"
    REPLICATE = "replicate"
    FAL = "fal"
    RUNWAYML = "runwayml"


class ThemeMode(StrEnum):
    """UI theme modes."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


def _get_encryption_key() -> bytes:
    """Derive encryption key from secret key."""
    # Use environment secret key or generate a stable one
    secret = os.environ.get("SECRET_KEY", "scenemachine-default-key-change-me")
    salt = b"scenemachine-settings-salt"

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value."""
    if not value:
        return ""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt a sensitive value."""
    if not encrypted:
        return ""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return ""


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """User settings stored in the database.

    Stores user-configurable settings that override environment defaults.
    Sensitive values like API keys are encrypted at rest.
    """

    __tablename__ = "user_settings"

    # Settings are singleton - only one row expected
    # Using 'default' as a fixed key for the main settings
    settings_key: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        default="default",
        nullable=False,
    )

    # AI Provider Settings
    llm_provider: Mapped[str | None] = mapped_column(
        String(50),
        default=LLMProvider.ANTHROPIC.value,
        nullable=True,
    )
    video_provider: Mapped[str | None] = mapped_column(
        String(50),
        default=VideoProvider.LOCAL.value,
        nullable=True,
    )

    # Encrypted API Keys
    _anthropic_api_key: Mapped[str | None] = mapped_column(
        "anthropic_api_key",
        Text,
        nullable=True,
    )
    _openai_api_key: Mapped[str | None] = mapped_column(
        "openai_api_key",
        Text,
        nullable=True,
    )
    _replicate_api_key: Mapped[str | None] = mapped_column(
        "replicate_api_key",
        Text,
        nullable=True,
    )
    _fal_api_key: Mapped[str | None] = mapped_column(
        "fal_api_key",
        Text,
        nullable=True,
    )
    _runwayml_api_key: Mapped[str | None] = mapped_column(
        "runwayml_api_key",
        Text,
        nullable=True,
    )

    # Generation Settings
    max_concurrent_generations: Mapped[int] = mapped_column(
        default=2,
        nullable=False,
    )
    generation_timeout_seconds: Mapped[int] = mapped_column(
        default=600,
        nullable=False,
    )
    default_video_resolution: Mapped[str] = mapped_column(
        String(20),
        default="1920x1080",
        nullable=False,
    )
    default_video_fps: Mapped[int] = mapped_column(
        default=24,
        nullable=False,
    )

    # UI Preferences
    theme_mode: Mapped[str] = mapped_column(
        String(20),
        default=ThemeMode.DARK.value,
        nullable=False,
    )
    auto_save_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    show_advanced_options: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Storage Settings
    auto_cleanup_temp_files: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    max_cache_size_gb: Mapped[int] = mapped_column(
        default=10,
        nullable=False,
    )

    # Export Defaults
    default_export_format: Mapped[str] = mapped_column(
        String(20),
        default="mp4_h264",
        nullable=False,
    )
    default_export_quality: Mapped[str] = mapped_column(
        String(20),
        default="high",
        nullable=False,
    )

    # Accessibility Settings
    font_size_scale: Mapped[str] = mapped_column(
        String(20),
        default="medium",  # small | medium | large | extra-large
        nullable=False,
    )
    high_contrast_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    reduce_motion_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    large_click_targets_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Additional settings stored as JSON
    additional_settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )

    # Property accessors for encrypted API keys
    @property
    def anthropic_api_key(self) -> str:
        """Get decrypted Anthropic API key."""
        return decrypt_value(self._anthropic_api_key or "")

    @anthropic_api_key.setter
    def anthropic_api_key(self, value: str) -> None:
        """Set and encrypt Anthropic API key."""
        self._anthropic_api_key = encrypt_value(value) if value else None

    @property
    def openai_api_key(self) -> str:
        """Get decrypted OpenAI API key."""
        return decrypt_value(self._openai_api_key or "")

    @openai_api_key.setter
    def openai_api_key(self, value: str) -> None:
        """Set and encrypt OpenAI API key."""
        self._openai_api_key = encrypt_value(value) if value else None

    @property
    def replicate_api_key(self) -> str:
        """Get decrypted Replicate API key."""
        return decrypt_value(self._replicate_api_key or "")

    @replicate_api_key.setter
    def replicate_api_key(self, value: str) -> None:
        """Set and encrypt Replicate API key."""
        self._replicate_api_key = encrypt_value(value) if value else None

    @property
    def fal_api_key(self) -> str:
        """Get decrypted Fal API key."""
        return decrypt_value(self._fal_api_key or "")

    @fal_api_key.setter
    def fal_api_key(self, value: str) -> None:
        """Set and encrypt Fal API key."""
        self._fal_api_key = encrypt_value(value) if value else None

    @property
    def runwayml_api_key(self) -> str:
        """Get decrypted RunwayML API key."""
        return decrypt_value(self._runwayml_api_key or "")

    @runwayml_api_key.setter
    def runwayml_api_key(self, value: str) -> None:
        """Set and encrypt RunwayML API key."""
        self._runwayml_api_key = encrypt_value(value) if value else None

    def has_api_key(self, provider: str) -> bool:
        """Check if an API key is configured for a provider."""
        key_map = {
            "anthropic": self._anthropic_api_key,
            "openai": self._openai_api_key,
            "replicate": self._replicate_api_key,
            "fal": self._fal_api_key,
            "runwayml": self._runwayml_api_key,
        }
        encrypted = key_map.get(provider.lower())
        return bool(encrypted and decrypt_value(encrypted))

    def mask_api_key(self, key: str) -> str:
        """Return masked version of API key for display."""
        if not key or len(key) < 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    def to_dict(self, include_keys: bool = False) -> dict[str, Any]:
        """Convert settings to dictionary.

        Args:
            include_keys: If True, include masked API keys
        """
        result = {
            "id": str(self.id),
            "llmProvider": self.llm_provider,
            "videoProvider": self.video_provider,
            "maxConcurrentGenerations": self.max_concurrent_generations,
            "generationTimeoutSeconds": self.generation_timeout_seconds,
            "defaultVideoResolution": self.default_video_resolution,
            "defaultVideoFps": self.default_video_fps,
            "themeMode": self.theme_mode,
            "autoSaveEnabled": self.auto_save_enabled,
            "showAdvancedOptions": self.show_advanced_options,
            "autoCleanupTempFiles": self.auto_cleanup_temp_files,
            "maxCacheSizeGb": self.max_cache_size_gb,
            "defaultExportFormat": self.default_export_format,
            "defaultExportQuality": self.default_export_quality,
            # Accessibility settings
            "fontSizeScale": self.font_size_scale,
            "highContrastEnabled": self.high_contrast_enabled,
            "reduceMotionEnabled": self.reduce_motion_enabled,
            "largeClickTargetsEnabled": self.large_click_targets_enabled,
            "additionalSettings": self.additional_settings or {},
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_keys:
            result["apiKeys"] = {
                "anthropic": {
                    "configured": self.has_api_key("anthropic"),
                    "masked": self.mask_api_key(self.anthropic_api_key) if self.has_api_key("anthropic") else None,
                },
                "openai": {
                    "configured": self.has_api_key("openai"),
                    "masked": self.mask_api_key(self.openai_api_key) if self.has_api_key("openai") else None,
                },
                "replicate": {
                    "configured": self.has_api_key("replicate"),
                    "masked": self.mask_api_key(self.replicate_api_key) if self.has_api_key("replicate") else None,
                },
                "fal": {
                    "configured": self.has_api_key("fal"),
                    "masked": self.mask_api_key(self.fal_api_key) if self.has_api_key("fal") else None,
                },
                "runwayml": {
                    "configured": self.has_api_key("runwayml"),
                    "masked": self.mask_api_key(self.runwayml_api_key) if self.has_api_key("runwayml") else None,
                },
            }

        return result
