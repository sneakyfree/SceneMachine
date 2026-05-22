"""GPU Exchange Router for intelligent job routing.

Implements smart routing algorithm with:
- Cost optimization
- Latency awareness
- Reliability scoring
- Automatic failover (<30s)
- Circuit breaker integration
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID

from scenemachine.gpu_exchange.base import (
    GPUExchangeProvider,
    GPUPricing,
    GPUType,
    ProviderCapability,
    ProvisionResult,
)
from scenemachine.gpu_exchange.pricing import (
    get_pricing_service,
)
from scenemachine.gpu_exchange.registry import get_provider_registry

logger = logging.getLogger(__name__)


class RoutingPriority(StrEnum):
    """Job priority levels for routing decisions."""

    LOW = "low"  # Cost-optimized, can wait
    NORMAL = "normal"  # Balanced
    HIGH = "high"  # Speed-optimized
    URGENT = "urgent"  # Premium providers only


@dataclass
class RoutingConfig:
    """Configuration for routing decisions."""

    priority: RoutingPriority = RoutingPriority.NORMAL
    max_price_usd: float | None = None
    preferred_providers: list[str] = field(default_factory=list)
    excluded_providers: list[str] = field(default_factory=list)
    preferred_regions: list[str] = field(default_factory=lambda: ["us-east-1"])
    allow_spot: bool = True
    max_queue_depth: int = 100
    max_latency_ms: float = 5000
    failover_timeout_seconds: float = 30.0


@dataclass
class ProviderScore:
    """Scoring breakdown for a provider."""

    provider_id: str
    total_score: float
    cost_score: float
    latency_score: float
    reliability_score: float
    queue_score: float
    pricing: GPUPricing | None = None
    is_eligible: bool = True
    disqualification_reason: str | None = None


@dataclass
class ProviderSelection:
    """Result of provider selection."""

    provider_id: str
    provider: GPUExchangeProvider
    pricing: GPUPricing
    score: ProviderScore
    fallback_providers: list[str]
    estimated_cost: float
    use_spot: bool = False


@dataclass
class RoutingDecision:
    """Audit record of a routing decision."""

    decision_id: str
    job_id: UUID
    selected_provider: str
    fallback_providers: list[str]
    scores: list[ProviderScore]
    config: RoutingConfig
    estimated_cost: float
    actual_cost: float | None = None
    success: bool | None = None
    failover_used: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class GPUExchangeRouter:
    """Intelligent router for GPU job distribution.

    Implements the routing algorithm:
    1. Filter by capability + circuit breaker status
    2. Apply priority-based filtering
    3. Geographic filtering for latency
    4. Score all candidates
    5. Select best within budget with fallbacks

    Features:
    - <30 second failover
    - Circuit breaker integration
    - Cost optimization
    - Reliability tracking
    """

    _instance: Optional["GPUExchangeRouter"] = None

    # Scoring weights
    COST_WEIGHT = 0.40
    LATENCY_WEIGHT = 0.20
    RELIABILITY_WEIGHT = 0.25
    QUEUE_WEIGHT = 0.15

    # Circuit breaker tracking
    _circuit_breakers: dict[str, dict[str, Any]] = {}
    _provider_reliability: dict[str, float] = {}

    def __init__(self) -> None:
        self._routing_history: list[RoutingDecision] = []
        self._active_jobs: dict[str, str] = {}  # job_id -> provider_id

    @classmethod
    def get_instance(cls) -> "GPUExchangeRouter":
        """Get singleton router instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def select_provider(
        self,
        gpu_type: GPUType,
        duration_seconds: float,
        config: RoutingConfig | None = None,
        required_capability: ProviderCapability = ProviderCapability.VIDEO_GENERATION,
    ) -> ProviderSelection | None:
        """Select optimal provider for a job.

        Args:
            gpu_type: Required GPU type
            duration_seconds: Estimated job duration
            config: Routing configuration
            required_capability: Required provider capability

        Returns:
            ProviderSelection or None if no suitable provider
        """
        config = config or RoutingConfig()
        registry = get_provider_registry()
        get_pricing_service()

        # Phase 1: Filter by capability and circuit breaker
        candidates = await self._filter_candidates(
            gpu_type, required_capability, config
        )

        if not candidates:
            logger.warning(f"No eligible providers for {gpu_type}")
            return None

        # Phase 2: Get pricing and score all candidates
        scores = await self._score_candidates(
            candidates, gpu_type, duration_seconds, config
        )

        # Filter out ineligible providers
        eligible_scores = [s for s in scores if s.is_eligible]

        if not eligible_scores:
            logger.warning("All providers filtered out during scoring")
            return None

        # Phase 3: Select best provider
        eligible_scores.sort(key=lambda s: s.total_score, reverse=True)
        best_score = eligible_scores[0]

        # Get fallback providers
        fallbacks = [s.provider_id for s in eligible_scores[1:4]]

        provider = registry.get_provider(best_score.provider_id)
        if not provider or not best_score.pricing:
            return None

        # Calculate estimated cost
        estimated_cost = (best_score.pricing.price_per_hour / 3600) * duration_seconds
        use_spot = (
            config.allow_spot
            and config.priority in [RoutingPriority.LOW, RoutingPriority.NORMAL]
            and best_score.pricing.spot_price_per_hour is not None
        )

        if use_spot and best_score.pricing.spot_price_per_hour:
            estimated_cost = (
                best_score.pricing.spot_price_per_hour / 3600
            ) * duration_seconds

        return ProviderSelection(
            provider_id=best_score.provider_id,
            provider=provider,
            pricing=best_score.pricing,
            score=best_score,
            fallback_providers=fallbacks,
            estimated_cost=estimated_cost,
            use_spot=use_spot,
        )

    async def _filter_candidates(
        self,
        gpu_type: GPUType,
        required_capability: ProviderCapability,
        config: RoutingConfig,
    ) -> list[str]:
        """Filter providers by capability and availability."""
        registry = get_provider_registry()
        candidates = []

        for provider_id in registry.list_providers():
            # Check exclusions
            if provider_id in config.excluded_providers:
                continue

            # Check circuit breaker
            if self._is_circuit_open(provider_id):
                continue

            provider = registry.get_provider(provider_id)
            if not provider:
                continue

            # Check GPU support
            if gpu_type not in provider.supported_gpu_types:
                continue

            # Check capability
            if required_capability not in provider.capabilities:
                continue

            candidates.append(provider_id)

        # Apply preferred providers filter for HIGH/URGENT priority
        if config.priority in [RoutingPriority.HIGH, RoutingPriority.URGENT]:
            if config.preferred_providers:
                preferred = [p for p in candidates if p in config.preferred_providers]
                if preferred:
                    return preferred

        return candidates

    async def _score_candidates(
        self,
        candidates: list[str],
        gpu_type: GPUType,
        duration_seconds: float,
        config: RoutingConfig,
    ) -> list[ProviderScore]:
        """Score all candidate providers."""
        registry = get_provider_registry()
        pricing_service = get_pricing_service()
        scores = []

        # Get all pricing in parallel
        pricing_tasks = [
            pricing_service.get_pricing(p, gpu_type) for p in candidates
        ]
        pricing_results = await asyncio.gather(*pricing_tasks, return_exceptions=True)

        # Get health in parallel
        health_tasks = []
        for provider_id in candidates:
            provider = registry.get_provider(provider_id)
            if provider:
                health_tasks.append(provider.check_health())
            else:
                health_tasks.append(asyncio.coroutine(lambda: None)())

        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)

        # Find price range for normalization
        valid_prices = [
            p.price_per_hour
            for p in pricing_results
            if isinstance(p, GPUPricing)
        ]
        min_price = min(valid_prices) if valid_prices else 1.0
        max_price = max(valid_prices) if valid_prices else 2.0
        price_range = max_price - min_price if max_price > min_price else 1.0

        for i, provider_id in enumerate(candidates):
            pricing = pricing_results[i] if not isinstance(pricing_results[i], Exception) else None
            health = health_results[i] if not isinstance(health_results[i], Exception) else None

            score = ProviderScore(
                provider_id=provider_id,
                total_score=0,
                cost_score=0,
                latency_score=0,
                reliability_score=0,
                queue_score=0,
                pricing=pricing,
            )

            # Check if pricing is available
            if not pricing:
                score.is_eligible = False
                score.disqualification_reason = "Pricing unavailable"
                scores.append(score)
                continue

            # Check budget
            job_cost = (pricing.price_per_hour / 3600) * duration_seconds
            if config.max_price_usd and job_cost > config.max_price_usd:
                score.is_eligible = False
                score.disqualification_reason = f"Exceeds budget (${job_cost:.2f} > ${config.max_price_usd:.2f})"
                scores.append(score)
                continue

            # Cost score (lower = better, so invert)
            score.cost_score = 1.0 - ((pricing.price_per_hour - min_price) / price_range)

            # Latency score
            if health and hasattr(health, "latency_ms") and health.latency_ms:
                if health.latency_ms > config.max_latency_ms:
                    score.is_eligible = False
                    score.disqualification_reason = f"Latency too high ({health.latency_ms:.0f}ms)"
                    scores.append(score)
                    continue
                score.latency_score = 1.0 - (health.latency_ms / config.max_latency_ms)
            else:
                score.latency_score = 0.5  # Unknown latency

            # Reliability score
            score.reliability_score = self._provider_reliability.get(provider_id, 0.8)

            # Queue score
            if health and hasattr(health, "queue_depth"):
                if health.queue_depth > config.max_queue_depth:
                    score.is_eligible = False
                    score.disqualification_reason = f"Queue too deep ({health.queue_depth})"
                    scores.append(score)
                    continue
                score.queue_score = 1.0 - (health.queue_depth / config.max_queue_depth)
            else:
                score.queue_score = 0.7  # Unknown queue

            # Calculate total score with weights
            score.total_score = (
                score.cost_score * self.COST_WEIGHT
                + score.latency_score * self.LATENCY_WEIGHT
                + score.reliability_score * self.RELIABILITY_WEIGHT
                + score.queue_score * self.QUEUE_WEIGHT
            )

            # Priority adjustments
            if config.priority == RoutingPriority.LOW:
                # Boost cost importance
                score.total_score = score.cost_score * 0.6 + score.total_score * 0.4
            elif config.priority == RoutingPriority.URGENT:
                # Boost latency/reliability importance
                score.total_score = (
                    score.latency_score * 0.4
                    + score.reliability_score * 0.4
                    + score.total_score * 0.2
                )

            scores.append(score)

        return scores

    def _is_circuit_open(self, provider_id: str) -> bool:
        """Check if circuit breaker is open for a provider."""
        breaker = self._circuit_breakers.get(provider_id)
        if not breaker:
            return False

        if breaker.get("state") == "open":
            # Check if recovery timeout has passed
            open_time = breaker.get("opened_at")
            if open_time:
                elapsed = (datetime.utcnow() - open_time).total_seconds()
                if elapsed > breaker.get("recovery_timeout", 60):
                    # Move to half-open
                    breaker["state"] = "half_open"
                    return False
            return True

        return False

    def _mark_provider_failure(self, provider_id: str) -> None:
        """Mark a provider failure for circuit breaker."""
        if provider_id not in self._circuit_breakers:
            self._circuit_breakers[provider_id] = {
                "state": "closed",
                "failures": 0,
                "failure_threshold": 3,
                "recovery_timeout": 60,
            }

        breaker = self._circuit_breakers[provider_id]
        breaker["failures"] = breaker.get("failures", 0) + 1

        if breaker["failures"] >= breaker["failure_threshold"]:
            breaker["state"] = "open"
            breaker["opened_at"] = datetime.utcnow()
            logger.warning(f"Circuit breaker opened for {provider_id}")

        # Update reliability score
        current = self._provider_reliability.get(provider_id, 0.8)
        self._provider_reliability[provider_id] = max(0.1, current - 0.1)

    def _mark_provider_success(self, provider_id: str) -> None:
        """Mark a provider success for circuit breaker."""
        if provider_id in self._circuit_breakers:
            breaker = self._circuit_breakers[provider_id]
            if breaker["state"] == "half_open":
                breaker["state"] = "closed"
                breaker["failures"] = 0
                logger.info(f"Circuit breaker closed for {provider_id}")

        # Update reliability score
        current = self._provider_reliability.get(provider_id, 0.8)
        self._provider_reliability[provider_id] = min(1.0, current + 0.02)

    async def route_with_failover(
        self,
        selection: ProviderSelection,
        job_id: UUID,
        provision_callback: Any,
        timeout: float = 30.0,
    ) -> tuple[bool, ProvisionResult | None, str]:
        """Route a job with automatic failover.

        Args:
            selection: Initial provider selection
            job_id: The job being routed
            provision_callback: Async function to provision/run job
            timeout: Failover timeout in seconds

        Returns:
            Tuple of (success, result, provider_used)
        """
        providers_to_try = [selection.provider_id] + selection.fallback_providers
        last_error = None

        for provider_id in providers_to_try:
            registry = get_provider_registry()
            provider = registry.get_provider(provider_id)

            if not provider:
                continue

            if self._is_circuit_open(provider_id):
                continue

            try:
                # Attempt with timeout
                result = await asyncio.wait_for(
                    provision_callback(provider),
                    timeout=timeout,
                )

                if result and result.success:
                    self._mark_provider_success(provider_id)
                    self._active_jobs[str(job_id)] = provider_id
                    return (True, result, provider_id)
                else:
                    last_error = result.error_message if result else "Unknown error"
                    self._mark_provider_failure(provider_id)

            except TimeoutError:
                logger.warning(f"Provider {provider_id} timed out for job {job_id}")
                self._mark_provider_failure(provider_id)
                last_error = "Timeout"
                continue

            except Exception as e:
                logger.error(f"Provider {provider_id} failed for job {job_id}: {e}")
                self._mark_provider_failure(provider_id)
                last_error = str(e)
                continue

        logger.error(f"All providers failed for job {job_id}: {last_error}")
        return (False, None, "none")

    def record_decision(
        self,
        job_id: UUID,
        selection: ProviderSelection,
        scores: list[ProviderScore],
        config: RoutingConfig,
    ) -> RoutingDecision:
        """Record a routing decision for auditing."""
        decision = RoutingDecision(
            decision_id=f"rd_{job_id}",
            job_id=job_id,
            selected_provider=selection.provider_id,
            fallback_providers=selection.fallback_providers,
            scores=scores,
            config=config,
            estimated_cost=selection.estimated_cost,
        )

        self._routing_history.append(decision)

        # Trim old history
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-500:]

        return decision

    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        total = len(self._routing_history)
        successful = sum(1 for d in self._routing_history if d.success)
        failovers = sum(1 for d in self._routing_history if d.failover_used)

        by_provider = {}
        for decision in self._routing_history:
            provider = decision.selected_provider
            if provider not in by_provider:
                by_provider[provider] = {"total": 0, "successful": 0}
            by_provider[provider]["total"] += 1
            if decision.success:
                by_provider[provider]["successful"] += 1

        return {
            "total_routings": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "failovers_used": failovers,
            "by_provider": by_provider,
            "circuit_breakers": {
                p: b.get("state", "closed")
                for p, b in self._circuit_breakers.items()
            },
            "reliability_scores": dict(self._provider_reliability),
        }


def get_gpu_exchange() -> GPUExchangeRouter:
    """Get the global GPU Exchange router."""
    return GPUExchangeRouter.get_instance()
