"""Analytics service for generation metrics, costs, and performance tracking."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Character, Project, Scene, Shot
from scenemachine.models.generation_job import GenerationJob, JobProvider, JobStatus

logger = logging.getLogger(__name__)


@dataclass
class GenerationStats:
    """Generation job statistics."""

    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    pending_jobs: int
    success_rate: float
    avg_generation_time_seconds: float
    total_generation_time_seconds: float


@dataclass
class CostStats:
    """Cost statistics."""

    total_cost_usd: float
    cost_by_provider: Dict[str, float]
    cost_by_project: Dict[str, float]
    avg_cost_per_shot: float


@dataclass
class ProjectStats:
    """Project statistics."""

    total_projects: int
    active_projects: int
    total_scenes: int
    total_shots: int
    total_characters: int


@dataclass
class PerformanceStats:
    """Performance statistics."""

    avg_wait_time_seconds: float
    avg_processing_time_seconds: float
    peak_concurrent_jobs: int
    current_queue_size: int


class AnalyticsService:
    """Service for gathering analytics and metrics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_time_filter(self, time_range: str) -> Optional[datetime]:
        """Convert time range string to datetime filter."""
        now = datetime.now(timezone.utc)

        if time_range == "24h":
            return now - timedelta(hours=24)
        elif time_range == "7d":
            return now - timedelta(days=7)
        elif time_range == "30d":
            return now - timedelta(days=30)
        elif time_range == "all":
            return None
        else:
            return now - timedelta(days=7)  # Default to 7 days

    async def get_generation_stats(
        self,
        time_range: str = "7d",
        project_id: Optional[UUID] = None,
    ) -> GenerationStats:
        """Get generation job statistics.

        Args:
            time_range: Time range filter (24h, 7d, 30d, all)
            project_id: Optional project filter
        """
        time_filter = self._get_time_filter(time_range)

        # Base query
        base_query = select(GenerationJob)

        if time_filter:
            base_query = base_query.where(GenerationJob.created_at >= time_filter)

        if project_id:
            base_query = base_query.join(Shot).where(Shot.project_id == project_id)

        # Total jobs
        total_result = await self.session.execute(
            select(func.count(GenerationJob.id)).select_from(base_query.subquery())
        )
        total_jobs = total_result.scalar() or 0

        # Jobs by status
        status_counts = {}
        for status in JobStatus:
            status_query = base_query.where(GenerationJob.status == status)
            result = await self.session.execute(
                select(func.count(GenerationJob.id)).select_from(status_query.subquery())
            )
            status_counts[status] = result.scalar() or 0

        completed_jobs = status_counts.get(JobStatus.COMPLETED, 0)
        failed_jobs = status_counts.get(JobStatus.FAILED, 0) + status_counts.get(JobStatus.TIMEOUT, 0)
        cancelled_jobs = status_counts.get(JobStatus.CANCELLED, 0)
        pending_jobs = status_counts.get(JobStatus.PENDING, 0)

        # Success rate
        finished_jobs = completed_jobs + failed_jobs + cancelled_jobs
        success_rate = (completed_jobs / finished_jobs * 100) if finished_jobs > 0 else 0.0

        # Generation times (only for completed jobs)
        completed_query = base_query.where(GenerationJob.status == JobStatus.COMPLETED)
        time_result = await self.session.execute(completed_query)
        completed_jobs_list = time_result.scalars().all()

        generation_times = [
            j.duration_seconds for j in completed_jobs_list
            if j.duration_seconds is not None
        ]

        avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0.0
        total_generation_time = sum(generation_times)

        return GenerationStats(
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            cancelled_jobs=cancelled_jobs,
            pending_jobs=pending_jobs,
            success_rate=success_rate,
            avg_generation_time_seconds=avg_generation_time,
            total_generation_time_seconds=total_generation_time,
        )

    async def get_cost_stats(
        self,
        time_range: str = "7d",
        project_id: Optional[UUID] = None,
    ) -> CostStats:
        """Get cost statistics.

        Args:
            time_range: Time range filter (24h, 7d, 30d, all)
            project_id: Optional project filter
        """
        time_filter = self._get_time_filter(time_range)

        # Base query for jobs with cost
        base_query = select(GenerationJob).where(GenerationJob.cost_usd.isnot(None))

        if time_filter:
            base_query = base_query.where(GenerationJob.created_at >= time_filter)

        if project_id:
            base_query = base_query.join(Shot).where(Shot.project_id == project_id)

        # Get all jobs with costs
        result = await self.session.execute(base_query)
        jobs = result.scalars().all()

        # Calculate totals
        total_cost = sum(j.cost_usd or 0 for j in jobs)

        # Cost by provider
        cost_by_provider: Dict[str, float] = {}
        for job in jobs:
            provider_name = job.provider.value
            cost_by_provider[provider_name] = cost_by_provider.get(provider_name, 0) + (job.cost_usd or 0)

        # Cost by project (requires joining through shots)
        cost_by_project: Dict[str, float] = {}
        if not project_id:
            # Get shot -> project mappings
            shot_ids = [j.shot_id for j in jobs]
            if shot_ids:
                shots_query = select(Shot).where(Shot.id.in_(shot_ids))
                shots_result = await self.session.execute(shots_query)
                shots = {s.id: s for s in shots_result.scalars().all()}

                # Get project names
                project_ids = {s.project_id for s in shots.values()}
                if project_ids:
                    projects_query = select(Project).where(Project.id.in_(project_ids))
                    projects_result = await self.session.execute(projects_query)
                    projects = {p.id: p.name for p in projects_result.scalars().all()}

                    for job in jobs:
                        shot = shots.get(job.shot_id)
                        if shot:
                            project_name = projects.get(shot.project_id, "Unknown")
                            cost_by_project[project_name] = cost_by_project.get(project_name, 0) + (job.cost_usd or 0)

        # Average cost per completed shot
        completed_count = len([j for j in jobs if j.status == JobStatus.COMPLETED])
        avg_cost_per_shot = total_cost / completed_count if completed_count > 0 else 0.0

        return CostStats(
            total_cost_usd=total_cost,
            cost_by_provider=cost_by_provider,
            cost_by_project=cost_by_project,
            avg_cost_per_shot=avg_cost_per_shot,
        )

    async def get_project_stats(self) -> ProjectStats:
        """Get project statistics."""
        # Total projects
        total_result = await self.session.execute(select(func.count(Project.id)))
        total_projects = total_result.scalar() or 0

        # Active projects (have activity in last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_result = await self.session.execute(
            select(func.count(Project.id)).where(Project.updated_at >= week_ago)
        )
        active_projects = active_result.scalar() or 0

        # Total scenes
        scenes_result = await self.session.execute(select(func.count(Scene.id)))
        total_scenes = scenes_result.scalar() or 0

        # Total shots
        shots_result = await self.session.execute(select(func.count(Shot.id)))
        total_shots = shots_result.scalar() or 0

        # Total characters
        chars_result = await self.session.execute(select(func.count(Character.id)))
        total_characters = chars_result.scalar() or 0

        return ProjectStats(
            total_projects=total_projects,
            active_projects=active_projects,
            total_scenes=total_scenes,
            total_shots=total_shots,
            total_characters=total_characters,
        )

    async def get_performance_stats(self) -> PerformanceStats:
        """Get performance statistics."""
        # Get all completed jobs for wait/processing time
        completed_query = select(GenerationJob).where(
            GenerationJob.status == JobStatus.COMPLETED
        ).order_by(GenerationJob.completed_at.desc()).limit(100)

        result = await self.session.execute(completed_query)
        jobs = result.scalars().all()

        # Calculate average wait time
        wait_times = [
            j.wait_time_seconds for j in jobs
            if j.wait_time_seconds is not None
        ]
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0

        # Calculate average processing time
        processing_times = [
            j.duration_seconds for j in jobs
            if j.duration_seconds is not None
        ]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0

        # Peak concurrent jobs (estimate from overlapping time ranges)
        # For simplicity, count max running jobs at any point
        peak_concurrent = await self._estimate_peak_concurrent()

        # Current queue size
        queue_query = select(func.count(GenerationJob.id)).where(
            GenerationJob.status.in_([JobStatus.PENDING, JobStatus.PREPARING, JobStatus.RUNNING])
        )
        queue_result = await self.session.execute(queue_query)
        current_queue_size = queue_result.scalar() or 0

        return PerformanceStats(
            avg_wait_time_seconds=avg_wait_time,
            avg_processing_time_seconds=avg_processing_time,
            peak_concurrent_jobs=peak_concurrent,
            current_queue_size=current_queue_size,
        )

    async def _estimate_peak_concurrent(self) -> int:
        """Estimate peak concurrent jobs from history."""
        # Get running jobs from last 24 hours
        day_ago = datetime.now(timezone.utc) - timedelta(days=1)

        running_query = select(GenerationJob).where(
            GenerationJob.started_at >= day_ago,
            GenerationJob.started_at.isnot(None),
        )

        result = await self.session.execute(running_query)
        jobs = result.scalars().all()

        if not jobs:
            return 0

        # Create events list (start and end times)
        events: List[tuple[datetime, int]] = []
        for job in jobs:
            if job.started_at:
                events.append((job.started_at, 1))  # Job started
            if job.completed_at:
                events.append((job.completed_at, -1))  # Job ended

        # Sort by time
        events.sort(key=lambda x: x[0])

        # Find peak
        current = 0
        peak = 0
        for _, delta in events:
            current += delta
            peak = max(peak, current)

        return peak

    async def get_provider_usage(
        self,
        time_range: str = "7d",
    ) -> List[Dict]:
        """Get usage statistics by provider.

        Args:
            time_range: Time range filter
        """
        time_filter = self._get_time_filter(time_range)

        results = []
        for provider in JobProvider:
            query = select(GenerationJob).where(GenerationJob.provider == provider)

            if time_filter:
                query = query.where(GenerationJob.created_at >= time_filter)

            result = await self.session.execute(query)
            jobs = result.scalars().all()

            if jobs:
                total_jobs = len(jobs)
                completed = len([j for j in jobs if j.status == JobStatus.COMPLETED])
                failed = len([j for j in jobs if j.status in (JobStatus.FAILED, JobStatus.TIMEOUT)])
                total_cost = sum(j.cost_usd or 0 for j in jobs)

                results.append({
                    "provider": provider.value,
                    "total_jobs": total_jobs,
                    "completed_jobs": completed,
                    "failed_jobs": failed,
                    "success_rate": (completed / total_jobs * 100) if total_jobs > 0 else 0,
                    "total_cost_usd": total_cost,
                })

        return results

    async def get_daily_stats(
        self,
        days: int = 7,
        project_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """Get daily generation statistics.

        Args:
            days: Number of days to include
            project_id: Optional project filter
        """
        results = []
        now = datetime.now(timezone.utc)

        for i in range(days):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            query = select(GenerationJob).where(
                GenerationJob.created_at >= day_start,
                GenerationJob.created_at < day_end,
            )

            if project_id:
                query = query.join(Shot).where(Shot.project_id == project_id)

            result = await self.session.execute(query)
            jobs = result.scalars().all()

            completed = len([j for j in jobs if j.status == JobStatus.COMPLETED])
            failed = len([j for j in jobs if j.status in (JobStatus.FAILED, JobStatus.TIMEOUT)])
            total_cost = sum(j.cost_usd or 0 for j in jobs)

            results.append({
                "date": day_start.date().isoformat(),
                "total_jobs": len(jobs),
                "completed_jobs": completed,
                "failed_jobs": failed,
                "success_rate": (completed / len(jobs) * 100) if jobs else 0,
                "total_cost_usd": total_cost,
            })

        # Reverse to get chronological order
        results.reverse()
        return results
