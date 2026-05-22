"""Cost tracking service.

Tracks costs for video generation, LLM usage, and storage
with aggregation and reporting capabilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus

logger = logging.getLogger(__name__)


class CostCategory(StrEnum):
    """Cost categories for tracking."""

    VIDEO_GENERATION = "video_generation"
    LLM_PROMPT = "llm_prompt"
    LLM_COMPLETION = "llm_completion"
    AUDIO_GENERATION = "audio_generation"
    STORAGE = "storage"
    EXPORT = "export"


@dataclass
class CostBreakdown:
    """Breakdown of costs by category and provider."""

    total_usd: float = 0.0
    by_category: dict[str, float] = field(default_factory=dict)
    by_provider: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)
    job_count: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0


@dataclass
class CostEstimate:
    """Cost estimate for a generation request."""

    provider: str
    model: str
    estimated_cost_usd: float
    duration_seconds: float
    cost_per_second: float
    notes: str | None = None


@dataclass
class UsageStats:
    """Usage statistics for a period."""

    period_start: datetime
    period_end: datetime
    total_jobs: int
    total_cost_usd: float
    total_duration_seconds: float
    average_cost_per_job: float
    average_duration_per_job: float
    breakdown: CostBreakdown


# Provider cost rates (USD per second of video)
PROVIDER_RATES = {
    JobProvider.LOCAL: 0.0,  # Free for local
    JobProvider.REPLICATE: {
        "svd": 0.05,
        "minimax": 0.08,
        "luma": 0.10,
        "kling": 0.06,
        "default": 0.07,
    },
    JobProvider.FAL: {
        "fast-svd": 0.03,
        "animatediff": 0.04,
        "cogvideox": 0.05,
        "hunyuan": 0.06,
        "ltx": 0.04,
        "default": 0.05,
    },
    JobProvider.RUNPOD: {
        "gen-2": 0.12,
        "gen-3": 0.15,
        "default": 0.10,
    },
}

# LLM cost rates (USD per 1K tokens)
LLM_RATES = {
    "anthropic": {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
        "default": {"input": 0.003, "output": 0.015},
    },
    "openai": {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "default": {"input": 0.005, "output": 0.015},
    },
}


class CostTrackingService:
    """Service for tracking and reporting costs.

    Features:
    - Track generation costs by provider/model
    - Estimate costs before generation
    - Generate usage reports
    - Set budget alerts
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize cost tracking service.

        Args:
            session: Database session
        """
        self.session = session
        self._budget_limit: float | None = None
        self._budget_period_days: int = 30

    def set_budget_limit(self, limit_usd: float, period_days: int = 30) -> None:
        """Set a budget limit for alerts.

        Args:
            limit_usd: Budget limit in USD
            period_days: Period for the budget (default 30 days)
        """
        self._budget_limit = limit_usd
        self._budget_period_days = period_days

    def estimate_generation_cost(
        self,
        provider: JobProvider,
        model_id: str | None = None,
        duration_seconds: float = 3.0,
    ) -> CostEstimate:
        """Estimate cost for a video generation.

        Args:
            provider: Generation provider
            model_id: Specific model ID
            duration_seconds: Video duration

        Returns:
            CostEstimate with breakdown
        """
        rates = PROVIDER_RATES.get(provider, 0.0)

        if isinstance(rates, dict):
            cost_per_second = rates.get(model_id or "default", rates.get("default", 0.07))
        else:
            cost_per_second = rates

        estimated_cost = cost_per_second * duration_seconds

        return CostEstimate(
            provider=provider.value,
            model=model_id or "default",
            estimated_cost_usd=estimated_cost,
            duration_seconds=duration_seconds,
            cost_per_second=cost_per_second,
        )

    def estimate_llm_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for LLM API call.

        Args:
            provider: LLM provider (anthropic, openai)
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        provider_rates = LLM_RATES.get(provider, {})
        model_rates = provider_rates.get(model, provider_rates.get("default", {}))

        input_rate = model_rates.get("input", 0.003)  # per 1K tokens
        output_rate = model_rates.get("output", 0.015)

        input_cost = (input_tokens / 1000) * input_rate
        output_cost = (output_tokens / 1000) * output_rate

        return input_cost + output_cost

    async def get_project_costs(
        self,
        project_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CostBreakdown:
        """Get cost breakdown for a project.

        Args:
            project_id: Project UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            CostBreakdown with detailed costs
        """
        from scenemachine.models import Scene, Shot

        # Build query for generation jobs via shots
        stmt = (
            select(GenerationJob)
            .join(Shot, GenerationJob.shot_id == Shot.id)
            .join(Scene, Shot.scene_id == Scene.id)
            .where(Scene.project_id == project_id)
        )

        if start_date:
            stmt = stmt.where(GenerationJob.created_at >= start_date)
        if end_date:
            stmt = stmt.where(GenerationJob.created_at <= end_date)

        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        return self._calculate_breakdown(jobs)

    async def get_period_costs(
        self,
        start_date: datetime,
        end_date: datetime,
        project_id: UUID | None = None,
    ) -> UsageStats:
        """Get usage statistics for a time period.

        Args:
            start_date: Period start
            end_date: Period end
            project_id: Optional project filter

        Returns:
            UsageStats with breakdown
        """
        from scenemachine.models import Scene, Shot

        stmt = select(GenerationJob).where(
            GenerationJob.created_at >= start_date,
            GenerationJob.created_at <= end_date,
        )

        if project_id:
            stmt = (
                stmt.join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .where(Scene.project_id == project_id)
            )

        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        breakdown = self._calculate_breakdown(jobs)

        total_duration = sum(
            j.parameters.get("duration_seconds", 3.0) if j.parameters else 3.0
            for j in jobs
            if j.status == JobStatus.COMPLETED
        )

        return UsageStats(
            period_start=start_date,
            period_end=end_date,
            total_jobs=len(jobs),
            total_cost_usd=breakdown.total_usd,
            total_duration_seconds=total_duration,
            average_cost_per_job=breakdown.total_usd / len(jobs) if jobs else 0,
            average_duration_per_job=total_duration / breakdown.successful_jobs
            if breakdown.successful_jobs
            else 0,
            breakdown=breakdown,
        )

    async def get_monthly_report(
        self,
        year: int,
        month: int,
        project_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get monthly cost report.

        Args:
            year: Year
            month: Month (1-12)
            project_id: Optional project filter

        Returns:
            Monthly report with daily breakdown
        """
        from calendar import monthrange

        # Get start and end of month
        start_date = datetime(year, month, 1, tzinfo=UTC)
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

        # Get overall stats
        stats = await self.get_period_costs(start_date, end_date, project_id)

        # Get daily breakdown
        daily_costs: dict[str, float] = {}
        daily_jobs: dict[str, int] = {}

        from scenemachine.models import Scene, Shot

        stmt = select(GenerationJob).where(
            GenerationJob.created_at >= start_date,
            GenerationJob.created_at <= end_date,
        )

        if project_id:
            stmt = (
                stmt.join(Shot, GenerationJob.shot_id == Shot.id)
                .join(Scene, Shot.scene_id == Scene.id)
                .where(Scene.project_id == project_id)
            )

        result = await self.session.execute(stmt)
        jobs = result.scalars().all()

        for job in jobs:
            day_key = job.created_at.strftime("%Y-%m-%d")
            cost = job.cost_usd or 0.0
            daily_costs[day_key] = daily_costs.get(day_key, 0.0) + cost
            daily_jobs[day_key] = daily_jobs.get(day_key, 0) + 1

        return {
            "year": year,
            "month": month,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_cost_usd": stats.total_cost_usd,
            "total_jobs": stats.total_jobs,
            "total_duration_seconds": stats.total_duration_seconds,
            "average_cost_per_job": stats.average_cost_per_job,
            "daily_costs": daily_costs,
            "daily_job_counts": daily_jobs,
            "breakdown": {
                "by_provider": stats.breakdown.by_provider,
                "by_model": stats.breakdown.by_model,
                "successful_jobs": stats.breakdown.successful_jobs,
                "failed_jobs": stats.breakdown.failed_jobs,
            },
            "budget_status": self._get_budget_status(stats.total_cost_usd),
        }

    async def get_provider_comparison(
        self,
        project_id: UUID | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Compare costs across providers.

        Args:
            project_id: Optional project filter
            days: Number of days to analyze

        Returns:
            Provider comparison data
        """
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        stats = await self.get_period_costs(start_date, end_date, project_id)

        # Calculate per-provider metrics
        provider_metrics = {}
        for provider, cost in stats.breakdown.by_provider.items():
            # Count jobs per provider
            from scenemachine.models import Scene, Shot

            stmt = select(func.count(GenerationJob.id)).where(
                GenerationJob.provider == provider,
                GenerationJob.created_at >= start_date,
                GenerationJob.created_at <= end_date,
            )

            if project_id:
                stmt = (
                    stmt.join(Shot, GenerationJob.shot_id == Shot.id)
                    .join(Scene, Shot.scene_id == Scene.id)
                    .where(Scene.project_id == project_id)
                )

            result = await self.session.execute(stmt)
            job_count = result.scalar() or 0

            provider_metrics[provider] = {
                "total_cost_usd": cost,
                "job_count": job_count,
                "average_cost_per_job": cost / job_count if job_count > 0 else 0,
            }

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_cost_usd": stats.total_cost_usd,
            "providers": provider_metrics,
            "recommended_provider": self._get_recommended_provider(provider_metrics),
        }

    async def check_budget_alert(
        self,
        project_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Check if budget limit has been exceeded.

        Args:
            project_id: Optional project filter

        Returns:
            Alert info if budget exceeded, None otherwise
        """
        if not self._budget_limit:
            return None

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=self._budget_period_days)

        stats = await self.get_period_costs(start_date, end_date, project_id)

        if stats.total_cost_usd >= self._budget_limit:
            return {
                "alert_type": "budget_exceeded",
                "current_spend_usd": stats.total_cost_usd,
                "budget_limit_usd": self._budget_limit,
                "period_days": self._budget_period_days,
                "percent_used": (stats.total_cost_usd / self._budget_limit) * 100,
            }
        elif stats.total_cost_usd >= self._budget_limit * 0.8:
            return {
                "alert_type": "budget_warning",
                "current_spend_usd": stats.total_cost_usd,
                "budget_limit_usd": self._budget_limit,
                "period_days": self._budget_period_days,
                "percent_used": (stats.total_cost_usd / self._budget_limit) * 100,
            }

        return None

    def _calculate_breakdown(self, jobs: list[GenerationJob]) -> CostBreakdown:
        """Calculate cost breakdown from jobs.

        Args:
            jobs: List of generation jobs

        Returns:
            CostBreakdown
        """
        breakdown = CostBreakdown()

        for job in jobs:
            cost = job.cost_usd or 0.0
            breakdown.total_usd += cost
            breakdown.job_count += 1

            if job.status == JobStatus.COMPLETED:
                breakdown.successful_jobs += 1
            elif job.status == JobStatus.FAILED:
                breakdown.failed_jobs += 1

            # By provider
            provider = job.provider.value if job.provider else "unknown"
            breakdown.by_provider[provider] = breakdown.by_provider.get(provider, 0.0) + cost

            # By model
            model = job.model_id or "default"
            breakdown.by_model[model] = breakdown.by_model.get(model, 0.0) + cost

            # By category (all video generation for now)
            category = CostCategory.VIDEO_GENERATION.value
            breakdown.by_category[category] = breakdown.by_category.get(category, 0.0) + cost

        return breakdown

    def _get_budget_status(self, current_spend: float) -> dict[str, Any]:
        """Get budget status.

        Args:
            current_spend: Current spend in USD

        Returns:
            Budget status dict
        """
        if not self._budget_limit:
            return {"has_budget": False}

        percent_used = (current_spend / self._budget_limit) * 100
        remaining = max(0, self._budget_limit - current_spend)

        status = "ok"
        if percent_used >= 100:
            status = "exceeded"
        elif percent_used >= 80:
            status = "warning"

        return {
            "has_budget": True,
            "limit_usd": self._budget_limit,
            "spent_usd": current_spend,
            "remaining_usd": remaining,
            "percent_used": percent_used,
            "status": status,
            "period_days": self._budget_period_days,
        }

    def _get_recommended_provider(
        self,
        provider_metrics: dict[str, dict[str, Any]],
    ) -> str | None:
        """Get recommended provider based on cost efficiency.

        Args:
            provider_metrics: Provider metrics dict

        Returns:
            Recommended provider name or None
        """
        if not provider_metrics:
            return None

        # Find provider with lowest average cost per job (that has usage)
        best_provider = None
        best_avg_cost = float("inf")

        for provider, metrics in provider_metrics.items():
            if metrics["job_count"] > 0 and metrics["average_cost_per_job"] < best_avg_cost:
                best_avg_cost = metrics["average_cost_per_job"]
                best_provider = provider

        return best_provider


async def get_cost_tracking_service(session: AsyncSession) -> CostTrackingService:
    """Factory function for CostTrackingService."""
    return CostTrackingService(session)
