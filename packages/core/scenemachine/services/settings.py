"""Settings service for managing user configuration."""

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.settings import (
    LLMProvider,
    ThemeMode,
    UserSettings,
    VideoProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderStatus:
    """Status of a provider."""

    provider: str
    name: str
    available: bool
    configured: bool
    message: str
    latency_ms: Optional[float] = None


@dataclass
class StorageStats:
    """Storage statistics."""

    data_dir: str
    upload_dir: str
    output_dir: str
    cache_dir: str
    total_size_bytes: int
    upload_size_bytes: int
    output_size_bytes: int
    cache_size_bytes: int
    temp_files_count: int


class SettingsService:
    """Service for managing user settings and configuration."""

    def __init__(self, session: AsyncSession):
        """Initialize settings service.

        Args:
            session: Database session
        """
        self._session = session
        self._app_settings = get_settings()

    async def get_settings(self) -> UserSettings:
        """Get current user settings, creating defaults if not exist.

        Returns:
            UserSettings instance
        """
        stmt = select(UserSettings).where(UserSettings.settings_key == "default")
        result = await self._session.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            # Create default settings
            settings = UserSettings(settings_key="default")
            self._session.add(settings)
            await self._session.commit()
            await self._session.refresh(settings)

        return settings

    async def update_settings(
        self,
        llm_provider: Optional[str] = None,
        video_provider: Optional[str] = None,
        max_concurrent_generations: Optional[int] = None,
        generation_timeout_seconds: Optional[int] = None,
        default_video_resolution: Optional[str] = None,
        default_video_fps: Optional[int] = None,
        theme_mode: Optional[str] = None,
        auto_save_enabled: Optional[bool] = None,
        show_advanced_options: Optional[bool] = None,
        auto_cleanup_temp_files: Optional[bool] = None,
        max_cache_size_gb: Optional[int] = None,
        default_export_format: Optional[str] = None,
        default_export_quality: Optional[str] = None,
        additional_settings: Optional[Dict[str, Any]] = None,
    ) -> UserSettings:
        """Update user settings.

        Args:
            Various settings fields to update

        Returns:
            Updated UserSettings instance
        """
        settings = await self.get_settings()

        if llm_provider is not None:
            # Validate provider
            if llm_provider not in [p.value for p in LLMProvider]:
                raise ValueError(f"Invalid LLM provider: {llm_provider}")
            settings.llm_provider = llm_provider

        if video_provider is not None:
            if video_provider not in [p.value for p in VideoProvider]:
                raise ValueError(f"Invalid video provider: {video_provider}")
            settings.video_provider = video_provider

        if max_concurrent_generations is not None:
            if max_concurrent_generations < 1 or max_concurrent_generations > 10:
                raise ValueError("Max concurrent generations must be between 1 and 10")
            settings.max_concurrent_generations = max_concurrent_generations

        if generation_timeout_seconds is not None:
            if generation_timeout_seconds < 60 or generation_timeout_seconds > 3600:
                raise ValueError("Generation timeout must be between 60 and 3600 seconds")
            settings.generation_timeout_seconds = generation_timeout_seconds

        if default_video_resolution is not None:
            valid_resolutions = ["1280x720", "1920x1080", "2560x1440", "3840x2160"]
            if default_video_resolution not in valid_resolutions:
                raise ValueError(f"Invalid resolution. Must be one of: {valid_resolutions}")
            settings.default_video_resolution = default_video_resolution

        if default_video_fps is not None:
            if default_video_fps not in [24, 25, 30, 60]:
                raise ValueError("FPS must be 24, 25, 30, or 60")
            settings.default_video_fps = default_video_fps

        if theme_mode is not None:
            if theme_mode not in [t.value for t in ThemeMode]:
                raise ValueError(f"Invalid theme mode: {theme_mode}")
            settings.theme_mode = theme_mode

        if auto_save_enabled is not None:
            settings.auto_save_enabled = auto_save_enabled

        if show_advanced_options is not None:
            settings.show_advanced_options = show_advanced_options

        if auto_cleanup_temp_files is not None:
            settings.auto_cleanup_temp_files = auto_cleanup_temp_files

        if max_cache_size_gb is not None:
            if max_cache_size_gb < 1 or max_cache_size_gb > 100:
                raise ValueError("Max cache size must be between 1 and 100 GB")
            settings.max_cache_size_gb = max_cache_size_gb

        if default_export_format is not None:
            valid_formats = ["mp4_h264", "mp4_h265", "mov_prores", "webm_vp9", "mkv_h264"]
            if default_export_format not in valid_formats:
                raise ValueError(f"Invalid export format: {default_export_format}")
            settings.default_export_format = default_export_format

        if default_export_quality is not None:
            valid_qualities = ["draft", "standard", "high", "master"]
            if default_export_quality not in valid_qualities:
                raise ValueError(f"Invalid export quality: {default_export_quality}")
            settings.default_export_quality = default_export_quality

        if additional_settings is not None:
            settings.additional_settings = {
                **(settings.additional_settings or {}),
                **additional_settings,
            }

        await self._session.commit()
        await self._session.refresh(settings)
        return settings

    async def set_api_key(self, provider: str, api_key: str) -> bool:
        """Set API key for a provider.

        Args:
            provider: Provider name (anthropic, openai, replicate, fal, runwayml)
            api_key: API key value

        Returns:
            True if successful
        """
        settings = await self.get_settings()

        provider_lower = provider.lower()
        if provider_lower == "anthropic":
            settings.anthropic_api_key = api_key
        elif provider_lower == "openai":
            settings.openai_api_key = api_key
        elif provider_lower == "replicate":
            settings.replicate_api_key = api_key
        elif provider_lower == "fal":
            settings.fal_api_key = api_key
        elif provider_lower == "runwayml":
            settings.runwayml_api_key = api_key
        else:
            raise ValueError(f"Unknown provider: {provider}")

        await self._session.commit()
        return True

    async def remove_api_key(self, provider: str) -> bool:
        """Remove API key for a provider.

        Args:
            provider: Provider name

        Returns:
            True if successful
        """
        return await self.set_api_key(provider, "")

    async def validate_api_key(self, provider: str, api_key: Optional[str] = None) -> ProviderStatus:
        """Validate an API key by testing the provider.

        Args:
            provider: Provider name
            api_key: Optional API key to test (uses stored key if not provided)

        Returns:
            ProviderStatus with validation result
        """
        settings = await self.get_settings()

        # Get the key to test
        if api_key is None:
            key_map = {
                "anthropic": settings.anthropic_api_key,
                "openai": settings.openai_api_key,
                "replicate": settings.replicate_api_key,
                "fal": settings.fal_api_key,
                "runwayml": settings.runwayml_api_key,
            }
            api_key = key_map.get(provider.lower(), "")

        if not api_key:
            return ProviderStatus(
                provider=provider,
                name=provider.title(),
                available=False,
                configured=False,
                message="No API key configured",
            )

        # Test the key based on provider
        try:
            if provider.lower() == "anthropic":
                return await self._test_anthropic_key(api_key)
            elif provider.lower() == "openai":
                return await self._test_openai_key(api_key)
            elif provider.lower() == "replicate":
                return await self._test_replicate_key(api_key)
            elif provider.lower() == "fal":
                return await self._test_fal_key(api_key)
            elif provider.lower() == "runwayml":
                return await self._test_runwayml_key(api_key)
            else:
                return ProviderStatus(
                    provider=provider,
                    name=provider.title(),
                    available=False,
                    configured=False,
                    message=f"Unknown provider: {provider}",
                )
        except Exception as e:
            logger.error(f"Error validating {provider} API key: {e}")
            return ProviderStatus(
                provider=provider,
                name=provider.title(),
                available=False,
                configured=True,
                message=f"Validation error: {str(e)}",
            )

    async def _test_anthropic_key(self, api_key: str) -> ProviderStatus:
        """Test Anthropic API key."""
        import time

        start = time.time()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    timeout=10.0,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return ProviderStatus(
                        provider="anthropic",
                        name="Anthropic",
                        available=True,
                        configured=True,
                        message="API key valid",
                        latency_ms=latency,
                    )
                elif response.status_code == 401:
                    return ProviderStatus(
                        provider="anthropic",
                        name="Anthropic",
                        available=False,
                        configured=True,
                        message="Invalid API key",
                    )
                else:
                    return ProviderStatus(
                        provider="anthropic",
                        name="Anthropic",
                        available=False,
                        configured=True,
                        message=f"API error: {response.status_code}",
                    )
            except httpx.TimeoutException:
                return ProviderStatus(
                    provider="anthropic",
                    name="Anthropic",
                    available=False,
                    configured=True,
                    message="Connection timeout",
                )

    async def _test_openai_key(self, api_key: str) -> ProviderStatus:
        """Test OpenAI API key."""
        import time

        start = time.time()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return ProviderStatus(
                        provider="openai",
                        name="OpenAI",
                        available=True,
                        configured=True,
                        message="API key valid",
                        latency_ms=latency,
                    )
                elif response.status_code == 401:
                    return ProviderStatus(
                        provider="openai",
                        name="OpenAI",
                        available=False,
                        configured=True,
                        message="Invalid API key",
                    )
                else:
                    return ProviderStatus(
                        provider="openai",
                        name="OpenAI",
                        available=False,
                        configured=True,
                        message=f"API error: {response.status_code}",
                    )
            except httpx.TimeoutException:
                return ProviderStatus(
                    provider="openai",
                    name="OpenAI",
                    available=False,
                    configured=True,
                    message="Connection timeout",
                )

    async def _test_replicate_key(self, api_key: str) -> ProviderStatus:
        """Test Replicate API key."""
        import time

        start = time.time()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.replicate.com/v1/account",
                    headers={"Authorization": f"Token {api_key}"},
                    timeout=10.0,
                )
                latency = (time.time() - start) * 1000

                if response.status_code == 200:
                    return ProviderStatus(
                        provider="replicate",
                        name="Replicate",
                        available=True,
                        configured=True,
                        message="API key valid",
                        latency_ms=latency,
                    )
                elif response.status_code == 401:
                    return ProviderStatus(
                        provider="replicate",
                        name="Replicate",
                        available=False,
                        configured=True,
                        message="Invalid API key",
                    )
                else:
                    return ProviderStatus(
                        provider="replicate",
                        name="Replicate",
                        available=False,
                        configured=True,
                        message=f"API error: {response.status_code}",
                    )
            except httpx.TimeoutException:
                return ProviderStatus(
                    provider="replicate",
                    name="Replicate",
                    available=False,
                    configured=True,
                    message="Connection timeout",
                )

    async def _test_fal_key(self, api_key: str) -> ProviderStatus:
        """Test Fal.ai API key."""
        import time

        start = time.time()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://fal.run/fal-ai/flux/schnell",
                    headers={"Authorization": f"Key {api_key}"},
                    timeout=10.0,
                )
                latency = (time.time() - start) * 1000

                # Fal returns 400 for GET (expects POST) but validates auth
                if response.status_code in [200, 400, 405]:
                    return ProviderStatus(
                        provider="fal",
                        name="Fal.ai",
                        available=True,
                        configured=True,
                        message="API key valid",
                        latency_ms=latency,
                    )
                elif response.status_code == 401:
                    return ProviderStatus(
                        provider="fal",
                        name="Fal.ai",
                        available=False,
                        configured=True,
                        message="Invalid API key",
                    )
                else:
                    return ProviderStatus(
                        provider="fal",
                        name="Fal.ai",
                        available=False,
                        configured=True,
                        message=f"API error: {response.status_code}",
                    )
            except httpx.TimeoutException:
                return ProviderStatus(
                    provider="fal",
                    name="Fal.ai",
                    available=False,
                    configured=True,
                    message="Connection timeout",
                )

    async def _test_runwayml_key(self, api_key: str) -> ProviderStatus:
        """Test RunwayML API key."""
        # RunwayML doesn't have a simple auth test endpoint
        # Just verify key format for now
        if api_key and len(api_key) > 10:
            return ProviderStatus(
                provider="runwayml",
                name="RunwayML",
                available=True,
                configured=True,
                message="API key configured (format valid)",
            )
        return ProviderStatus(
            provider="runwayml",
            name="RunwayML",
            available=False,
            configured=True,
            message="Invalid API key format",
        )

    async def check_all_providers(self) -> List[ProviderStatus]:
        """Check status of all configured providers.

        Returns:
            List of ProviderStatus for all providers
        """
        providers = ["anthropic", "openai", "replicate", "fal", "runwayml"]
        tasks = [self.validate_api_key(p) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        statuses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                statuses.append(ProviderStatus(
                    provider=providers[i],
                    name=providers[i].title(),
                    available=False,
                    configured=False,
                    message=f"Error: {str(result)}",
                ))
            else:
                statuses.append(result)

        # Add local provider (always available)
        statuses.insert(0, ProviderStatus(
            provider="local",
            name="Local (Mock)",
            available=True,
            configured=True,
            message="Local generation available",
        ))

        return statuses

    async def get_storage_stats(self) -> StorageStats:
        """Get storage statistics.

        Returns:
            StorageStats with directory sizes
        """
        def get_dir_size(path: Path) -> int:
            """Calculate total size of directory."""
            total = 0
            if path.exists():
                for p in path.rglob("*"):
                    if p.is_file():
                        try:
                            total += p.stat().st_size
                        except (OSError, PermissionError):
                            pass
            return total

        def count_temp_files(path: Path) -> int:
            """Count temporary files."""
            count = 0
            if path.exists():
                for p in path.rglob("*.tmp"):
                    count += 1
                for p in path.rglob("temp_*"):
                    count += 1
            return count

        data_dir = self._app_settings.data_dir
        upload_dir = self._app_settings.upload_dir
        output_dir = self._app_settings.output_dir
        cache_dir = self._app_settings.model_cache_dir

        # Calculate sizes (can be slow for large directories)
        upload_size = get_dir_size(upload_dir)
        output_size = get_dir_size(output_dir)
        cache_size = get_dir_size(cache_dir)
        total_size = get_dir_size(data_dir)
        temp_count = count_temp_files(data_dir)

        return StorageStats(
            data_dir=str(data_dir),
            upload_dir=str(upload_dir),
            output_dir=str(output_dir),
            cache_dir=str(cache_dir),
            total_size_bytes=total_size,
            upload_size_bytes=upload_size,
            output_size_bytes=output_size,
            cache_size_bytes=cache_size,
            temp_files_count=temp_count,
        )

    async def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """Clear cached files.

        Args:
            cache_type: Type of cache to clear (model, temp, output, all)

        Returns:
            Dict with cleared items info
        """
        cleared = {
            "model_cache": 0,
            "temp_files": 0,
            "bytes_freed": 0,
        }

        if cache_type in ["model", "all"]:
            cache_dir = self._app_settings.model_cache_dir
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    try:
                        size = item.stat().st_size if item.is_file() else 0
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                        cleared["model_cache"] += 1
                        cleared["bytes_freed"] += size
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Failed to remove {item}: {e}")

        if cache_type in ["temp", "all"]:
            data_dir = self._app_settings.data_dir
            if data_dir.exists():
                for pattern in ["*.tmp", "temp_*"]:
                    for item in data_dir.rglob(pattern):
                        try:
                            size = item.stat().st_size if item.is_file() else 0
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item)
                            cleared["temp_files"] += 1
                            cleared["bytes_freed"] += size
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Failed to remove {item}: {e}")

        return cleared

    async def get_available_llm_providers(self) -> List[Dict[str, Any]]:
        """Get list of available LLM providers.

        Returns:
            List of provider info dicts
        """
        return [
            {
                "value": LLMProvider.ANTHROPIC.value,
                "label": "Anthropic (Claude)",
                "description": "Claude models for screenplay analysis and planning",
                "requiresKey": True,
            },
            {
                "value": LLMProvider.OPENAI.value,
                "label": "OpenAI (GPT)",
                "description": "GPT models for text generation",
                "requiresKey": True,
            },
        ]

    async def get_available_video_providers(self) -> List[Dict[str, Any]]:
        """Get list of available video generation providers.

        Returns:
            List of provider info dicts
        """
        return [
            {
                "value": VideoProvider.LOCAL.value,
                "label": "Local (Mock)",
                "description": "Local mock generation for testing",
                "requiresKey": False,
            },
            {
                "value": VideoProvider.REPLICATE.value,
                "label": "Replicate",
                "description": "Cloud video generation via Replicate API",
                "requiresKey": True,
            },
            {
                "value": VideoProvider.FAL.value,
                "label": "Fal.ai",
                "description": "Fast video generation with Fal.ai",
                "requiresKey": True,
            },
            {
                "value": VideoProvider.RUNWAYML.value,
                "label": "RunwayML",
                "description": "Professional video generation with RunwayML",
                "requiresKey": True,
            },
        ]

    async def get_theme_options(self) -> List[Dict[str, str]]:
        """Get available theme options.

        Returns:
            List of theme option dicts
        """
        return [
            {"value": ThemeMode.SYSTEM.value, "label": "System"},
            {"value": ThemeMode.LIGHT.value, "label": "Light"},
            {"value": ThemeMode.DARK.value, "label": "Dark"},
        ]

    async def export_settings(self) -> Dict[str, Any]:
        """Export settings for backup (excluding sensitive data).

        Returns:
            Settings dict without API keys
        """
        settings = await self.get_settings()
        return settings.to_dict(include_keys=False)

    async def import_settings(self, data: Dict[str, Any]) -> UserSettings:
        """Import settings from backup.

        Args:
            data: Settings dict to import

        Returns:
            Updated UserSettings
        """
        # Map from camelCase to snake_case
        update_data = {}
        field_map = {
            "llmProvider": "llm_provider",
            "videoProvider": "video_provider",
            "maxConcurrentGenerations": "max_concurrent_generations",
            "generationTimeoutSeconds": "generation_timeout_seconds",
            "defaultVideoResolution": "default_video_resolution",
            "defaultVideoFps": "default_video_fps",
            "themeMode": "theme_mode",
            "autoSaveEnabled": "auto_save_enabled",
            "showAdvancedOptions": "show_advanced_options",
            "autoCleanupTempFiles": "auto_cleanup_temp_files",
            "maxCacheSizeGb": "max_cache_size_gb",
            "defaultExportFormat": "default_export_format",
            "defaultExportQuality": "default_export_quality",
            "additionalSettings": "additional_settings",
        }

        for camel, snake in field_map.items():
            if camel in data:
                update_data[snake] = data[camel]

        return await self.update_settings(**update_data)
