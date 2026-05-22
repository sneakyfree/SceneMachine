"""GPU Provider Registry for managing available providers.

Handles registration, discovery, and configuration of GPU providers.
"""

import logging
from typing import Any, Optional

from scenemachine.gpu_exchange.base import (
    GPUExchangeProvider,
    GPUType,
    ProviderHealth,
)

logger = logging.getLogger(__name__)


class GPUProviderRegistry:
    """Central registry for GPU Exchange providers.

    Manages provider registration, discovery, and lifecycle.
    Implements singleton pattern for global access.

    Usage:
        # Register a provider
        registry = GPUProviderRegistry.get_instance()
        registry.register("lambda_labs", LambdaLabsProvider)

        # Get a provider instance
        provider = registry.get_provider("lambda_labs", api_key="...")

        # List available providers
        providers = registry.list_providers()
    """

    _instance: Optional["GPUProviderRegistry"] = None

    def __init__(self) -> None:
        # Map of provider_id -> provider class
        self._provider_classes: dict[str, type[GPUExchangeProvider]] = {}
        # Map of provider_id -> instantiated provider (cached)
        self._provider_instances: dict[str, GPUExchangeProvider] = {}
        # Provider configuration
        self._provider_configs: dict[str, dict[str, Any]] = {}
        # Provider priority (lower = higher priority)
        self._provider_priorities: dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> "GPUProviderRegistry":
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset registry (useful for testing)."""
        cls._instance = None

    def register(
        self,
        provider_id: str,
        provider_class: type[GPUExchangeProvider],
        config: dict[str, Any] | None = None,
        priority: int = 100,
    ) -> None:
        """Register a GPU provider class.

        Args:
            provider_id: Unique identifier for the provider
            provider_class: The provider class (not instance)
            config: Optional default configuration
            priority: Provider priority (lower = higher priority)
        """
        self._provider_classes[provider_id] = provider_class
        if config:
            self._provider_configs[provider_id] = config
        self._provider_priorities[provider_id] = priority
        # Clear any cached instance
        self._provider_instances.pop(provider_id, None)
        logger.debug(f"Registered GPU provider: {provider_id}")

    def unregister(self, provider_id: str) -> None:
        """Unregister a provider."""
        self._provider_classes.pop(provider_id, None)
        self._provider_instances.pop(provider_id, None)
        self._provider_configs.pop(provider_id, None)
        self._provider_priorities.pop(provider_id, None)

    def get_provider(
        self,
        provider_id: str,
        **kwargs: Any,
    ) -> GPUExchangeProvider | None:
        """Get a provider instance.

        Args:
            provider_id: The provider ID to get
            **kwargs: Configuration to pass to provider constructor

        Returns:
            Provider instance or None if not registered
        """
        if provider_id not in self._provider_classes:
            return None

        # Check for cached instance (only if no custom kwargs)
        if not kwargs and provider_id in self._provider_instances:
            return self._provider_instances[provider_id]

        # Merge default config with kwargs
        config = {**self._provider_configs.get(provider_id, {}), **kwargs}

        # Instantiate provider
        provider_class = self._provider_classes[provider_id]
        try:
            provider = provider_class(**config)

            # Cache if using default config
            if not kwargs:
                self._provider_instances[provider_id] = provider

            return provider
        except Exception as e:
            logger.error(f"Failed to instantiate GPU provider {provider_id}: {e}")
            return None

    def get_provider_class(self, provider_id: str) -> type[GPUExchangeProvider] | None:
        """Get provider class without instantiation."""
        return self._provider_classes.get(provider_id)

    def is_registered(self, provider_id: str) -> bool:
        """Check if a provider is registered."""
        return provider_id in self._provider_classes

    def list_providers(self) -> list[str]:
        """List all registered provider IDs."""
        return list(self._provider_classes.keys())

    def list_providers_by_priority(self) -> list[str]:
        """List providers sorted by priority (highest first)."""
        return sorted(
            self._provider_classes.keys(),
            key=lambda p: self._provider_priorities.get(p, 100),
        )

    def get_providers_for_gpu(self, gpu_type: GPUType) -> list[str]:
        """Get providers that support a specific GPU type."""
        providers = []
        for provider_id in self._provider_classes:
            provider = self.get_provider(provider_id)
            if provider and gpu_type in provider.supported_gpu_types:
                providers.append(provider_id)
        return providers

    async def list_available_providers(self) -> list[str]:
        """List providers that are currently available."""
        available = []
        for provider_id in self._provider_classes:
            provider = self.get_provider(provider_id)
            if provider and await provider.check_availability():
                available.append(provider_id)
        return available

    async def get_all_health(self) -> dict[str, ProviderHealth]:
        """Get health status of all registered providers."""
        health = {}
        for provider_id in self._provider_classes:
            provider = self.get_provider(provider_id)
            if provider:
                health[provider_id] = await provider.check_health()
            else:
                health[provider_id] = ProviderHealth(
                    available=False,
                    message="Failed to instantiate provider",
                    error_code="INSTANTIATION_FAILED",
                )
        return health

    def get_provider_info(self, provider_id: str) -> dict[str, Any] | None:
        """Get information about a provider."""
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        return {
            "id": provider_id,
            "name": provider.name,
            "priority": self._provider_priorities.get(provider_id, 100),
            "capabilities": [c.value for c in provider.capabilities],
            "supported_gpu_types": [g.value for g in provider.supported_gpu_types],
            "regions": provider.regions,
        }


def get_provider_registry() -> GPUProviderRegistry:
    """Get the global GPU provider registry."""
    return GPUProviderRegistry.get_instance()
