"""Base classes and interfaces for video generation providers.

This module defines the core abstractions for the provider plugin system:
- GenerationProvider: Abstract base class all providers must implement
- ProviderCapabilities: Declares what a provider can do
- ProviderRegistry: Central registry for provider discovery and management
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID

from scenemachine.models.generation_job import JobProvider


class ProviderFeature(StrEnum):
    """Features a provider may support."""

    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    UPSCALING = "upscaling"
    INTERPOLATION = "interpolation"
    INPAINTING = "inpainting"
    STYLE_TRANSFER = "style_transfer"
    CHARACTER_CONSISTENCY = "character_consistency"
    LORA_SUPPORT = "lora_support"
    CONTROLNET = "controlnet"


@dataclass
class ProviderCapabilities:
    """Declares the capabilities of a provider."""

    # Supported features
    features: list[ProviderFeature] = field(default_factory=list)

    # Resolution limits
    min_width: int = 256
    max_width: int = 1920
    min_height: int = 256
    max_height: int = 1080

    # Duration limits (seconds)
    min_duration: float = 1.0
    max_duration: float = 10.0

    # FPS support
    supported_fps: list[int] = field(default_factory=lambda: [8, 12, 16, 24, 30])

    # Aspect ratios
    supported_aspect_ratios: list[str] = field(
        default_factory=lambda: ["16:9", "9:16", "1:1", "4:3", "3:4"]
    )

    # Concurrency
    max_concurrent_jobs: int = 1

    # Cost info
    supports_cost_estimation: bool = True

    def supports(self, feature: ProviderFeature) -> bool:
        """Check if provider supports a feature."""
        return feature in self.features


@dataclass
class VideoModel:
    """Video generation model configuration."""

    id: str
    name: str
    version: str = ""
    cost_per_second: float = 0.0  # USD per second of video
    supports_text_to_video: bool = True
    supports_image_to_video: bool = False
    max_duration: float = 4.0
    default_fps: int = 24
    default_steps: int = 50
    default_cfg_scale: float = 7.5
    input_mapping: dict[str, str] = field(default_factory=dict)
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationRequest:
    """Request for generating video content."""

    shot_id: UUID
    prompt: str
    negative_prompt: str = ""
    width: int = 1280
    height: int = 720
    fps: int = 24
    duration_seconds: float = 3.0
    seed: int | None = None
    guidance_scale: float = 7.5
    num_inference_steps: int = 50
    character_references: list[dict[str, Any]] = field(default_factory=list)
    style_preset: str | None = None
    input_image_path: str | None = None
    input_video_path: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result from a generation attempt."""

    success: bool
    output_path: str | None = None
    thumbnail_path: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    duration_seconds: float | None = None
    cost_usd: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationProgress:
    """Progress update for a generation job."""

    job_id: UUID
    percent: float
    message: str
    stage: str = "generating"


# Type alias for progress callbacks
ProgressCallback = Callable[[GenerationProgress], Any]


@dataclass
class ProviderHealth:
    """Health status of a provider."""

    available: bool
    message: str
    latency_ms: float | None = None
    models_available: int = 0
    queue_length: int | None = None
    error_code: str | None = None


