"""Vast.ai GPU provider implementation.

Vast.ai offers a GPU marketplace with competitive spot pricing
from individual hosts and data centers.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from scenemachine.gpu_exchange.base import (
    GPUExchangeProvider,
    GPUInstance,
    GPUPricing,
    GPUType,
    ProviderCapability,
    ProviderHealth,
    ProvisionResult,
)

logger = logging.getLogger(__name__)


class VastAIProvider(GPUExchangeProvider):
    """Vast.ai GPU marketplace provider.

    Features:
    - Marketplace pricing (often cheapest)
    - Wide GPU variety including consumer cards
    - Spot/interruptible instances
    - Docker-based environments

    Usage:
        provider = VastAIProvider(api_key="vast_key_...")
        instances = await provider.get_available_instances()
    """

    # Typical Vast.ai pricing ranges (USD/hr)
    # Prices vary by host - these are typical ranges
    TYPICAL_PRICING: Dict[GPUType, tuple] = {
        GPUType.RTX_3090: (0.20, 0.40),
        GPUType.RTX_4090: (0.35, 0.60),
        GPUType.A10: (0.35, 0.55),
        GPUType.A40: (0.50, 0.80),
        GPUType.A100_40GB: (0.80, 1.30),
        GPUType.A100_80GB: (1.20, 1.80),
        GPUType.H100: (2.00, 3.00),
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize Vast.ai provider.

        Args:
            api_key: Vast.ai API key
        """
        self.api_key = api_key
        self._cached_offers: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "Vast.ai"

    @property
    def provider_id(self) -> str:
        return "vast_ai"

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.VIDEO_GENERATION,
            ProviderCapability.IMAGE_GENERATION,
            ProviderCapability.LLM_INFERENCE,
            ProviderCapability.TRAINING,
            ProviderCapability.SPOT_INSTANCES,
            ProviderCapability.DEDICATED,
        ]

    @property
    def supported_gpu_types(self) -> List[GPUType]:
        return list(self.TYPICAL_PRICING.keys())

    @property
    def regions(self) -> List[str]:
        # Vast.ai has hosts globally
        return ["us", "eu", "asia", "global"]

    async def get_available_instances(
        self,
        gpu_type: Optional[GPUType] = None,
        region: Optional[str] = None,
    ) -> List[GPUInstance]:
        """Get available Vast.ai instances."""
        if not self.api_key:
            logger.warning("Vast.ai API key not configured")
            return []

        try:
            # In production, this would call the Vast.ai API
            # offers = await self._search_offers(gpu_type, region)

            instances = []

            for gtype, (min_price, max_price) in self.TYPICAL_PRICING.items():
                if gpu_type and gtype != gpu_type:
                    continue

                # Simulate multiple offers per GPU type
                for i, price in enumerate([min_price, (min_price + max_price) / 2, max_price]):
                    offer_id = f"vast_{gtype.value}_{i}"

                    pricing = GPUPricing(
                        gpu_type=gtype,
                        price_per_hour=price,
                        price_per_second=price / 3600,
                        spot_price_per_hour=price * 0.7,  # 30% cheaper spot
                        region=region or "us",
                        availability=3 - i,  # Cheaper = more available (simulated)
                    )

                    instances.append(
                        GPUInstance(
                            id=offer_id,
                            provider=self.provider_id,
                            gpu_type=gtype,
                            gpu_count=1,
                            vram_gb=self._get_vram(gtype),
                            cpu_cores=16,
                            ram_gb=64,
                            storage_gb=100,
                            region=region or "us",
                            is_available=True,
                            is_spot=True,
                            pricing=pricing,
                            capabilities=self.capabilities,
                            metadata={
                                "reliability_score": 0.95 - (i * 0.05),
                                "host_id": f"host_{offer_id}",
                            },
                        )
                    )

            return instances

        except Exception as e:
            logger.error(f"Failed to get Vast.ai instances: {e}")
            return []

    def _get_vram(self, gpu_type: GPUType) -> int:
        """Get VRAM for GPU type."""
        vram_map = {
            GPUType.RTX_3090: 24,
            GPUType.RTX_4090: 24,
            GPUType.A10: 24,
            GPUType.A40: 48,
            GPUType.A100_40GB: 40,
            GPUType.A100_80GB: 80,
            GPUType.H100: 80,
        }
        return vram_map.get(gpu_type, 24)

    async def get_current_pricing(
        self,
        gpu_type: GPUType,
        region: Optional[str] = None,
    ) -> Optional[GPUPricing]:
        """Get current Vast.ai pricing (cheapest available)."""
        if gpu_type not in self.TYPICAL_PRICING:
            return None

        min_price, max_price = self.TYPICAL_PRICING[gpu_type]

        # Return the median price as "current"
        median_price = (min_price + max_price) / 2

        return GPUPricing(
            gpu_type=gpu_type,
            price_per_hour=median_price,
            price_per_second=median_price / 3600,
            spot_price_per_hour=median_price * 0.7,
            region=region or "us",
            availability=10,  # Vast typically has good availability
        )

    async def provision_instance(
        self,
        gpu_type: GPUType,
        max_price_per_hour: float,
        region: Optional[str] = None,
        spot: bool = False,
    ) -> ProvisionResult:
        """Provision a Vast.ai instance."""
        if not self.api_key:
            return ProvisionResult(
                success=False,
                error_message="Vast.ai API key not configured",
                error_code="MISSING_API_KEY",
            )

        if gpu_type not in self.TYPICAL_PRICING:
            return ProvisionResult(
                success=False,
                error_message=f"GPU type {gpu_type} not supported",
                error_code="UNSUPPORTED_GPU",
            )

        min_price, _ = self.TYPICAL_PRICING[gpu_type]

        # Use spot price if requested
        effective_price = min_price * 0.7 if spot else min_price

        if effective_price > max_price_per_hour:
            return ProvisionResult(
                success=False,
                error_message=f"No offers within ${max_price_per_hour}/hr budget",
                error_code="PRICE_EXCEEDED",
            )

        try:
            # In production, this would:
            # 1. Search for matching offers
            # 2. Create instance with Docker template
            # vast.create_instance(offer_id=best_offer, image="scenemachine/worker:latest")

            instance_id = f"i-vast-{gpu_type.value}-{region or 'us'}"

            return ProvisionResult(
                success=True,
                instance_id=instance_id,
                instance=GPUInstance(
                    id=instance_id,
                    provider=self.provider_id,
                    gpu_type=gpu_type,
                    gpu_count=1,
                    vram_gb=self._get_vram(gpu_type),
                    region=region or "us",
                    is_available=True,
                    is_spot=spot,
                ),
                ssh_host=f"{instance_id}.vast.ai",
                ssh_port=22,
                ssh_user="root",
                api_endpoint=f"http://{instance_id}.vast.ai:8080",
                startup_time_seconds=60.0,  # Vast can be slower to start
            )

        except Exception as e:
            logger.error(f"Failed to provision Vast.ai instance: {e}")
            return ProvisionResult(
                success=False,
                error_message=str(e),
                error_code="PROVISION_FAILED",
            )

    async def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a Vast.ai instance."""
        if not self.api_key:
            return False

        try:
            # In production: vast.destroy_instance(instance_id)
            logger.info(f"Terminated Vast.ai instance: {instance_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to terminate instance {instance_id}: {e}")
            return False

    async def get_queue_depth(self) -> int:
        """Vast.ai doesn't have a queue - it's on-demand."""
        return 0

    async def check_health(self) -> ProviderHealth:
        """Check Vast.ai API health."""
        if not self.api_key:
            return ProviderHealth(
                available=False,
                message="API key not configured",
                error_code="MISSING_API_KEY",
            )

        try:
            import time

            start = time.time()

            # In production: await vast.get_user()
            await asyncio.sleep(0.15)  # Simulate API call

            latency = (time.time() - start) * 1000

            instances = await self.get_available_instances()
            available_count = len(instances)

            return ProviderHealth(
                available=True,
                message="Vast.ai marketplace is available",
                latency_ms=latency,
                instances_available=available_count,
            )

        except Exception as e:
            return ProviderHealth(
                available=False,
                message=str(e),
                error_code="HEALTH_CHECK_FAILED",
            )
