"""Health check endpoints."""

import logging
import os
import platform
import time
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.config import get_settings
from scenemachine.models.generation_job import JobProvider

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str
    version: str
    environment: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Readiness check response with detailed status."""

    ready: bool
    checks: dict[str, str]
    timestamp: str


class DetailedHealthResponse(BaseModel):
    """Comprehensive system health information."""

    status: str
    version: str
    environment: str
    timestamp: str
    uptime_seconds: float
    system: dict[str, Any]
    checks: dict[str, dict[str, Any]]


# Track application start time
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns basic application status without checking dependencies.
    Use /ready for a more comprehensive check.
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> ReadinessResponse:
    """Comprehensive readiness check.

    Checks all dependencies (database, etc.) to determine if the
    application is ready to serve requests.
    """
    checks: dict[str, str] = {}

    # Database check
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        checks["database"] = f"ok ({latency:.1f}ms)"
        logger.debug(f"Database health check passed: {latency:.1f}ms")
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        logger.error(f"Database health check failed: {e}")

    # Storage check
    settings = get_settings()
    try:
        data_dir = os.path.expanduser(settings.data_dir)
        if os.path.exists(data_dir) and os.access(data_dir, os.W_OK):
            checks["storage"] = "ok"
        else:
            checks["storage"] = "error: data directory not writable"
    except Exception as e:
        checks["storage"] = f"error: {str(e)}"

    # FFmpeg check (required for assembly/export)
    try:
        import shutil
        import subprocess

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            checks["ffmpeg"] = f"ok ({version_line})"
        else:
            checks["ffmpeg"] = "warning: ffmpeg not found - assembly/export will fail"
    except Exception as e:
        checks["ffmpeg"] = f"error: {str(e)}"

    all_ok = all(v.startswith("ok") for v in checks.values())

    return ReadinessResponse(
        ready=all_ok,
        checks=checks,
        timestamp=datetime.utcnow().isoformat(),
    )


class ProviderHealthResponse(BaseModel):
    """Health status of a single video generation provider."""

    provider: str
    name: str
    available: bool
    message: str
    latency_ms: Optional[float] = None
    models_available: int = 0
    queue_length: Optional[int] = None


class ProvidersHealthResponse(BaseModel):
    """Health status of all video generation providers."""

    providers: List[ProviderHealthResponse]
    total_registered: int
    total_available: int
    timestamp: str


@router.get("/health/providers", response_model=ProvidersHealthResponse)
async def providers_health_check() -> ProvidersHealthResponse:
    """Check health of all video generation providers.

    Returns the status of each registered provider including
    availability, latency, and number of available models.
    """
    from scenemachine.generators import get_provider_registry, setup_providers

    # Ensure providers are registered
    registry = get_provider_registry()
    if not registry.list_providers():
        setup_providers()

    # Get health status of all providers
    health = await registry.get_all_health()

    providers = []
    for provider_type, status in health.items():
        provider = registry.get_provider(provider_type)
        providers.append(
            ProviderHealthResponse(
                provider=provider_type.value,
                name=provider.name if provider else "Unknown",
                available=status.available,
                message=status.message,
                latency_ms=status.latency_ms,
                models_available=status.models_available,
                queue_length=status.queue_length,
            )
        )

    return ProvidersHealthResponse(
        providers=providers,
        total_registered=len(registry.list_providers()),
        total_available=sum(1 for s in health.values() if s.available),
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/health/providers/{provider_type}")
async def provider_health_check(provider_type: str) -> ProviderHealthResponse:
    """Check health of a specific video generation provider.

    Args:
        provider_type: Provider type (e.g., 'replicate', 'fal', 'comfyui')
    """
    from scenemachine.generators import get_provider_registry, setup_providers

    # Ensure providers are registered
    registry = get_provider_registry()
    if not registry.list_providers():
        setup_providers()

    # Map string to JobProvider enum
    try:
        job_provider = JobProvider(provider_type.lower())
    except ValueError:
        return ProviderHealthResponse(
            provider=provider_type,
            name="Unknown",
            available=False,
            message=f"Unknown provider type: {provider_type}",
        )

    provider = registry.get_provider(job_provider)
    if not provider:
        return ProviderHealthResponse(
            provider=provider_type,
            name="Unknown",
            available=False,
            message=f"Provider {provider_type} not registered",
        )

    status = await provider.check_health()

    return ProviderHealthResponse(
        provider=provider_type,
        name=provider.name,
        available=status.available,
        message=status.message,
        latency_ms=status.latency_ms,
        models_available=status.models_available,
        queue_length=status.queue_length,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
) -> DetailedHealthResponse:
    """Detailed health check with system information.

    Returns comprehensive health information including system metrics.
    Useful for monitoring and debugging.
    """
    settings = get_settings()
    checks: dict[str, dict[str, Any]] = {}

    # Database check with details
    try:
        start = time.time()
        result = await db.execute(text("SELECT version()"))
        db_version = result.scalar()
        latency = (time.time() - start) * 1000
        checks["database"] = {
            "status": "ok",
            "latency_ms": round(latency, 2),
            "version": db_version,
        }
    except Exception as e:
        checks["database"] = {
            "status": "error",
            "error": str(e),
        }

    # Storage check with details
    try:
        data_dir = os.path.expanduser(settings.data_dir)
        if os.path.exists(data_dir):
            statvfs = os.statvfs(data_dir)
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            total_bytes = statvfs.f_frsize * statvfs.f_blocks
            checks["storage"] = {
                "status": "ok",
                "path": data_dir,
                "free_gb": round(free_bytes / (1024**3), 2),
                "total_gb": round(total_bytes / (1024**3), 2),
                "usage_percent": round((1 - free_bytes / total_bytes) * 100, 1),
            }
        else:
            checks["storage"] = {
                "status": "warning",
                "message": "Data directory does not exist",
            }
    except Exception as e:
        checks["storage"] = {
            "status": "error",
            "error": str(e),
        }

    # System information
    system_info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "processor": platform.processor() or "unknown",
        "pid": os.getpid(),
    }

    # Determine overall status
    all_ok = all(
        c.get("status") == "ok" for c in checks.values()
    )
    status = "healthy" if all_ok else "degraded"

    return DetailedHealthResponse(
        status=status,
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=round(time.time() - _start_time, 2),
        system=system_info,
        checks=checks,
    )


class CircuitBreakerStatusResponse(BaseModel):
    """Status of a single circuit breaker."""

    name: str
    state: str  # 'closed', 'open', 'half_open'
    total_calls: int
    successful_calls: int
    failed_calls: int
    rejected_calls: int
    consecutive_failures: int
    consecutive_successes: int
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    failure_threshold: int
    recovery_timeout: float
    remaining_timeout: float = 0.0
    success_rate: float = 0.0


class AllCircuitBreakersResponse(BaseModel):
    """Status of all circuit breakers."""

    circuits: List[CircuitBreakerStatusResponse]
    total_count: int
    open_count: int
    half_open_count: int
    timestamp: str


@router.get("/health/circuits", response_model=AllCircuitBreakersResponse)
async def get_circuit_breaker_status() -> AllCircuitBreakersResponse:
    """Get status of all circuit breakers.

    Returns the state and statistics for all registered circuit breakers,
    useful for monitoring provider health and resilience.
    """
    from scenemachine.utils.circuit_breaker import CircuitBreakerRegistry

    registry = CircuitBreakerRegistry.get_instance()
    all_status = registry.get_all_status()

    circuits = []
    open_count = 0
    half_open_count = 0

    for name, status in all_status.items():
        stats = status.get("stats", {})
        config = status.get("config", {})

        total = stats.get("total_calls", 0)
        successful = stats.get("successful_calls", 0)
        success_rate = (successful / total * 100) if total > 0 else 100.0

        state = status.get("state", "closed")
        if state == "open":
            open_count += 1
        elif state == "half_open":
            half_open_count += 1

        circuits.append(
            CircuitBreakerStatusResponse(
                name=name,
                state=state,
                total_calls=stats.get("total_calls", 0),
                successful_calls=stats.get("successful_calls", 0),
                failed_calls=stats.get("failed_calls", 0),
                rejected_calls=stats.get("rejected_calls", 0),
                consecutive_failures=stats.get("consecutive_failures", 0),
                consecutive_successes=stats.get("consecutive_successes", 0),
                last_failure_time=stats.get("last_failure"),
                last_success_time=stats.get("last_success"),
                failure_threshold=config.get("failure_threshold", 5),
                recovery_timeout=config.get("recovery_timeout", 30.0),
                remaining_timeout=status.get("remaining_timeout", 0.0),
                success_rate=round(success_rate, 1),
            )
        )

    return AllCircuitBreakersResponse(
        circuits=circuits,
        total_count=len(circuits),
        open_count=open_count,
        half_open_count=half_open_count,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.post("/health/circuits/{circuit_name}/reset")
async def reset_circuit_breaker(circuit_name: str) -> dict[str, Any]:
    """Reset a specific circuit breaker to closed state.

    Args:
        circuit_name: Name of the circuit breaker to reset
    """
    from scenemachine.utils.circuit_breaker import CircuitBreakerRegistry

    registry = CircuitBreakerRegistry.get_instance()
    cb = registry.get(circuit_name)

    if not cb:
        return {"success": False, "error": f"Circuit breaker '{circuit_name}' not found"}

    cb.reset()
    return {"success": True, "message": f"Circuit '{circuit_name}' reset to closed state"}


# ---------------------------------------------------------------------------
# FEAT-119: Prometheus-Compatible /metrics Endpoint
# ---------------------------------------------------------------------------

@router.get("/metrics", response_class=None)
async def prometheus_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Prometheus-compatible metrics endpoint.

    Returns metrics in OpenMetrics text format for scraping by
    Prometheus, Grafana Agent, or compatible monitoring systems.

    Metrics exported:
    - scenemachine_up: Application status (1=healthy)
    - scenemachine_uptime_seconds: Time since process start
    - scenemachine_info: Build/version metadata
    - scenemachine_db_up: Database reachability
    - scenemachine_db_latency_seconds: Database query latency
    - scenemachine_provider_available: Per-provider availability
    - scenemachine_circuit_breaker_state: Circuit breaker states
    - process_resident_memory_bytes: RSS memory
    """
    from fastapi.responses import Response

    lines: list[str] = []

    def _gauge(name: str, help_text: str, value: float, labels: str = ""):
        label_part = f"{{{labels}}}" if labels else ""
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name}{label_part} {value}")

    settings = get_settings()
    uptime = time.time() - _start_time

    # Core metrics
    _gauge("scenemachine_up", "Application health (1=up)", 1)
    _gauge("scenemachine_uptime_seconds", "Seconds since process start", round(uptime, 2))

    # Version info as a metric with labels
    lines.append("# HELP scenemachine_info Application version info")
    lines.append("# TYPE scenemachine_info gauge")
    lines.append(
        f'scenemachine_info{{version="{settings.version}",'
        f'environment="{settings.environment}"}} 1'
    )

    # Database health
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        db_latency = time.time() - start
        _gauge("scenemachine_db_up", "Database reachability (1=ok)", 1)
        _gauge(
            "scenemachine_db_latency_seconds",
            "Database query latency",
            round(db_latency, 6),
        )
    except Exception:
        _gauge("scenemachine_db_up", "Database reachability (1=ok)", 0)

    # Provider availability
    try:
        from scenemachine.generators import get_provider_registry, setup_providers

        registry = get_provider_registry()
        if not registry.list_providers():
            setup_providers()

        health = await registry.get_all_health()
        lines.append("# HELP scenemachine_provider_available Provider availability (1=up)")
        lines.append("# TYPE scenemachine_provider_available gauge")
        for ptype, pstatus in health.items():
            val = 1 if pstatus.available else 0
            lines.append(
                f'scenemachine_provider_available{{provider="{ptype.value}"}} {val}'
            )
    except Exception:
        pass  # Providers not yet initialized

    # Circuit breaker states
    try:
        from scenemachine.utils.circuit_breaker import CircuitBreakerRegistry

        cb_registry = CircuitBreakerRegistry.get_instance()
        all_cb = cb_registry.get_all_status()
        if all_cb:
            state_map = {"closed": 0, "half_open": 1, "open": 2}
            lines.append(
                "# HELP scenemachine_circuit_breaker_state "
                "Circuit breaker state (0=closed, 1=half_open, 2=open)"
            )
            lines.append("# TYPE scenemachine_circuit_breaker_state gauge")
            for cb_name, cb_status in all_cb.items():
                state_val = state_map.get(cb_status.get("state", "closed"), 0)
                lines.append(
                    f'scenemachine_circuit_breaker_state{{name="{cb_name}"}} {state_val}'
                )
    except Exception:
        pass

    # Process memory (Linux)
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
                    _gauge(
                        "process_resident_memory_bytes",
                        "Resident memory size in bytes",
                        rss_kb * 1024,
                    )
                    break
    except Exception:
        pass

    # FFmpeg availability
    try:
        import shutil

        ffmpeg_available = 1 if shutil.which("ffmpeg") else 0
        _gauge(
            "scenemachine_ffmpeg_available",
            "FFmpeg availability (1=found)",
            ffmpeg_available,
        )
    except Exception:
        pass

    body = "\n".join(lines) + "\n"
    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
