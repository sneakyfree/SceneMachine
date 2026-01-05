"""Lambda Labs GPU provider implementation.

Lambda Labs offers cloud GPUs with simple pricing and
excellent availability for ML/AI workloads.
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


class LambdaLabsProvider(GPUExchangeProvider):
    """Lambda Labs cloud GPU provider.

    Features:
    - Simple per-hour pricing
    - Quick instance spin-up
    - Good availability for A100/H100
    - SSH access included

    Usage:
        provider = LambdaLabsProvider(api_key="lambda_key_...")
        instances = await provider.get_available_instances()
    """

    # GPU type mapping to Lambda Labs instance types
    INSTANCE_TYPES: Dict[GPUType, str] = {
        GPUType.A10: "gpu_1x_a10",
        GPUType.A100_40GB: "gpu_1x_a100",
        GPUType.A100_80GB: "gpu_1x_a100_80gb",
        GPUType.H100: "gpu_1x_h100_pcie",
    }

    # Pricing per hour (USD)
    HOURLY_PRICING: Dict[GPUType, float] = {
        GPUType.A10: 0.60,
        GPUType.A100_40GB: 1.29,
        GPUType.A100_80GB: 1.89,
        GPUType.H100: 2.49,
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize Lambda Labs provider.

        Args:
            api_key: Lambda Labs API key
        """
        self.api_key = api_key
        self._client = None

    @property
    def name(self) -> str:
        return "Lambda Labs"

    @property
    def provider_id(self) -> str:
        return "lambda_labs"

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.VIDEO_GENERATION,
            ProviderCapability.IMAGE_GENERATION,
            ProviderCapability.LLM_INFERENCE,
            ProviderCapability.TRAINING,
            ProviderCapability.DEDICATED,
        ]

    @property
    def supported_gpu_types(self) -> List[GPUType]:
        return list(self.INSTANCE_TYPES.keys())

    @property
    def regions(self) -> List[str]:
        return ["us-tx-1", "us-az-1", "us-ca-1", "eu-south-1"]

    async def get_available_instances(
        self,
        gpu_type: Optional[GPUType] = None,
        region: Optional[str] = None,
    ) -> List[GPUInstance]:
        """Get available Lambda Labs instances."""
        if not self.api_key:
            logger.warning("Lambda Labs API key not configured")
            return []

        try:
            # In production, this would call the Lambda Labs API
            # For now, return simulated availability
            instances = []

            for gtype, instance_type in self.INSTANCE_TYPES.items():
                if gpu_type and gtype != gpu_type:
                    continue

                # Simulate availability check
                for reg in self.regions:
                    if region and reg != region:
                        continue

                    # Get pricing
                    pricing = await self.get_current_pricing(gtype, reg)

                    instances.append(
                        GPUInstance(
                            id=f"lambda_{instance_type}_{reg}",
                            provider=self.provider_id,
                            gpu_type=gtype,
                            gpu_count=1,
                            vram_gb=self._get_vram(gtype),
                            cpu_cores=30,
                            ram_gb=200,
                            storage_gb=512,
                            region=reg,
                            is_available=True,
                            is_spot=False,
                            pricing=pricing,
                            capabilities=self.capabilities,
                        )
                    )

            return instances

        except Exception as e:
            logger.error(f"Failed to get Lambda Labs instances: {e}")
            return []

    def _get_vram(self, gpu_type: GPUType) -> int:
        """Get VRAM for GPU type."""
        vram_map = {
            GPUType.A10: 24,
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
        """Get current Lambda Labs pricing."""
        if gpu_type not in self.HOURLY_PRICING:
            return None

        hourly_rate = self.HOURLY_PRICING[gpu_type]

        return GPUPricing(
            gpu_type=gpu_type,
            price_per_hour=hourly_rate,
            price_per_second=hourly_rate / 3600,
            spot_price_per_hour=None,  # Lambda doesn't offer spot
            region=region or "us-tx-1",
            availability=5,  # Simulated
        )

    async def provision_instance(
        self,
        gpu_type: GPUType,
        max_price_per_hour: float,
        region: Optional[str] = None,
        spot: bool = False,
    ) -> ProvisionResult:
        """Provision a Lambda Labs instance."""
        if not self.api_key:
            return ProvisionResult(
                success=False,
                error_message="Lambda Labs API key not configured",
                error_code="MISSING_API_KEY",
            )

        if gpu_type not in self.INSTANCE_TYPES:
            return ProvisionResult(
                success=False,
                error_message=f"GPU type {gpu_type} not supported",
                error_code="UNSUPPORTED_GPU",
            )

        # Check price
        pricing = await self.get_current_pricing(gpu_type, region)
        if pricing and pricing.price_per_hour > max_price_per_hour:
            return ProvisionResult(
                success=False,
                error_message=f"Price ${pricing.price_per_hour}/hr exceeds max ${max_price_per_hour}/hr",
                error_code="PRICE_EXCEEDED",
            )

        try:
            # In production, this would call Lambda Labs API to launch instance
            # lambda_cloud.instances.create(...)

            # Simulate successful provision
            instance_id = f"i-lambda-{gpu_type.value}-{region or 'us-tx-1'}"

            return ProvisionResult(
                success=True,
                instance_id=instance_id,
                instance=GPUInstance(
                    id=instance_id,
                    provider=self.provider_id,
                    gpu_type=gpu_type,
                    gpu_count=1,
                    vram_gb=self._get_vram(gpu_type),
                    region=region or "us-tx-1",
                    is_available=True,
                    pricing=pricing,
                ),
                ssh_host=f"{instance_id}.cloud.lambdalabs.com",
                ssh_port=22,
                ssh_user="ubuntu",
                startup_time_seconds=45.0,
            )

        except Exception as e:
            logger.error(f"Failed to provision Lambda Labs instance: {e}")
            return ProvisionResult(
                success=False,
                error_message=str(e),
                error_code="PROVISION_FAILED",
            )

    async def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a Lambda Labs instance."""
        if not self.api_key:
            return False

        try:
            # In production: lambda_cloud.instances.terminate(instance_id)
            logger.info(f"Terminated Lambda Labs instance: {instance_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to terminate instance {instance_id}: {e}")
            return False

    async def check_health(self) -> ProviderHealth:
        """Check Lambda Labs API health."""
        if not self.api_key:
            return ProviderHealth(
                available=False,
                message="API key not configured",
                error_code="MISSING_API_KEY",
            )

        try:
            import time

            start = time.time()

            # In production, make a lightweight API call
            # await self._make_request("instance-types")
            await asyncio.sleep(0.1)  # Simulate API call

            latency = (time.time() - start) * 1000

            instances = await self.get_available_instances()
            available_count = sum(1 for i in instances if i.is_available)

            return ProviderHealth(
                available=True,
                message="Lambda Labs API is healthy",
                latency_ms=latency,
                instances_available=available_count,
            )

        except Exception as e:
            return ProviderHealth(
                available=False,
                message=str(e),
                error_code="HEALTH_CHECK_FAILED",
            )
