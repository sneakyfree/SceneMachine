"""Video generation providers and orchestration.

This module provides video generation capabilities through multiple providers:
- ReplicateProvider: Cloud-based generation via Replicate.com
- FalProvider: Cloud-based generation via Fal.ai
- MockGenerationProvider: Local mock for development/testing

Usage:
    from scenemachine.generators import ReplicateProvider, FalProvider

    # Create a provider
    provider = ReplicateProvider(api_token="your-token", model_id="minimax")

    # Estimate cost
    cost = provider.estimate_cost(duration_seconds=3.0)

    # Generate video
    result = await provider.generate(request, progress_callback)
"""

from scenemachine.services.generation import (
    # Base classes
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    GenerationProgress,
    ProgressCallback,
    VideoModel,
    # Providers
    ReplicateProvider,
    FalProvider,
    MockGenerationProvider,
    # Service
    GenerationService,
    get_generation_service,
)

from scenemachine.services.queue_worker import (
    QueueWorker,
    WorkerStats,
    get_queue_worker,
    start_queue_worker,
    stop_queue_worker,
    managed_queue_worker,
)

__all__ = [
    # Base classes
    "GenerationProvider",
    "GenerationRequest",
    "GenerationResult",
    "GenerationProgress",
    "ProgressCallback",
    "VideoModel",
    # Providers
    "ReplicateProvider",
    "FalProvider",
    "MockGenerationProvider",
    # Service
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
