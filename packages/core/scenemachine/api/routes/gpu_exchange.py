"""GPU Exchange API routes.

Endpoints for managing GPU providers, pricing, and routing decisions.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from scenemachine.gpu_exchange.base import (
    GPUType,
    ProviderCapability,
)
from scenemachine.gpu_exchange.pricing import (
    PricingTier,
    get_pricing_service,
)
from scenemachine.gpu_exchange.registry import get_provider_registry
from scenemachine.gpu_exchange.router import (
    RoutingConfig,
    RoutingPriority,
    get_gpu_exchange,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gpu-exchange")


# ============================================================================
# Request/Response Models
# ============================================================================


class GPUTypeEnum(str):
    """String representation of GPU types for API."""

    pass


class ProviderInfoResponse(BaseModel):
    """Information about a GPU provider."""

    id: str
    name: str
    priority: int
    capabilities: list[str]
    supported_gpu_types: list[str]
    regions: list[str]


class ProviderHealthResponse(BaseModel):
    """Health status of a provider."""

    provider_id: str
    available: bool
    message: str
    latency_ms: float | None = None
    instances_available: int = 0
    queue_depth: int = 0
    error_code: str | None = None
    last_check: datetime


class AllProvidersHealthResponse(BaseModel):
    """Health status of all providers."""

    providers: dict[str, ProviderHealthResponse]
    healthy_count: int
    total_count: int


class GPUPricingResponse(BaseModel):
    """Pricing information for a GPU type."""

    gpu_type: str
    price_per_hour: float
    price_per_second: float
    spot_price_per_hour: float | None = None
    reserved_price_per_hour: float | None = None
    currency: str = "USD"
    region: str
    availability: int = 0
    last_updated: datetime


class PricingComparisonResponse(BaseModel):
    """Comparison of pricing across providers."""

    gpu_type: str
    region: str
    cheapest_provider: str
    cheapest_price: float
    fastest_provider: str
    best_value_provider: str
    all_options: list[dict[str, Any]]
    generated_at: datetime


class RoutingConfigRequest(BaseModel):
    """Configuration for routing a job."""

    priority: str = Field(
        default="normal",
        description="Job priority: low, normal, high, urgent",
    )
    max_price_usd: float | None = Field(
        default=None,
        description="Maximum budget for this job",
    )
    preferred_providers: list[str] = Field(
        default_factory=list,
        description="Preferred provider IDs",
    )
    excluded_providers: list[str] = Field(
        default_factory=list,
        description="Provider IDs to exclude",
    )
    preferred_regions: list[str] = Field(
        default_factory=lambda: ["us-east-1"],
        description="Preferred regions",
    )
    allow_spot: bool = Field(
        default=True,
        description="Allow spot/preemptible instances",
    )


class SelectProviderRequest(BaseModel):
    """Request to select optimal provider."""

    gpu_type: str = Field(..., description="GPU type required (e.g., 'a100_80gb')")
    duration_seconds: float = Field(..., description="Estimated job duration in seconds")
    config: RoutingConfigRequest | None = Field(
        default=None,
        description="Routing configuration",
    )
    required_capability: str = Field(
        default="video_generation",
        description="Required capability",
    )


class ProviderSelectionResponse(BaseModel):
    """Result of provider selection."""

    provider_id: str
    provider_name: str
    price_per_hour: float
    estimated_cost: float
    use_spot: bool
    fallback_providers: list[str]
    score_breakdown: dict[str, float]


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    gpu_type: str
    duration_seconds: float
    provider_id: str | None = None
    use_spot: bool = False


class CostEstimateResponse(BaseModel):
    """Cost estimation result."""

    provider_id: str
    gpu_type: str
    duration_seconds: float
    use_spot: bool
    estimated_cost_usd: float
    price_per_hour: float
    currency: str = "USD"


class RoutingStatsResponse(BaseModel):
    """Routing statistics."""

    total_routings: int
    successful: int
    success_rate: float
    failovers_used: int
    by_provider: dict[str, dict[str, int]]
    circuit_breakers: dict[str, str]
    reliability_scores: dict[str, float]


class BudgetLimitRequest(BaseModel):
    """Request to set a budget limit."""

    project_id: str
    limit_usd: float = Field(..., ge=0, description="Budget limit in USD")


class BudgetCheckRequest(BaseModel):
    """Request to check budget."""

    project_id: str
    estimated_cost: float
    current_spent: float = 0.0


class BudgetCheckResponse(BaseModel):
    """Result of budget check."""

    allowed: bool
    warning: str | None = None


# ============================================================================
# Provider Endpoints
# ============================================================================


@router.get("/providers", response_model=list[ProviderInfoResponse])
async def list_providers() -> list[ProviderInfoResponse]:
    """List all registered GPU providers."""
    registry = get_provider_registry()
    providers = []

    for provider_id in registry.list_providers_by_priority():
        info = registry.get_provider_info(provider_id)
        if info:
            providers.append(
                ProviderInfoResponse(
                    id=info["id"],
                    name=info["name"],
                    priority=info["priority"],
                    capabilities=info["capabilities"],
                    supported_gpu_types=info["supported_gpu_types"],
                    regions=info["regions"],
                )
            )

    return providers


@router.get("/providers/{provider_id}", response_model=ProviderInfoResponse)
async def get_provider(provider_id: str) -> ProviderInfoResponse:
    """Get information about a specific provider."""
    registry = get_provider_registry()
    info = registry.get_provider_info(provider_id)

    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found",
        )

    return ProviderInfoResponse(
        id=info["id"],
        name=info["name"],
        priority=info["priority"],
        capabilities=info["capabilities"],
        supported_gpu_types=info["supported_gpu_types"],
        regions=info["regions"],
    )


@router.get("/providers/{provider_id}/health", response_model=ProviderHealthResponse)
async def get_provider_health(provider_id: str) -> ProviderHealthResponse:
    """Get health status of a specific provider."""
    registry = get_provider_registry()
    provider = registry.get_provider(provider_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found",
        )

    health = await provider.check_health()

    return ProviderHealthResponse(
        provider_id=provider_id,
        available=health.available,
        message=health.message,
        latency_ms=health.latency_ms,
        instances_available=health.instances_available,
        queue_depth=health.queue_depth,
        error_code=health.error_code,
        last_check=health.last_check,
    )


@router.get("/providers/health/all", response_model=AllProvidersHealthResponse)
async def get_all_providers_health() -> AllProvidersHealthResponse:
    """Get health status of all registered providers."""
    registry = get_provider_registry()
    all_health = await registry.get_all_health()

    providers_response = {}
    healthy_count = 0

    for provider_id, health in all_health.items():
        if health.available:
            healthy_count += 1

        providers_response[provider_id] = ProviderHealthResponse(
            provider_id=provider_id,
            available=health.available,
            message=health.message,
            latency_ms=health.latency_ms,
            instances_available=health.instances_available,
            queue_depth=health.queue_depth,
            error_code=health.error_code,
            last_check=health.last_check,
        )

    return AllProvidersHealthResponse(
        providers=providers_response,
        healthy_count=healthy_count,
        total_count=len(all_health),
    )


@router.get("/providers/gpu/{gpu_type}", response_model=list[str])
async def get_providers_for_gpu(gpu_type: str) -> list[str]:
    """Get providers that support a specific GPU type."""
    try:
        gpu = GPUType(gpu_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GPU type: {gpu_type}",
        )

    registry = get_provider_registry()
    return registry.get_providers_for_gpu(gpu)


# ============================================================================
# Pricing Endpoints
# ============================================================================


@router.get("/pricing/{provider_id}/{gpu_type}", response_model=GPUPricingResponse)
async def get_pricing(
    provider_id: str,
    gpu_type: str,
    region: str = Query(default="us-east-1", description="Region for pricing"),
) -> GPUPricingResponse:
    """Get current pricing for a GPU type from a provider."""
    try:
        gpu = GPUType(gpu_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GPU type: {gpu_type}",
        )

    pricing_service = get_pricing_service()
    pricing = await pricing_service.get_pricing(provider_id, gpu, region)

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing not available for {provider_id}/{gpu_type}",
        )

    return GPUPricingResponse(
        gpu_type=gpu_type,
        price_per_hour=pricing.price_per_hour,
        price_per_second=pricing.price_per_second,
        spot_price_per_hour=pricing.spot_price_per_hour,
        reserved_price_per_hour=pricing.reserved_price_per_hour,
        currency=pricing.currency,
        region=pricing.region,
        availability=pricing.availability,
        last_updated=pricing.last_updated,
    )


@router.get("/pricing/compare/{gpu_type}", response_model=PricingComparisonResponse)
async def compare_pricing(
    gpu_type: str,
    region: str = Query(default="us-east-1", description="Region for pricing"),
) -> PricingComparisonResponse:
    """Compare pricing across all providers for a GPU type."""
    try:
        gpu = GPUType(gpu_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GPU type: {gpu_type}",
        )

    pricing_service = get_pricing_service()
    comparison = await pricing_service.compare_pricing(gpu, region)

    return PricingComparisonResponse(
        gpu_type=gpu_type,
        region=comparison.region,
        cheapest_provider=comparison.cheapest_provider,
        cheapest_price=comparison.cheapest_price,
        fastest_provider=comparison.fastest_provider,
        best_value_provider=comparison.best_value_provider,
        all_options=comparison.all_options,
        generated_at=comparison.generated_at,
    )


@router.get("/pricing/all/{gpu_type}", response_model=dict[str, GPUPricingResponse])
async def get_all_pricing(
    gpu_type: str,
    region: str = Query(default="us-east-1", description="Region for pricing"),
) -> dict[str, GPUPricingResponse]:
    """Get pricing from all providers for a GPU type."""
    try:
        gpu = GPUType(gpu_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GPU type: {gpu_type}",
        )

    pricing_service = get_pricing_service()
    all_pricing = await pricing_service.get_all_pricing(gpu, region)

    result = {}
    for provider_id, pricing in all_pricing.items():
        result[provider_id] = GPUPricingResponse(
            gpu_type=gpu_type,
            price_per_hour=pricing.price_per_hour,
            price_per_second=pricing.price_per_second,
            spot_price_per_hour=pricing.spot_price_per_hour,
            reserved_price_per_hour=pricing.reserved_price_per_hour,
            currency=pricing.currency,
            region=pricing.region,
            availability=pricing.availability,
            last_updated=pricing.last_updated,
        )

    return result


@router.post("/pricing/estimate", response_model=CostEstimateResponse)
async def estimate_cost(request: CostEstimateRequest) -> CostEstimateResponse:
    """Estimate cost for a job."""
    try:
        gpu = GPUType(request.gpu_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GPU type: {request.gpu_type}",
        )

    pricing_service = get_pricing_service()

    if request.provider_id:
        # Specific provider
        pricing = await pricing_service.get_pricing(request.provider_id, gpu)
        if not pricing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pricing not available for {request.provider_id}",
            )

        if request.use_spot and pricing.spot_price_per_hour:
            price_per_hour = pricing.spot_price_per_hour
        else:
            price_per_hour = pricing.price_per_hour

        estimated_cost = (price_per_hour / 3600) * request.duration_seconds

        return CostEstimateResponse(
            provider_id=request.provider_id,
            gpu_type=request.gpu_type,
            duration_seconds=request.duration_seconds,
            use_spot=request.use_spot,
            estimated_cost_usd=round(estimated_cost, 4),
            price_per_hour=price_per_hour,
        )

    else:
        # Find optimal provider
        tier = PricingTier.BUDGET if request.use_spot else PricingTier.STANDARD
        result = await pricing_service.get_optimal_provider(
            gpu, request.duration_seconds, tier=tier
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No providers available for {request.gpu_type}",
            )

        provider_id, pricing = result

        if request.use_spot and pricing.spot_price_per_hour:
            price_per_hour = pricing.spot_price_per_hour
        else:
            price_per_hour = pricing.price_per_hour

        estimated_cost = (price_per_hour / 3600) * request.duration_seconds

        return CostEstimateResponse(
            provider_id=provider_id,
            gpu_type=request.gpu_type,
            duration_seconds=request.duration_seconds,
            use_spot=request.use_spot and pricing.spot_price_per_hour is not None,
            estimated_cost_usd=round(estimated_cost, 4),
            price_per_hour=price_per_hour,
        )


# ============================================================================
# Routing Endpoints
# ============================================================================


@router.post("/routing/select", response_model=ProviderSelectionResponse)
async def select_provider(request: SelectProviderRequest) -> ProviderSelectionResponse:
    """Select optimal provider for a job using the routing algorithm."""
    try:
        gpu = GPUType(request.gpu_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GPU type: {request.gpu_type}",
        )

    try:
        capability = ProviderCapability(request.required_capability)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid capability: {request.required_capability}",
        )

    # Build routing config
    config = RoutingConfig()
    if request.config:
        try:
            config.priority = RoutingPriority(request.config.priority)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.config.priority}",
            )

        config.max_price_usd = request.config.max_price_usd
        config.preferred_providers = request.config.preferred_providers
        config.excluded_providers = request.config.excluded_providers
        config.preferred_regions = request.config.preferred_regions
        config.allow_spot = request.config.allow_spot

    # Select provider
    exchange = get_gpu_exchange()
    selection = await exchange.select_provider(gpu, request.duration_seconds, config, capability)

    if not selection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No suitable provider found for the requested configuration",
        )

    return ProviderSelectionResponse(
        provider_id=selection.provider_id,
        provider_name=selection.provider.name,
        price_per_hour=selection.pricing.price_per_hour,
        estimated_cost=round(selection.estimated_cost, 4),
        use_spot=selection.use_spot,
        fallback_providers=selection.fallback_providers,
        score_breakdown={
            "total": selection.score.total_score,
            "cost": selection.score.cost_score,
            "latency": selection.score.latency_score,
            "reliability": selection.score.reliability_score,
            "queue": selection.score.queue_score,
        },
    )


@router.get("/routing/stats", response_model=RoutingStatsResponse)
async def get_routing_stats() -> RoutingStatsResponse:
    """Get routing statistics and circuit breaker status."""
    exchange = get_gpu_exchange()
    stats = exchange.get_routing_stats()

    return RoutingStatsResponse(
        total_routings=stats["total_routings"],
        successful=stats["successful"],
        success_rate=stats["success_rate"],
        failovers_used=stats["failovers_used"],
        by_provider=stats["by_provider"],
        circuit_breakers=stats["circuit_breakers"],
        reliability_scores=stats["reliability_scores"],
    )


# ============================================================================
# Budget Endpoints
# ============================================================================


@router.post("/budget/limit", status_code=status.HTTP_200_OK)
async def set_budget_limit(request: BudgetLimitRequest) -> dict[str, Any]:
    """Set a budget limit for a project."""
    pricing_service = get_pricing_service()
    pricing_service.set_budget_limit(request.project_id, request.limit_usd)

    return {
        "status": "success",
        "project_id": request.project_id,
        "limit_usd": request.limit_usd,
    }


@router.post("/budget/check", response_model=BudgetCheckResponse)
async def check_budget(request: BudgetCheckRequest) -> BudgetCheckResponse:
    """Check if a job would exceed budget."""
    pricing_service = get_pricing_service()
    allowed, warning = pricing_service.check_budget(
        request.project_id, request.estimated_cost, request.current_spent
    )

    return BudgetCheckResponse(allowed=allowed, warning=warning)


# ============================================================================
# GPU Types Endpoint
# ============================================================================


@router.get("/gpu-types", response_model=list[dict[str, str]])
async def list_gpu_types() -> list[dict[str, str]]:
    """List all supported GPU types."""
    return [{"id": gpu.value, "name": gpu.name.replace("_", " ")} for gpu in GPUType]


@router.get("/capabilities", response_model=list[dict[str, str]])
async def list_capabilities() -> list[dict[str, str]]:
    """List all provider capabilities."""
    return [
        {"id": cap.value, "name": cap.name.replace("_", " ").title()} for cap in ProviderCapability
    ]


@router.get("/pricing-tiers", response_model=list[dict[str, str]])
async def list_pricing_tiers() -> list[dict[str, str]]:
    """List all pricing tiers."""
    return [
        {
            "id": tier.value,
            "name": tier.name.title(),
            "description": {
                "budget": "Cheapest available, may use spot instances",
                "standard": "Balanced price and reliability",
                "premium": "Fastest, most reliable",
                "reserved": "Reserved capacity discount",
            }.get(tier.value, ""),
        }
        for tier in PricingTier
    ]
