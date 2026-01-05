"""GPU Exchange - Dynamic GPU provider routing and management.

This module provides intelligent routing to the lowest-cost GPU providers
with automatic failover and load balancing.

Supported Providers:
- Lambda Labs
- RunPod (enhanced)
- Vast.ai
- FluidStack
- CoreWeave

Usage:
    from scenemachine.gpu_exchange import (
        get_gpu_exchange,
        GPUExchangeRouter,
        GPUInstance,
    )

    # Get router instance
    router = get_gpu_exchange()

    # Get optimal provider for a job
    selection = await router.select_provider(job_request, config)

    # Route job to selected provider
    result = await router.route_job(job, selection)
"""

from scenemachine.gpu_exchange.base import (
    GPUExchangeProvider,
    GPUInstance,
    GPUPricing,
    GPUType,
    ProviderCapability,
)
from scenemachine.gpu_exchange.registry import (
    GPUProviderRegistry,
    get_provider_registry,
)
from scenemachine.gpu_exchange.pricing import (
    PricingService,
    PricingTier,
    get_pricing_service,
)
from scenemachine.gpu_exchange.router import (
    GPUExchangeRouter,
    ProviderSelection,
    RoutingConfig,
    RoutingDecision,
    get_gpu_exchange,
)

__all__ = [
    # Base classes
    "GPUExchangeProvider",
    "GPUInstance",
    "GPUPricing",
    "GPUType",
    "ProviderCapability",
    # Registry
    "GPUProviderRegistry",
    "get_provider_registry",
    # Pricing
    "PricingService",
    "PricingTier",
    "get_pricing_service",
    # Router
    "GPUExchangeRouter",
    "ProviderSelection",
    "RoutingConfig",
    "RoutingDecision",
    "get_gpu_exchange",
]
