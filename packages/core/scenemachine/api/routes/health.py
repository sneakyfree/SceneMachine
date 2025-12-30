"""Health check endpoints."""

import logging
import os
import platform
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.config import get_settings

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

    all_ok = all(v.startswith("ok") for v in checks.values())

    return ReadinessResponse(
        ready=all_ok,
        checks=checks,
        timestamp=datetime.utcnow().isoformat(),
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
