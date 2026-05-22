"""Provider registry setup and initialization.

This module handles the registration of all built-in providers
and provides utilities for provider discovery.
"""

import logging

from scenemachine.config import get_settings
from scenemachine.models.generation_job import JobProvider

from .base import (
    ProviderRegistry,
    get_provider_registry,
)

logger = logging.getLogger(__name__)


def register_builtin_providers(registry: ProviderRegistry | None = None) -> None:
    """Register all built-in providers with the registry.

    This is called automatically during application startup.
    Providers are registered with their default configurations
    based on environment settings.
    """
    if registry is None:
        registry = get_provider_registry()

    settings = get_settings()

    # Import providers here to avoid circular imports
    from .actcore import ActCoreProvider
    from .comfyui import ComfyUIProvider
    from .fal import FalProvider
    from .mock import MockGenerationProvider
    from .replicate import ReplicateProvider
    from .runpod import RunPodProvider

    # Register the local ComfyUI provider FIRST as JobProvider.LOCAL —
    # the renderer maps the "local" UI option to JobProvider.LOCAL, and
    # users expect "local" to mean "the ComfyUI running on this machine",
    # not a mock. The mock provider used to claim this slot, which made
    # generation.getProviderModels('local') return only "mock" and hid
    # the validated Wan 2.2 T2V / I2V / Animate + LTX-2 model entries.
    # If the user has no local ComfyUI configured, the provider will
    # still register but its check_availability() will return False —
    # better signal than silently returning a mock.
    comfyui_url = getattr(settings, "comfyui_url", None)
    registry.register(
        JobProvider.LOCAL,
        ComfyUIProvider,
        config={"comfyui_url": comfyui_url or "http://127.0.0.1:8188"},
    )
    logger.debug("Registered ComfyUIProvider as LOCAL")

    # Mock provider remains available as JobProvider.CUSTOM for tests and
    # dev environments that explicitly opt in. Importantly it is NOT the
    # default for any production flow.
    registry.register(JobProvider.CUSTOM, MockGenerationProvider)
    logger.debug("Registered MockGenerationProvider as CUSTOM (test-only)")

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

    # (ComfyUI was registered as LOCAL at the top of this function so
    # 'local' in the renderer routes correctly to the real ComfyUI
    # provider — see comment there. The legacy CUSTOM slot now holds the
    # MockGenerationProvider for test-only use.)

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

    # Register ActCore provider (performer-driven retargeting)
    comfyui_url = getattr(settings, "comfyui_url", None)
    registry.register(
        JobProvider.ACTCORE,
        ActCoreProvider,
        config={
            "comfyui_url": comfyui_url or "http://127.0.0.1:8188",
            "local_processing": True,
        },
    )
    logger.debug("Registered ActCoreProvider")

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
