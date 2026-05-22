"""Analytics API endpoints."""

from datetime import UTC
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.services.analytics import AnalyticsService
from scenemachine.services.cost_tracking import CostTrackingService

router = APIRouter()


@router.get("/generation-stats")
async def get_generation_stats(
    time_range: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get generation job statistics.

    Args:
        time_range: Time range filter (24h, 7d, 30d, all)
        project_id: Optional project filter
    """
    service = AnalyticsService(db)
    stats = await service.get_generation_stats(time_range, project_id)

    return {
        "totalJobs": stats.total_jobs,
        "completedJobs": stats.completed_jobs,
        "failedJobs": stats.failed_jobs,
        "cancelledJobs": stats.cancelled_jobs,
        "pendingJobs": stats.pending_jobs,
        "successRate": round(stats.success_rate, 2),
        "avgGenerationTimeSeconds": round(stats.avg_generation_time_seconds, 2),
        "totalGenerationTimeSeconds": round(stats.total_generation_time_seconds, 2),
        "timeRange": time_range,
    }


@router.get("/cost-stats")
async def get_cost_stats(
    time_range: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get cost statistics.

    Args:
        time_range: Time range filter (24h, 7d, 30d, all)
        project_id: Optional project filter
    """
    service = AnalyticsService(db)
    stats = await service.get_cost_stats(time_range, project_id)

    return {
        "totalCostUsd": round(stats.total_cost_usd, 4),
        "costByProvider": {k: round(v, 4) for k, v in stats.cost_by_provider.items()},
        "costByProject": {k: round(v, 4) for k, v in stats.cost_by_project.items()},
        "avgCostPerShot": round(stats.avg_cost_per_shot, 4),
        "timeRange": time_range,
    }


@router.get("/project-stats")
async def get_project_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get project statistics."""
    service = AnalyticsService(db)
    stats = await service.get_project_stats()

    return {
        "totalProjects": stats.total_projects,
        "activeProjects": stats.active_projects,
        "totalScenes": stats.total_scenes,
        "totalShots": stats.total_shots,
        "totalCharacters": stats.total_characters,
    }


@router.get("/performance-stats")
async def get_performance_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get performance statistics."""
    service = AnalyticsService(db)
    stats = await service.get_performance_stats()

    return {
        "avgWaitTimeSeconds": round(stats.avg_wait_time_seconds, 2),
        "avgProcessingTimeSeconds": round(stats.avg_processing_time_seconds, 2),
        "peakConcurrentJobs": stats.peak_concurrent_jobs,
        "currentQueueSize": stats.current_queue_size,
    }


@router.get("/provider-usage")
async def get_provider_usage(
    time_range: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get usage statistics by provider.

    Args:
        time_range: Time range filter
    """
    service = AnalyticsService(db)
    usage = await service.get_provider_usage(time_range)

    return [
        {
            "provider": item["provider"],
            "totalJobs": item["total_jobs"],
            "completedJobs": item["completed_jobs"],
            "failedJobs": item["failed_jobs"],
            "successRate": round(item["success_rate"], 2),
            "totalCostUsd": round(item["total_cost_usd"], 4),
        }
        for item in usage
    ]


@router.get("/daily-stats")
async def get_daily_stats(
    days: int = Query(7, ge=1, le=90),
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get daily generation statistics.

    Args:
        days: Number of days to include
        project_id: Optional project filter
    """
    service = AnalyticsService(db)
    stats = await service.get_daily_stats(days, project_id)

    return [
        {
            "date": item["date"],
            "totalJobs": item["total_jobs"],
            "completedJobs": item["completed_jobs"],
            "failedJobs": item["failed_jobs"],
            "successRate": round(item["success_rate"], 2),
            "totalCostUsd": round(item["total_cost_usd"], 4),
        }
        for item in stats
    ]


@router.get("/dashboard")
async def get_dashboard_stats(
    time_range: str = Query("7d", regex="^(24h|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get combined dashboard statistics.

    Returns all stats needed for the analytics dashboard in one call.
    """
    service = AnalyticsService(db)
    cost_service = CostTrackingService(db)

    # Gather all stats in parallel
    generation_stats = await service.get_generation_stats(time_range)
    cost_stats = await service.get_cost_stats(time_range)
    project_stats = await service.get_project_stats()
    performance_stats = await service.get_performance_stats()
    provider_usage = await service.get_provider_usage(time_range)
    daily_stats = await service.get_daily_stats(7)

    # Check for budget alerts
    budget_alert = await cost_service.check_budget_alert()

    return {
        "generation": {
            "totalJobs": generation_stats.total_jobs,
            "completedJobs": generation_stats.completed_jobs,
            "failedJobs": generation_stats.failed_jobs,
            "pendingJobs": generation_stats.pending_jobs,
            "successRate": round(generation_stats.success_rate, 2),
            "avgGenerationTimeSeconds": round(generation_stats.avg_generation_time_seconds, 2),
        },
        "costs": {
            "totalCostUsd": round(cost_stats.total_cost_usd, 4),
            "costByProvider": {k: round(v, 4) for k, v in cost_stats.cost_by_provider.items()},
            "avgCostPerShot": round(cost_stats.avg_cost_per_shot, 4),
        },
        "projects": {
            "totalProjects": project_stats.total_projects,
            "activeProjects": project_stats.active_projects,
            "totalScenes": project_stats.total_scenes,
            "totalShots": project_stats.total_shots,
            "totalCharacters": project_stats.total_characters,
        },
        "performance": {
            "avgWaitTimeSeconds": round(performance_stats.avg_wait_time_seconds, 2),
            "avgProcessingTimeSeconds": round(performance_stats.avg_processing_time_seconds, 2),
            "peakConcurrentJobs": performance_stats.peak_concurrent_jobs,
            "currentQueueSize": performance_stats.current_queue_size,
        },
        "providerUsage": [
            {
                "provider": item["provider"],
                "totalJobs": item["total_jobs"],
                "successRate": round(item["success_rate"], 2),
                "totalCostUsd": round(item["total_cost_usd"], 4),
            }
            for item in provider_usage
        ],
        "dailyStats": [
            {
                "date": item["date"],
                "totalJobs": item["total_jobs"],
                "successRate": round(item["success_rate"], 2),
                "totalCostUsd": round(item["total_cost_usd"], 4),
            }
            for item in daily_stats
        ],
        "budgetAlert": budget_alert,
        "timeRange": time_range,
    }


@router.get("/projects/{project_id}/costs")
async def get_project_costs(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get detailed cost breakdown for a project."""
    cost_service = CostTrackingService(db)
    breakdown = await cost_service.get_project_costs(project_id)

    return {
        "projectId": str(project_id),
        "totalCostUsd": round(breakdown.total_usd, 4),
        "byCategory": {k: round(v, 4) for k, v in breakdown.by_category.items()},
        "byProvider": {k: round(v, 4) for k, v in breakdown.by_provider.items()},
        "byModel": {k: round(v, 4) for k, v in breakdown.by_model.items()},
        "jobCount": breakdown.job_count,
        "successfulJobs": breakdown.successful_jobs,
        "failedJobs": breakdown.failed_jobs,
    }


@router.get("/cost-estimate")
async def estimate_generation_cost(
    provider: str = Query(..., description="Provider name"),
    model: str | None = Query(None, description="Model ID"),
    duration_seconds: float = Query(3.0, ge=1.0, le=30.0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Estimate cost for a video generation.

    Args:
        provider: Provider name (replicate, fal, runwayml)
        model: Optional model ID
        duration_seconds: Video duration
    """
    from scenemachine.models.generation_job import JobProvider

    try:
        provider_enum = JobProvider(provider.lower())
    except ValueError:
        return {
            "error": f"Unknown provider: {provider}",
            "supportedProviders": [p.value for p in JobProvider],
        }

    cost_service = CostTrackingService(db)
    estimate = cost_service.estimate_generation_cost(
        provider=provider_enum,
        model_id=model,
        duration_seconds=duration_seconds,
    )

    return {
        "provider": estimate.provider,
        "model": estimate.model,
        "durationSeconds": estimate.duration_seconds,
        "estimatedCostUsd": round(estimate.estimated_cost_usd, 4),
        "costPerSecond": round(estimate.cost_per_second, 4),
    }


@router.post("/budget")
async def set_budget(
    limit_usd: float = Query(..., gt=0, description="Budget limit in USD"),
    period_days: int = Query(30, ge=1, le=365, description="Budget period in days"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """FEAT-038: Set a budget limit for cost tracking alerts.

    When spending reaches 80% of the limit, a warning is surfaced.
    When spending exceeds the limit, generation requests are blocked.
    """
    cost_service = CostTrackingService(db)
    cost_service.set_budget_limit(limit_usd, period_days)

    # Check current status against the new limit
    alert = await cost_service.check_budget_alert()

    return {
        "limitUsd": limit_usd,
        "periodDays": period_days,
        "budgetAlert": alert,
        "message": f"Budget set to ${limit_usd:.2f} over {period_days} days",
    }


@router.get("/budget")
async def get_budget(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """FEAT-038: Get current budget status.

    Returns the current budget limit, spending, remaining balance,
    and alert status.
    """
    from datetime import datetime, timedelta

    cost_service = CostTrackingService(db)

    # Get current period costs
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=cost_service._budget_period_days)
    stats = await cost_service.get_period_costs(start_date, end_date)

    budget_status = cost_service._get_budget_status(stats.total_cost_usd)
    alert = await cost_service.check_budget_alert()

    return {
        "budget": budget_status,
        "currentSpend": round(stats.total_cost_usd, 4),
        "periodStart": start_date.isoformat(),
        "periodEnd": end_date.isoformat(),
        "totalJobs": stats.total_jobs,
        "budgetAlert": alert,
    }


@router.get("/provider-comparison")
async def get_provider_comparison(
    project_id: UUID | None = None,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """FEAT-038: Compare cost efficiency across providers.

    Shows cost, speed, and reliability metrics per provider to help
    users optimize their generation budget.
    """
    cost_service = CostTrackingService(db)
    comparison = await cost_service.get_provider_comparison(project_id=project_id, days=days)

    return {
        "periodDays": days,
        "projectId": str(project_id) if project_id else None,
        "providers": comparison,
    }
