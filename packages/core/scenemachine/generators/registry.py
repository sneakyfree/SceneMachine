"""Provider registry setup and initialization.

This module handles the registration of all built-in providers
and provides utilities for provider discovery.
"""

import logging
from typing import Optional

from scenemachine.config import get_settings
from scenemachine.models.generation_job import JobProvider

from .base import (
    GenerationProvider,
    ProviderRegistry,
    get_provider_registry,
)

logger = logging.getLogger(__name__)


def register_builtin_providers(registry: Optional[ProviderRegistry] = None) -> None:
    """Register all built-in providers with the registry.

    This is called automatically during application startup.
    Providers are registered with their default configurations
    based on environment settings.
    """
    if registry is None:
        registry = get_provider_registry()

    settings = get_settings()

    # Import providers here to avoid circular imports
    from .mock import MockGenerationProvider
    from .replicate import ReplicateProvider
    from .fal import FalProvider
    from .comfyui import ComfyUIProvider
    from .runpod import RunPodProvider

    # Always register mock provider for testing/development
    registry.register(JobProvider.LOCAL, MockGenerationProvider)
    logger.debug("Registered MockGenerationProvider as LOCAL")

    # Register Replicate provider
    registry.register(
        JobProvider.REPLICATE,
        ReplicateProvider,
        config={
            "api_token": settings.replicate_api_token,
            "model_id": settings.replicate_video_model,
        },
    )
    logger.debug("Registered ReplicateProvider")

    # Register Fal.ai provider
    registry.register(
        JobProvider.FAL,
        FalProvider,
        config={
            "api_key": settings.fal_api_key,
            "model_id": settings.fal_video_model,
        },
    )
    logger.debug("Registered FalProvider")

    # Register ComfyUI provider (local)
    comfyui_url = getattr(settings, "comfyui_url", None)
    registry.register(
        JobProvider.CUSTOM,  # Using CUSTOM for ComfyUI local
        ComfyUIProvider,
        config={
            "comfyui_url": comfyui_url or "http://127.0.0.1:8188",
        },
    )
    logger.debug("Registered ComfyUIProvider")

    # Register RunPod provider
    runpod_api_key = getattr(settings, "runpod_api_key", None)
    registry.register(
        JobProvider.RUNPOD,
        RunPodProvider,
        config={
            "api_key": runpod_api_key,
        },
    )
    logger.debug("Registered RunPodProvider")

    logger.info(f"Registered {len(registry.list_providers())} video generation providers")


def setup_providers() -> ProviderRegistry:
    """Initialize and return the provider registry.

    Call this during application startup to ensure all providers
    are registered and ready to use.

    Returns:
        Configured ProviderRegistry instance
    """
    registry = get_provider_registry()
    register_builtin_providers(registry)
    return registry


async def check_provider_status() -> dict:
    """Check status of all registered providers.

    Returns:
        Dict with provider status information
    """
    registry = get_provider_registry()
    health = await registry.get_all_health()

    return {
        "providers": [
            {
                "type": provider_type.value,
                "name": registry.get_provider(provider_type).name
                if registry.get_provider(provider_type)
                else "Unknown",
                "available": status.available,
                "message": status.message,
                "latency_ms": status.latency_ms,
                "models_available": status.models_available,
            }
            for provider_type, status in health.items()
        ],
        "total_registered": len(registry.list_providers()),
        "total_available": sum(1 for s in health.values() if s.available),
    }