class GenerationProvider(ABC):
    """Abstract base class for video generation providers.

    All providers must implement this interface to be compatible
    with the SceneMachine generation pipeline.

    Example:
        class MyProvider(GenerationProvider):
            @property
            def name(self) -> str:
                return "My Provider"

            @property
            def provider_type(self) -> JobProvider:
                return JobProvider.CUSTOM

            async def generate(self, request, callback) -> GenerationResult:
                # Implementation
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def provider_type(self) -> JobProvider:
        """Provider type enum value."""
        ...

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Provider capabilities. Override to customize."""
        return ProviderCapabilities(
            features=[ProviderFeature.TEXT_TO_VIDEO],
        )

    @abstractmethod
    async def generate(
        self,
        request: GenerationRequest,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Execute video generation.

        Args:
            request: Generation request parameters
            progress_callback: Optional callback for progress updates

        Returns:
            GenerationResult with output path or error
        """
        ...

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if provider is available and configured."""
        ...

    async def check_health(self) -> ProviderHealth:
        """Detailed health check. Override for custom implementation."""
        try:
            available = await self.check_availability()
            return ProviderHealth(
                available=available,
                message="Provider available" if available else "Provider unavailable",
                models_available=len(self.list_models()) if hasattr(self, 'list_models') else 0,
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                message=str(e),
                error_code="HEALTH_CHECK_FAILED",
            )

    async def cancel(self, provider_job_id: str) -> bool:
        """Cancel a running job. Returns True if cancelled."""
        return False

    def estimate_cost(
        self,
        duration_seconds: float = 3.0,
        model_id: str | None = None,
    ) -> float:
        """Estimate generation cost in USD. Override to customize."""
        return 0.0

    def list_models(self) -> list[dict[str, Any]]:
        """List available models. Override to customize."""
        return []

    def get_model(self, model_id: str) -> VideoModel | None:
        """Get model configuration by ID. Override to customize."""
        return None

    def validate_request(self, request: GenerationRequest) -> list[str]:
        """Validate a generation request. Returns list of error messages."""
        errors = []
        caps = self.capabilities

        if request.width < caps.min_width or request.width > caps.max_width:
            errors.append(
                f"Width {request.width} outside supported range "
                f"[{caps.min_width}, {caps.max_width}]"
            )

        if request.height < caps.min_height or request.height > caps.max_height:
            errors.append(
                f"Height {request.height} outside supported range "
                f"[{caps.min_height}, {caps.max_height}]"
            )

        if request.duration_seconds < caps.min_duration:
            errors.append(
                f"Duration {request.duration_seconds}s below minimum {caps.min_duration}s"
            )

        if request.duration_seconds > caps.max_duration:
            errors.append(
                f"Duration {request.duration_seconds}s exceeds maximum {caps.max_duration}s"
            )

        if request.fps not in caps.supported_fps:
            errors.append(
                f"FPS {request.fps} not in supported values: {caps.supported_fps}"
            )

        return errors


class ProviderRegistry:
    """Central registry for video generation providers.

    Manages provider registration, discovery, and lifecycle.
    Implements singleton pattern for global access.

    Usage:
        # Register a provider
        registry = ProviderRegistry.get_instance()
        registry.register(JobProvider.CUSTOM, MyProvider)

        # Get a provider instance
        provider = registry.get_provider(JobProvider.CUSTOM, api_key="...")

        # List available providers
        providers = registry.list_providers()
    """

    _instance: Optional["ProviderRegistry"] = None

    def __init__(self) -> None:
        # Map of provider type -> provider class
        self._provider_classes: dict[JobProvider, type[GenerationProvider]] = {}
        # Map of provider type -> instantiated provider (cached)
        self._provider_instances: dict[JobProvider, GenerationProvider] = {}
        # Provider configuration
        self._provider_configs: dict[JobProvider, dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "ProviderRegistry":
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
        provider_type: JobProvider,
        provider_class: type[GenerationProvider],
        config: dict[str, Any] | None = None,
    ) -> None:
        """Register a provider class.

        Args:
            provider_type: The JobProvider enum value
            provider_class: The provider class (not instance)
            config: Optional default configuration for the provider
        """
        self._provider_classes[provider_type] = provider_class
        if config:
            self._provider_configs[provider_type] = config
        # Clear any cached instance
        self._provider_instances.pop(provider_type, None)

    def unregister(self, provider_type: JobProvider) -> None:
        """Unregister a provider."""
        self._provider_classes.pop(provider_type, None)
        self._provider_instances.pop(provider_type, None)
        self._provider_configs.pop(provider_type, None)

    def get_provider(
        self,
        provider_type: JobProvider,
        **kwargs: Any,
    ) -> GenerationProvider | None:
        """Get a provider instance.

        Args:
            provider_type: The provider type to get
            **kwargs: Configuration to pass to provider constructor

        Returns:
            Provider instance or None if not registered
        """
        if provider_type not in self._provider_classes:
            return None

        # Check for cached instance (only if no custom kwargs)
        if not kwargs and provider_type in self._provider_instances:
            return self._provider_instances[provider_type]

        # Merge default config with kwargs
        config = {**self._provider_configs.get(provider_type, {}), **kwargs}

        # Instantiate provider
        provider_class = self._provider_classes[provider_type]
        try:
            provider = provider_class(**config)

            # Cache if using default config
            if not kwargs:
                self._provider_instances[provider_type] = provider

            return provider
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to instantiate provider {provider_type}: {e}"
            )
            return None

    def get_provider_class(
        self, provider_type: JobProvider
    ) -> type[GenerationProvider] | None:
        """Get provider class without instantiation."""
        return self._provider_classes.get(provider_type)

    def is_registered(self, provider_type: JobProvider) -> bool:
        """Check if a provider type is registered."""
        return provider_type in self._provider_classes

    def list_providers(self) -> list[JobProvider]:
        """List all registered provider types."""
        return list(self._provider_classes.keys())

    async def list_available_providers(self) -> list[JobProvider]:
        """List providers that are currently available."""
        available = []
        for provider_type in self._provider_classes:
            provider = self.get_provider(provider_type)
            if provider and await provider.check_availability():
                available.append(provider_type)
        return available

    async def get_all_health(self) -> dict[JobProvider, ProviderHealth]:
        """Get health status of all registered providers."""
        health = {}
        for provider_type in self._provider_classes:
            provider = self.get_provider(provider_type)
            if provider:
                health[provider_type] = await provider.check_health()
            else:
                health[provider_type] = ProviderHealth(
                    available=False,
                    message="Failed to instantiate provider",
                    error_code="INSTANTIATION_FAILED",
                )
        return health

    def get_provider_info(self, provider_type: JobProvider) -> dict[str, Any] | None:
        """Get information about a provider."""
        provider = self.get_provider(provider_type)
        if not provider:
            return None

        return {
            "type": provider_type.value,
            "name": provider.name,
            "capabilities": {
                "features": [f.value for f in provider.capabilities.features],
                "max_width": provider.capabilities.max_width,
                "max_height": provider.capabilities.max_height,
                "max_duration": provider.capabilities.max_duration,
                "supported_fps": provider.capabilities.supported_fps,
            },
            "models": provider.list_models(),
        }


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    return ProviderRegistry.get_instance()
