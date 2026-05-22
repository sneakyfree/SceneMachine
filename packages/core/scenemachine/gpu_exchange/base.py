"""Base classes and interfaces for GPU Exchange providers.

This module defines the core abstractions for GPU provider integration:
- GPUExchangeProvider: Abstract base class all GPU providers must implement
- GPUInstance: Represents a GPU instance available for provisioning
- GPUPricing: Current pricing information for a GPU type
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class GPUType(StrEnum):
    """Standard GPU types across providers."""

    # NVIDIA Consumer
    RTX_3090 = "rtx_3090"
    RTX_4090 = "rtx_4090"

    # NVIDIA Professional
    A10 = "a10"
    A40 = "a40"
    A100_40GB = "a100_40gb"
    A100_80GB = "a100_80gb"
    H100 = "h100"
    L40S = "l40s"

    # AMD
    MI250X = "mi250x"
    MI300X = "mi300x"


class ProviderCapability(StrEnum):
    """Capabilities a GPU provider may support."""

    VIDEO_GENERATION = "video_generation"
    IMAGE_GENERATION = "image_generation"
    LLM_INFERENCE = "llm_inference"
    TRAINING = "training"
    FINE_TUNING = "fine_tuning"
    SERVERLESS = "serverless"
    DEDICATED = "dedicated"
    SPOT_INSTANCES = "spot"
    RESERVED = "reserved"


@dataclass
class GPUPricing:
    """Current pricing for a GPU instance type."""

    gpu_type: GPUType
    price_per_hour: float  # USD
    price_per_second: float  # USD (for sub-hour billing)
    spot_price_per_hour: float | None = None
    reserved_price_per_hour: float | None = None
    currency: str = "USD"
    region: str = "us-east-1"
    availability: int = 0  # Number of instances available
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if self.price_per_second == 0 and self.price_per_hour > 0:
            self.price_per_second = self.price_per_hour / 3600


@dataclass
class GPUInstance:
    """Represents a GPU instance available for provisioning."""

    id: str
    provider: str
    gpu_type: GPUType
    gpu_count: int = 1
    vram_gb: int = 24
    cpu_cores: int = 8
    ram_gb: int = 32
    storage_gb: int = 100
    region: str = "us-east-1"
    is_available: bool = True
    is_spot: bool = False
    pricing: GPUPricing | None = None
    capabilities: list[ProviderCapability] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProvisionResult:
    """Result of provisioning a GPU instance."""

    success: bool
    instance_id: str | None = None
    instance: GPUInstance | None = None
    ssh_host: str | None = None
    ssh_port: int = 22
    ssh_user: str = "root"
    api_endpoint: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    startup_time_seconds: float | None = None


@dataclass
class ProviderHealth:
    """Health status of a GPU provider."""

    available: bool
    message: str
    latency_ms: float | None = None
    instances_available: int = 0
    queue_depth: int = 0
    error_code: str | None = None
    last_check: datetime = field(default_factory=datetime.utcnow)


class GPUExchangeProvider(ABC):
    """Abstract base class for GPU Exchange providers.

    All GPU providers must implement this interface to be compatible
    with the GPU Exchange routing system.

    Example:
        class LambdaLabsProvider(GPUExchangeProvider):
            @property
            def name(self) -> str:
                return "Lambda Labs"

            @property
            def provider_id(self) -> str:
                return "lambda_labs"

            async def get_available_instances(self) -> List[GPUInstance]:
                # Implementation
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier."""
        ...

    @property
    def capabilities(self) -> list[ProviderCapability]:
        """Provider capabilities. Override to customize."""
        return [ProviderCapability.VIDEO_GENERATION]

    @property
    def supported_gpu_types(self) -> list[GPUType]:
        """GPU types supported by this provider. Override to customize."""
        return [GPUType.A100_80GB, GPUType.H100]

    @property
    def regions(self) -> list[str]:
        """Available regions. Override to customize."""
        return ["us-east-1"]

    @abstractmethod
    async def get_available_instances(
        self,
        gpu_type: GPUType | None = None,
        region: str | None = None,
    ) -> list[GPUInstance]:
        """Get list of available GPU instances.

        Args:
            gpu_type: Filter by GPU type
            region: Filter by region

        Returns:
            List of available GPUInstance objects
        """
        ...

    @abstractmethod
    async def get_current_pricing(
        self,
        gpu_type: GPUType,
        region: str | None = None,
    ) -> GPUPricing | None:
        """Get current pricing for a GPU type.

        Args:
            gpu_type: The GPU type to get pricing for
            region: Optional region filter

        Returns:
            GPUPricing or None if not available
        """
        ...

    @abstractmethod
    async def provision_instance(
        self,
        gpu_type: GPUType,
        max_price_per_hour: float,
        region: str | None = None,
        spot: bool = False,
    ) -> ProvisionResult:
        """Provision a GPU instance.

        Args:
            gpu_type: The GPU type to provision
            max_price_per_hour: Maximum price willing to pay
            region: Preferred region
            spot: Whether to use spot/preemptible instances

        Returns:
            ProvisionResult with instance details or error
        """
        ...

    @abstractmethod
    async def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a running instance.

        Args:
            instance_id: The instance to terminate

        Returns:
            True if successful, False otherwise
        """
        ...

    async def get_queue_depth(self) -> int:
        """Get current queue depth for serverless providers.

        Returns:
            Number of jobs in queue, or 0 for dedicated providers
        """
        return 0

    async def check_availability(self) -> bool:
        """Check if provider API is available."""
        try:
            await self.get_available_instances()
            return True
        except Exception:
            return False

    async def check_health(self) -> ProviderHealth:
        """Detailed health check."""
        import time

        start = time.time()
        try:
            instances = await self.get_available_instances()
            latency = (time.time() - start) * 1000
            available_count = sum(1 for i in instances if i.is_available)

            return ProviderHealth(
                available=True,
                message=f"{self.name} is available",
                latency_ms=latency,
                instances_available=available_count,
                queue_depth=await self.get_queue_depth(),
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                message=str(e),
                error_code="HEALTH_CHECK_FAILED",
            )

    def estimate_cost(
        self,
        gpu_type: GPUType,
        duration_seconds: float,
        spot: bool = False,
    ) -> float:
        """Estimate cost for a job. Override to customize."""
        # Default estimates based on typical pricing
        base_hourly = {
            GPUType.RTX_3090: 0.50,
            GPUType.RTX_4090: 0.80,
            GPUType.A10: 0.75,
            GPUType.A40: 1.00,
            GPUType.A100_40GB: 1.50,
            GPUType.A100_80GB: 2.00,
            GPUType.H100: 3.50,
            GPUType.L40S: 1.20,
        }

        hourly_rate = base_hourly.get(gpu_type, 1.00)
        if spot:
            hourly_rate *= 0.5  # Assume 50% discount for spot

        return (hourly_rate / 3600) * duration_seconds
