"""Vast.ai GPU provider implementation.

Vast.ai offers a GPU marketplace with competitive spot pricing
from individual hosts and data centers.
"""

import contextlib
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
    TYPICAL_PRICING: dict[GPUType, tuple] = {
        GPUType.RTX_3090: (0.20, 0.40),
        GPUType.RTX_4090: (0.35, 0.60),
        GPUType.A10: (0.35, 0.55),
        GPUType.A40: (0.50, 0.80),
        GPUType.A100_40GB: (0.80, 1.30),
        GPUType.A100_80GB: (1.20, 1.80),
        GPUType.H100: (2.00, 3.00),
    }

    # Vast.ai API base URL
    API_BASE = "https://console.vast.ai/api/v0"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Vast.ai provider.

        Args:
            api_key: Vast.ai API key
        """
        self.api_key = api_key
        self._cached_offers: list[dict[str, Any]] = []
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={
                    "Accept": "application/json",
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
        # Vast.ai uses query param for API key
        params = kwargs.pop("params", {})
        params["api_key"] = self.api_key
        response = await client.request(method, endpoint, params=params, **kwargs)
        response.raise_for_status()
        return response.json()

    @property
    def name(self) -> str:
        return "Vast.ai"

    @property
    def provider_id(self) -> str:
        return "vast_ai"

    @property
    def capabilities(self) -> list[ProviderCapability]:
        return [
            ProviderCapability.VIDEO_GENERATION,
            ProviderCapability.IMAGE_GENERATION,
            ProviderCapability.LLM_INFERENCE,
            ProviderCapability.TRAINING,
            ProviderCapability.SPOT_INSTANCES,
            ProviderCapability.DEDICATED,
        ]

    @property
    def supported_gpu_types(self) -> list[GPUType]:
        return list(self.TYPICAL_PRICING.keys())

    @property
    def regions(self) -> list[str]:
        # Vast.ai has hosts globally
        return ["us", "eu", "asia", "global"]

    async def get_available_instances(
        self,
        gpu_type: GPUType | None = None,
        region: str | None = None,
    ) -> list[GPUInstance]:
        """Get available Vast.ai instances from the marketplace."""
        if not self.api_key:
            logger.warning("Vast.ai API key not configured")
            return []

        try:
            # Build search query for Vast.ai offers
            query = {
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "rented": {"eq": False},
            }

            # Add GPU filter if specified
            if gpu_type:
                gpu_name = self._get_gpu_name(gpu_type)
                if gpu_name:
                    query["gpu_name"] = {"eq": gpu_name}

            # Search offers from Vast.ai API
            data = await self._make_request(
                "GET",
                "/bundles/",
                params={"q": str(query)},
            )
            offers = data.get("offers", [])

            instances = []
            for offer in offers:
                # Map GPU name to our type
                offer_gpu_name = offer.get("gpu_name", "").lower()
                gtype = self._map_gpu_type(offer_gpu_name)

                if gtype is None:
                    continue
                if gpu_type and gtype != gpu_type:
                    continue

                # Extract pricing
                dph = offer.get("dph_total", 0)  # Price per hour
                pricing = GPUPricing(
                    gpu_type=gtype,
                    price_per_hour=dph,
                    price_per_second=dph / 3600,
                    spot_price_per_hour=dph * 0.7 if offer.get("is_bid", False) else None,
                    region=offer.get("geolocation", "unknown"),
                    availability=1,
                )

                instances.append(
                    GPUInstance(
                        id=str(offer.get("id")),
                        provider=self.provider_id,
                        gpu_type=gtype,
                        gpu_count=offer.get("num_gpus", 1),
                        vram_gb=int(offer.get("gpu_ram", 0) / 1024),  # MB to GB
                        cpu_cores=offer.get("cpu_cores", 0),
                        ram_gb=int(offer.get("cpu_ram", 0) / 1024),  # MB to GB
                        storage_gb=int(offer.get("disk_space", 0)),
                        region=offer.get("geolocation", "unknown"),
                        is_available=True,
                        is_spot=offer.get("is_bid", False),
                        pricing=pricing,
                        capabilities=self.capabilities,
                        metadata={
                            "reliability_score": offer.get("reliability2", 0.9),
                            "host_id": str(offer.get("machine_id")),
                            "dlperf": offer.get("dlperf", 0),
                            "cuda_version": offer.get("cuda_max_good", ""),
                        },
                    )
                )

            return instances

        except httpx.HTTPStatusError as e:
            logger.error(f"Vast.ai API error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Failed to get Vast.ai instances: {e}")
            return []

    def _get_gpu_name(self, gpu_type: GPUType) -> str | None:
        """Get Vast.ai GPU name from our type."""
        gpu_names = {
            GPUType.RTX_3090: "RTX 3090",
            GPUType.RTX_4090: "RTX 4090",
            GPUType.A10: "A10",
            GPUType.A40: "A40",
            GPUType.A100_40GB: "A100",
            GPUType.A100_80GB: "A100",
            GPUType.H100: "H100",
        }
        return gpu_names.get(gpu_type)

    def _map_gpu_type(self, gpu_name: str) -> GPUType | None:
        """Map GPU name to our GPUType enum."""
        name_lower = gpu_name.lower()
        if "h100" in name_lower:
            return GPUType.H100
        elif "a100" in name_lower and "80" in name_lower:
            return GPUType.A100_80GB
        elif "a100" in name_lower:
            return GPUType.A100_40GB
        elif "a40" in name_lower:
            return GPUType.A40
        elif "a10" in name_lower:
            return GPUType.A10
        elif "4090" in name_lower:
            return GPUType.RTX_4090
        elif "3090" in name_lower:
            return GPUType.RTX_3090
        return None

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
        region: str | None = None,
    ) -> GPUPricing | None:
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
        region: str | None = None,
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
            # Find best matching offer within budget
            instances = await self.get_available_instances(gpu_type=gpu_type, region=region)

            # Filter by price and sort by best value
            matching = [
                i for i in instances if i.pricing and i.pricing.price_per_hour <= max_price_per_hour
            ]

            if not matching:
                return ProvisionResult(
                    success=False,
                    error_message=f"No offers found within ${max_price_per_hour}/hr budget",
                    error_code="NO_OFFERS",
                )

            # Sort by price (cheapest first)
            matching.sort(key=lambda x: x.pricing.price_per_hour if x.pricing else float("inf"))
            best_offer = matching[0]

            # Create instance via Vast.ai API
            create_data = {
                "id": int(best_offer.id),
                "image": "scenemachine/worker:latest",
                "disk": 50,  # GB
                "onstart": "",  # Startup script
            }

            response = await self._make_request("PUT", "/asks/", json=create_data)
            new_contract = response.get("new_contract")

            if not new_contract:
                return ProvisionResult(
                    success=False,
                    error_message="Failed to create instance",
                    error_code="CREATE_FAILED",
                )

            instance_id = str(new_contract)

            # Get instance details
            details = await self._make_request("GET", f"/instances/{instance_id}")
            instance_info = details.get("instances", [{}])[0] if details.get("instances") else {}

            ssh_host = instance_info.get("public_ipaddr", "")
            ssh_port = instance_info.get("ports", {}).get("22/tcp", [{}])[0].get("HostPort", 22)

            return ProvisionResult(
                success=True,
                instance_id=instance_id,
                instance=GPUInstance(
                    id=instance_id,
                    provider=self.provider_id,
                    gpu_type=gpu_type,
                    gpu_count=best_offer.gpu_count,
                    vram_gb=best_offer.vram_gb,
                    region=best_offer.region,
                    is_available=True,
                    is_spot=spot,
                    pricing=best_offer.pricing,
                ),
                ssh_host=ssh_host,
                ssh_port=int(ssh_port) if ssh_port else 22,
                ssh_user="root",
                api_endpoint=f"http://{ssh_host}:8080",
                startup_time_seconds=60.0,
            )

        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            with contextlib.suppress(Exception):
                error_msg = e.response.json().get("msg", str(e))
            logger.error(f"Vast.ai API error during provision: {error_msg}")
            return ProvisionResult(
                success=False,
                error_message=error_msg,
                error_code="API_ERROR",
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
            # Call Vast.ai API to destroy instance
            await self._make_request("DELETE", f"/instances/{instance_id}/")
            logger.info(f"Terminated Vast.ai instance: {instance_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"API error terminating instance {instance_id}: {e.response.status_code}")
            return False
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

            # Check API health by getting user info
            await self._make_request("GET", "/users/current/")

            latency = (time.time() - start) * 1000

            instances = await self.get_available_instances()
            available_count = len(instances)

            return ProviderHealth(
                available=True,
                message="Vast.ai marketplace is available",
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
