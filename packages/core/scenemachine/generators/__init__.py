"""Video generation providers and orchestration.

This module provides video generation capabilities through multiple providers:
- ReplicateProvider: Cloud-based generation via Replicate.com
- FalProvider: Cloud-based generation via Fal.ai
- ComfyUIProvider: Local generation via ComfyUI
- RunPodProvider: Serverless GPU generation via RunPod
- MockGenerationProvider: Local mock for development/testing

Usage:
    from scenemachine.generators import (
        get_provider_registry,
        ReplicateProvider,
        FalProvider,
    )

    # Using the registry (recommended)
    registry = get_provider_registry()
    provider = registry.get_provider(JobProvider.REPLICATE, api_token="...")

    # Or create directly
    provider = ReplicateProvider(api_token="your-token", model_id="minimax")

    # Estimate cost
    cost = provider.estimate_cost(duration_seconds=3.0)

    # Generate video
    result = await provider.generate(request, progress_callback)
"""

# Base classes and interfaces
# Import from services for backwards compatibility
from scenemachine.services.generation import (
    GenerationService,
    get_generation_service,
)
from scenemachine.services.queue_worker import (
    QueueWorker,
    WorkerStats,
    get_queue_worker,
    managed_queue_worker,
    start_queue_worker,
    stop_queue_worker,
)

# Provider implementations
from .actcore import ActCoreProvider
from .base import (
    GenerationProgress,
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    ProgressCallback,
    ProviderCapabilities,
    ProviderFeature,
    ProviderHealth,
    ProviderRegistry,
    VideoModel,
    get_provider_registry,
)
from .comfyui import ComfyUIProvider
from .fal import FalProvider
from .mock import MockGenerationProvider

# Registry setup
from .registry import (
    check_provider_status,
    register_builtin_providers,
    setup_providers,
)
from .replicate import ReplicateProvider
from .runpod import RunPodProvider

__all__ = [
    # Base classes and interfaces
    "GenerationProvider",
    "GenerationRequest",
    "GenerationResult",
    "GenerationProgress",
    "ProgressCallback",
    "ProviderCapabilities",
    "ProviderFeature",
    "ProviderHealth",
    "ProviderRegistry",
    "VideoModel",
    "get_provider_registry",
    # Provider implementations
    "ActCoreProvider",
    "ReplicateProvider",
    "FalProvider",
    "ComfyUIProvider",
    "RunPodProvider",
    "MockGenerationProvider",
    # Registry setup
    "setup_providers",
    "register_builtin_providers",
    "check_provider_status",
    # Service (backwards compatibility)
    "GenerationService",
    "get_generation_service",
    # Queue worker
    "QueueWorker",
    "WorkerStats",
    "get_queue_worker",
    "start_queue_worker",
    "stop_queue_worker",
    "managed_queue_worker",
]
