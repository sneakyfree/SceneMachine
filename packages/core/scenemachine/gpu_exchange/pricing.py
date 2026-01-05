"""GPU Pricing Service for cost optimization.

Tracks pricing across providers, identifies optimal options,
and provides cost estimation for job planning.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from scenemachine.gpu_exchange.base import GPUPricing, GPUType
from scenemachine.gpu_exchange.registry import get_provider_registry

logger = logging.getLogger(__name__)


class PricingTier(str, Enum):
    """Pricing tier for cost optimization."""

    BUDGET = "budget"  # Cheapest available (may use spot)
    STANDARD = "standard"  # Reliable, standard pricing
    PREMIUM = "premium"  # Fastest, most reliable
    RESERVED = "reserved"  # Reserved capacity discount


@dataclass
class PricingRecord:
    """Historical pricing record for analytics."""

    provider_id: str
    gpu_type: GPUType
    price_per_hour: float
    spot_price: Optional[float]
    availability: int
    region: str
    recorded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PricingComparison:
    """Comparison of pricing across providers."""

    gpu_type: GPUType
    region: str
    cheapest_provider: str
    cheapest_price: float
    fastest_provider: str
    best_value_provider: str
    all_options: List[Dict[str, Any]]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class PricingService:
    """Service for tracking and optimizing GPU pricing.

    Features:
    - Real-time pricing from all providers
    - Historical price tracking
    - Cost optimization recommendations
    - Budget alerts and limits
    """

    _instance: Optional["PricingService"] = None

    # Cache duration for pricing data
    CACHE_DURATION = timedelta(minutes=5)

    def __init__(self) -> None:
        self._pricing_cache: Dict[Tuple[str, GPUType, str], GPUPricing] = {}
        self._cache_timestamps: Dict[Tuple[str, GPUType, str], datetime] = {}
        self._price_history: List[PricingRecord] = []
        self._budget_limits: Dict[str, float] = {}  # project_id -> limit_usd

    @classmethod
    def get_instance(cls) -> "PricingService":
        """Get singleton pricing service instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _cache_key(
        self, provider_id: str, gpu_type: GPUType, region: str
    ) -> Tuple[str, GPUType, str]:
        """Generate cache key for pricing data."""
        return (provider_id, gpu_type, region)

    def _is_cache_valid(self, key: Tuple[str, GPUType, str]) -> bool:
        """Check if cached pricing is still valid."""
        if key not in self._cache_timestamps:
            return False
        age = datetime.utcnow() - self._cache_timestamps[key]
        return age < self.CACHE_DURATION

    async def get_pricing(
        self,
        provider_id: str,
        gpu_type: GPUType,
        region: str = "us-east-1",
        force_refresh: bool = False,
    ) -> Optional[GPUPricing]:
        """Get current pricing for a GPU type from a provider.

        Args:
            provider_id: The provider to query
            gpu_type: The GPU type to price
            region: Region for pricing
            force_refresh: Force refresh from provider

        Returns:
            GPUPricing or None if unavailable
        """
        cache_key = self._cache_key(provider_id, gpu_type, region)

        # Check cache first
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._pricing_cache.get(cache_key)

        # Fetch from provider
        registry = get_provider_registry()
        provider = registry.get_provider(provider_id)

        if not provider:
            return None

        try:
            pricing = await provider.get_current_pricing(gpu_type, region)
            if pricing:
                self._pricing_cache[cache_key] = pricing
                self._cache_timestamps[cache_key] = datetime.utcnow()

                # Record for history
                self._price_history.append(
                    PricingRecord(
                        provider_id=provider_id,
                        gpu_type=gpu_type,
                        price_per_hour=pricing.price_per_hour,
                        spot_price=pricing.spot_price_per_hour,
                        availability=pricing.availability,
                        region=region,
                    )
                )

            return pricing
        except Exception as e:
            logger.error(f"Failed to get pricing from {provider_id}: {e}")
            return None

    async def get_all_pricing(
        self,
        gpu_type: GPUType,
        region: str = "us-east-1",
    ) -> Dict[str, GPUPricing]:
        """Get pricing from all providers for a GPU type.

        Args:
            gpu_type: The GPU type to price
            region: Region for pricing

        Returns:
            Dict mapping provider_id to GPUPricing
        """
        registry = get_provider_registry()
        providers = registry.list_providers()

        pricing_dict = {}
        tasks = []

        for provider_id in providers:
            tasks.append(self.get_pricing(provider_id, gpu_type, region))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for provider_id, result in zip(providers, results):
            if isinstance(result, GPUPricing):
                pricing_dict[provider_id] = result

        return pricing_dict

    async def compare_pricing(
        self,
        gpu_type: GPUType,
        region: str = "us-east-1",
    ) -> PricingComparison:
        """Compare pricing across all providers.

        Args:
            gpu_type: The GPU type to compare
            region: Region for pricing

        Returns:
            PricingComparison with analysis
        """
        all_pricing = await self.get_all_pricing(gpu_type, region)

        if not all_pricing:
            return PricingComparison(
                gpu_type=gpu_type,
                region=region,
                cheapest_provider="none",
                cheapest_price=0,
                fastest_provider="none",
                best_value_provider="none",
                all_options=[],
            )

        # Find cheapest
        cheapest_provider = min(all_pricing.keys(), key=lambda p: all_pricing[p].price_per_hour)
        cheapest_price = all_pricing[cheapest_provider].price_per_hour

        # Find fastest (most availability = likely fastest spin-up)
        fastest_provider = max(all_pricing.keys(), key=lambda p: all_pricing[p].availability)

        # Best value = cheapest with good availability
        def value_score(provider_id: str) -> float:
            pricing = all_pricing[provider_id]
            # Normalize price (lower = better, so invert)
            price_score = 1.0 / (pricing.price_per_hour + 0.01)
            # Availability score (higher = better)
            avail_score = min(pricing.availability / 10.0, 1.0)
            return price_score * 0.6 + avail_score * 0.4

        best_value_provider = max(all_pricing.keys(), key=value_score)

        # Build all options list
        all_options = [
            {
                "provider": provider_id,
                "price_per_hour": pricing.price_per_hour,
                "spot_price": pricing.spot_price_per_hour,
                "availability": pricing.availability,
                "value_score": value_score(provider_id),
            }
            for provider_id, pricing in all_pricing.items()
        ]

        # Sort by price
        all_options.sort(key=lambda x: x["price_per_hour"])

        return PricingComparison(
            gpu_type=gpu_type,
            region=region,
            cheapest_provider=cheapest_provider,
            cheapest_price=cheapest_price,
            fastest_provider=fastest_provider,
            best_value_provider=best_value_provider,
            all_options=all_options,
        )

    async def get_optimal_provider(
        self,
        gpu_type: GPUType,
        duration_seconds: float,
        max_price_usd: Optional[float] = None,
        tier: PricingTier = PricingTier.STANDARD,
        region: Optional[str] = None,
    ) -> Optional[Tuple[str, GPUPricing]]:
        """Get the optimal provider for a job.

        Args:
            gpu_type: Required GPU type
            duration_seconds: Estimated job duration
            max_price_usd: Maximum budget for this job
            tier: Pricing tier preference
            region: Preferred region

        Returns:
            Tuple of (provider_id, pricing) or None
        """
        region = region or "us-east-1"
        all_pricing = await self.get_all_pricing(gpu_type, region)

        if not all_pricing:
            return None

        # Filter by budget
        if max_price_usd is not None:
            all_pricing = {
                p: pricing
                for p, pricing in all_pricing.items()
                if (pricing.price_per_hour / 3600) * duration_seconds <= max_price_usd
            }

        if not all_pricing:
            return None

        # Select based on tier
        if tier == PricingTier.BUDGET:
            # Use spot if available, otherwise cheapest
            for provider_id, pricing in sorted(
                all_pricing.items(),
                key=lambda x: x[1].spot_price_per_hour or x[1].price_per_hour,
            ):
                if pricing.spot_price_per_hour:
                    return (provider_id, pricing)
            # Fall back to cheapest on-demand
            provider_id = min(all_pricing.keys(), key=lambda p: all_pricing[p].price_per_hour)
            return (provider_id, all_pricing[provider_id])

        elif tier == PricingTier.PREMIUM:
            # Prioritize availability and low latency
            provider_id = max(all_pricing.keys(), key=lambda p: all_pricing[p].availability)
            return (provider_id, all_pricing[provider_id])

        else:  # STANDARD or RESERVED
            # Balance of price and availability
            comparison = await self.compare_pricing(gpu_type, region)
            best_provider = comparison.best_value_provider
            if best_provider in all_pricing:
                return (best_provider, all_pricing[best_provider])

            # Fallback
            provider_id = min(all_pricing.keys(), key=lambda p: all_pricing[p].price_per_hour)
            return (provider_id, all_pricing[provider_id])

    def estimate_cost(
        self,
        provider_id: str,
        gpu_type: GPUType,
        duration_seconds: float,
        use_spot: bool = False,
    ) -> Optional[float]:
        """Estimate cost for a job using cached pricing.

        Args:
            provider_id: The provider to use
            gpu_type: GPU type for the job
            duration_seconds: Estimated duration
            use_spot: Whether to use spot pricing

        Returns:
            Estimated cost in USD or None if pricing unavailable
        """
        cache_key = self._cache_key(provider_id, gpu_type, "us-east-1")
        pricing = self._pricing_cache.get(cache_key)

        if not pricing:
            return None

        if use_spot and pricing.spot_price_per_hour:
            hourly_rate = pricing.spot_price_per_hour
        else:
            hourly_rate = pricing.price_per_hour

        return (hourly_rate / 3600) * duration_seconds

    def set_budget_limit(self, project_id: str, limit_usd: float) -> None:
        """Set a budget limit for a project.

        Args:
            project_id: The project ID
            limit_usd: Maximum budget in USD
        """
        self._budget_limits[project_id] = limit_usd

    def check_budget(
        self,
        project_id: str,
        estimated_cost: float,
        current_spent: float,
    ) -> Tuple[bool, Optional[str]]:
        """Check if a job would exceed budget.

        Args:
            project_id: The project ID
            estimated_cost: Cost of this job
            current_spent: Amount already spent

        Returns:
            Tuple of (allowed, warning_message)
        """
        limit = self._budget_limits.get(project_id)

        if limit is None:
            return (True, None)

        new_total = current_spent + estimated_cost

        if new_total > limit:
            return (
                False,
                f"Job would exceed budget (${new_total:.2f} > ${limit:.2f} limit)",
            )

        if new_total > limit * 0.8:
            return (
                True,
                f"Warning: Approaching budget limit (${new_total:.2f} of ${limit:.2f})",
            )

        return (True, None)

    def get_price_history(
        self,
        provider_id: Optional[str] = None,
        gpu_type: Optional[GPUType] = None,
        hours: int = 24,
    ) -> List[PricingRecord]:
        """Get historical pricing data.

        Args:
            provider_id: Filter by provider
            gpu_type: Filter by GPU type
            hours: Number of hours of history

        Returns:
            List of PricingRecord objects
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        return [
            record
            for record in self._price_history
            if record.recorded_at >= cutoff
            and (provider_id is None or record.provider_id == provider_id)
            and (gpu_type is None or record.gpu_type == gpu_type)
        ]


def get_pricing_service() -> PricingService:
    """Get the global pricing service instance."""
    return PricingService.get_instance()
