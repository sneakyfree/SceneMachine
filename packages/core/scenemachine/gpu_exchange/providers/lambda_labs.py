"""Lambda Labs GPU provider implementation.

Lambda Labs offers cloud GPUs with simple pricing and
excellent availability for ML/AI workloads.
"""

import logging
from typing import Any

import httpx

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
    INSTANCE_TYPES: dict[GPUType, str] = {
        GPUType.A10: "gpu_1x_a10",
        GPUType.A100_40GB: "gpu_1x_a100",
        GPUType.A100_80GB: "gpu_1x_a100_80gb",
        GPUType.H100: "gpu_1x_h100_pcie",
    }

    # Pricing per hour (USD)
    HOURLY_PRICING: dict[GPUType, float] = {
        GPUType.A10: 0.60,
        GPUType.A100_40GB: 1.29,
        GPUType.A100_80GB: 1.89,
        GPUType.H100: 2.49,
    }

    # Lambda Labs API base URL
    API_BASE = "https://cloud.lambdalabs.com/api/v1"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Lambda Labs provider.

        Args:
            api_key: Lambda Labs API key
        """
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        client = await self._get_client()
        response = await client.request(method, endpoint, **kwargs)
        response.raise_for_status()
        return response.json()

    @property
    def name(self) -> str:
        return "Lambda Labs"

    @property
    def provider_id(self) -> str:
        return "lambda_labs"

    @property
    def capabilities(self) -> list[ProviderCapability]:
        return [
            ProviderCapability.VIDEO_GENERATION,
            ProviderCapability.IMAGE_GENERATION,
            ProviderCapability.LLM_INFERENCE,
            ProviderCapability.TRAINING,
            ProviderCapability.DEDICATED,
        ]

    @property
    def supported_gpu_types(self) -> list[GPUType]:
        return list(self.INSTANCE_TYPES.keys())

    @property
    def regions(self) -> list[str]:
        return ["us-tx-1", "us-az-1", "us-ca-1", "eu-south-1"]

    async def get_available_instances(
        self,
        gpu_type: GPUType | None = None,
        region: str | None = None,
    ) -> list[GPUInstance]:
        """Get available Lambda Labs instances from the API."""
        if not self.api_key:
            logger.warning("Lambda Labs API key not configured")
            return []

        try:
            # Query instance types from Lambda Labs API
            data = await self._make_request("GET", "/instance-types")
            instance_types = data.get("data", {})

            instances = []

            for instance_name, info in instance_types.items():
                # Map Lambda instance type to our GPU type
                specs = info.get("instance_type", {}).get("specs", {})
                gpu_count = specs.get("gpus", 1)
                gpu_name = specs.get("gpu_description", "").lower()

                # Determine GPU type from specs
                gtype = self._map_gpu_type(gpu_name)
                if gtype is None:
                    continue

                if gpu_type and gtype != gpu_type:
                    continue

                # Check regions with availability
                regions_available = info.get("regions_with_capacity_available", [])
                for reg in regions_available:
                    reg_name = reg.get("name", "unknown")
                    if region and reg_name != region:
                        continue

                    pricing = await self.get_current_pricing(gtype, reg_name)

                    instances.append(
                        GPUInstance(
                            id=f"lambda_{instance_name}_{reg_name}",
                            provider=self.provider_id,
                            gpu_type=gtype,
                            gpu_count=gpu_count,
                            vram_gb=specs.get("memory_gib", self._get_vram(gtype)),
                            cpu_cores=specs.get("vcpus", 30),
                            ram_gb=specs.get("ram_gib", 200),
                            storage_gb=specs.get("storage_gib", 512),
                            region=reg_name,
                            is_available=True,
                            is_spot=False,
                            pricing=pricing,
                            capabilities=self.capabilities,
                        )
                    )

            return instances

        except httpx.HTTPStatusError as e:
            logger.error(f"Lambda Labs API error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Failed to get Lambda Labs instances: {e}")
            return []

    def _map_gpu_type(self, gpu_description: str) -> GPUType | None:
        """Map GPU description to our GPUType enum."""
        desc_lower = gpu_description.lower()
        if "h100" in desc_lower:
            return GPUType.H100
        elif "a100" in desc_lower and "80" in desc_lower:
            return GPUType.A100_80GB
        elif "a100" in desc_lower:
            return GPUType.A100_40GB
        elif "a10" in desc_lower:
            return GPUType.A10
        return None

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
        region: str | None = None,
    ) -> GPUPricing | None:
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
        region: str | None = None,
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
            # Get the Lambda Labs instance type name
            instance_type = self.INSTANCE_TYPES.get(gpu_type)
            if not instance_type:
                return ProvisionResult(
                    success=False,
                    error_message=f"No instance type mapping for {gpu_type}",
                    error_code="UNSUPPORTED_GPU",
                )

            # Launch instance via Lambda Labs API
            launch_data = {
                "region_name": region or "us-tx-1",
                "instance_type_name": instance_type,
                "ssh_key_names": [],  # Would be configured per-user
                "quantity": 1,
            }

            response = await self._make_request(
                "POST", "/instance-operations/launch", json=launch_data
            )
            instance_ids = response.get("data", {}).get("instance_ids", [])

            if not instance_ids:
                return ProvisionResult(
                    success=False,
                    error_message="No instance launched",
                    error_code="LAUNCH_FAILED",
                )

            instance_id = instance_ids[0]

            # Get instance details
            details = await self._make_request("GET", f"/instances/{instance_id}")
            instance_data = details.get("data", {})

            return ProvisionResult(
                success=True,
                instance_id=instance_id,
                instance=GPUInstance(
                    id=instance_id,
                    provider=self.provider_id,
                    gpu_type=gpu_type,
                    gpu_count=1,
                    vram_gb=self._get_vram(gpu_type),
                    region=instance_data.get("region", {}).get("name", region or "us-tx-1"),
                    is_available=True,
                    pricing=pricing,
                ),
                ssh_host=instance_data.get("ip", f"{instance_id}.cloud.lambdalabs.com"),
                ssh_port=22,
                ssh_user="ubuntu",
                startup_time_seconds=45.0,
            )

        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            error_msg = error_data.get("error", {}).get("message", str(e))
            logger.error(f"Lambda Labs API error during provision: {error_msg}")
            return ProvisionResult(
                success=False,
                error_message=error_msg,
                error_code="API_ERROR",
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
            # Call Lambda Labs API to terminate instance
            await self._make_request(
                "POST",
                "/instance-operations/terminate",
                json={"instance_ids": [instance_id]},
            )
            logger.info(f"Terminated Lambda Labs instance: {instance_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"API error terminating instance {instance_id}: {e.response.status_code}")
            return False
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

            # Make a lightweight API call to check health
            await self._make_request("GET", "/instance-types")

            latency = (time.time() - start) * 1000

            instances = await self.get_available_instances()
            available_count = sum(1 for i in instances if i.is_available)

            return ProviderHealth(
                available=True,
                message="Lambda Labs API is healthy",
                latency_ms=latency,
                instances_available=available_count,
            )

        except httpx.HTTPStatusError as e:
            return ProviderHealth(
                available=False,
                message=f"API error: {e.response.status_code}",
                error_code="API_ERROR",
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                message=str(e),
                error_code="HEALTH_CHECK_FAILED",
            )
