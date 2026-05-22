"""Background job queue service for async task execution.

Provides non-blocking job processing for long-running operations like:
- Video generation
- Audio synthesis
- Video assembly
- Export processing

Uses APScheduler for lightweight background task management.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.generation_job import GenerationJob, JobStatus

logger = logging.getLogger(__name__)


class JobPriority(int, Enum):
    """Job priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class JobType(StrEnum):
    """Types of background jobs."""

    GENERATION = "generation"
    AUDIO_SYNTHESIS = "audio_synthesis"
    VIDEO_ASSEMBLY = "video_assembly"
    EXPORT = "export"
    THUMBNAIL = "thumbnail"
    BATCH_OPERATION = "batch_operation"


class RetryStrategy(StrEnum):
    """Retry strategy for failed jobs."""

    EXPONENTIAL = "exponential"  # Standard exponential backoff
    LINEAR = "linear"  # Linear backoff (for rate limits)
    IMMEDIATE = "immediate"  # Retry immediately (transient errors)
    NO_RETRY = "no_retry"  # Permanent failures


# Error patterns that are safe to retry
RETRYABLE_ERROR_PATTERNS = [
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "429",
    "503",
    "502",
    "connection reset",
    "connection timeout",
    "temporary failure",
    "temporarily unavailable",
    "service unavailable",
    "gpu memory",
    "cuda out of memory",
    "resource exhausted",
]

# Error patterns that should NOT be retried (permanent failures)
NON_RETRYABLE_ERROR_PATTERNS = [
    "invalid_api_key",
    "authentication failed",
    "unauthorized",
    "403",
    "invalid request",
    "validation error",
    "model not found",
    "content policy violation",
    "nsfw",
    "quota exceeded",
]


def classify_error(error_message: str) -> RetryStrategy:
    """Classify an error message to determine retry strategy.

    Args:
        error_message: The error message to classify

    Returns:
        RetryStrategy indicating how to handle the error
    """
    error_lower = error_message.lower()

    # Check for non-retryable (permanent) errors first
    for pattern in NON_RETRYABLE_ERROR_PATTERNS:
        if pattern.lower() in error_lower:
            return RetryStrategy.NO_RETRY

    # Check for retryable errors
    for pattern in RETRYABLE_ERROR_PATTERNS:
        if pattern.lower() in error_lower:
            # Rate limit errors get linear backoff
            if any(x in error_lower for x in ["rate", "429", "too many"]):
                return RetryStrategy.LINEAR
            # Connection errors can retry faster
            if any(x in error_lower for x in ["connection", "timeout"]):
                return RetryStrategy.EXPONENTIAL
            # GPU/resource errors need longer waits
            if any(x in error_lower for x in ["gpu", "cuda", "memory"]):
                return RetryStrategy.EXPONENTIAL
            return RetryStrategy.EXPONENTIAL

    # Default: retry with exponential for unknown errors
    return RetryStrategy.EXPONENTIAL


@dataclass
class QueuedJob:
    """A job waiting in the queue."""

    id: UUID
    job_type: JobType
    priority: JobPriority
    handler: Callable[..., Coroutine[Any, Any, Any]]
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    db_job_id: UUID | None = None  # Link to GenerationJob if applicable
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 600  # 10 minutes default
    on_progress: Callable[[float, str], Coroutine[Any, Any, None]] | None = None
    on_complete: Callable[[Any], Coroutine[Any, Any, None]] | None = None
    on_error: Callable[[Exception], Coroutine[Any, Any, None]] | None = None

    def __lt__(self, other: "QueuedJob") -> bool:
        """Compare jobs for priority queue ordering."""
        if self.priority != other.priority:
            return self.priority.value > other.priority.value  # Higher priority first
        return self.created_at < other.created_at  # Earlier jobs first


@dataclass
class JobResult:
    """Result of a completed job."""

    job_id: UUID
    success: bool
    result: Any = None
    error: str | None = None
    duration_seconds: float = 0.0
    retry_count: int = 0


class BackgroundJobQueue:
    """Background job queue with concurrent execution and priority support.

    Features:
    - Priority queue (urgent, high, normal, low)
    - Concurrent execution with configurable limits
    - Automatic retry with exponential backoff
    - Progress tracking and callbacks
    - Graceful shutdown
    - Job cancellation
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        session_factory: Callable[[], AsyncSession] | None = None,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.session_factory = session_factory

        # Job storage
        self._pending: list[QueuedJob] = []  # Priority queue (heapq)
        self._running: dict[UUID, QueuedJob] = {}
        self._completed: dict[UUID, JobResult] = {}

        # Control
        self._running_tasks: dict[UUID, asyncio.Task] = {}
        self._cancelled: set[UUID] = set()
        self._shutdown = False
        self._processor_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # Metrics
        self._total_processed = 0
        self._total_failed = 0
        self._total_retried = 0

    async def start(self) -> None:
        """Start the job processor."""
        if self._processor_task is not None:
            return

        self._shutdown = False
        self._processor_task = asyncio.create_task(self._process_loop())
        logger.info("Background job queue started")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the job processor gracefully."""
        self._shutdown = True

        if self._processor_task:
            try:
                await asyncio.wait_for(self._processor_task, timeout=timeout)
            except TimeoutError:
                self._processor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._processor_task
            self._processor_task = None

        # Cancel running tasks
        for task in self._running_tasks.values():
            task.cancel()

        logger.info("Background job queue stopped")

    async def submit(
        self,
        job_type: JobType,
        handler: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        db_job_id: UUID | None = None,
        timeout_seconds: int = 600,
        max_retries: int = 3,
        on_progress: Callable[[float, str], Coroutine[Any, Any, None]] | None = None,
        on_complete: Callable[[Any], Coroutine[Any, Any, None]] | None = None,
        on_error: Callable[[Exception], Coroutine[Any, Any, None]] | None = None,
        **kwargs,
    ) -> UUID:
        """Submit a job to the queue.

        Args:
            job_type: Type of job for categorization
            handler: Async function to execute
            *args: Positional arguments for handler
            priority: Job priority level
            db_job_id: Optional database job ID for tracking
            timeout_seconds: Maximum execution time
            max_retries: Number of retry attempts
            on_progress: Progress callback (percent, message)
            on_complete: Completion callback (result)
            on_error: Error callback (exception)
            **kwargs: Keyword arguments for handler

        Returns:
            Job ID for tracking
        """
        job = QueuedJob(
            id=uuid4(),
            job_type=job_type,
            priority=priority,
            handler=handler,
            args=args,
            kwargs=kwargs,
            db_job_id=db_job_id,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )

        async with self._lock:
            self._pending.append(job)
            self._pending.sort()  # Maintain priority order

        logger.info(f"Job {job.id} submitted ({job_type.value}, priority={priority.name})")

        # Update database status if linked
        if db_job_id and self.session_factory:
            await self._update_db_job_status(db_job_id, JobStatus.PENDING)

        return job.id

    async def cancel(self, job_id: UUID) -> bool:
        """Cancel a job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if job was cancelled
        """
        async with self._lock:
            # Check pending jobs
            for i, job in enumerate(self._pending):
                if job.id == job_id:
                    self._pending.pop(i)
                    logger.info(f"Job {job_id} cancelled (was pending)")
                    if job.db_job_id and self.session_factory:
                        await self._update_db_job_status(job.db_job_id, JobStatus.CANCELLED)
                    return True

            # Check running jobs
            if job_id in self._running:
                self._cancelled.add(job_id)
                if job_id in self._running_tasks:
                    self._running_tasks[job_id].cancel()
                logger.info(f"Job {job_id} cancellation requested (running)")
                return True

        return False

    async def get_status(self, job_id: UUID) -> dict[str, Any] | None:
        """Get status of a specific job."""
        async with self._lock:
            # Check pending
            for job in self._pending:
                if job.id == job_id:
                    return {
                        "id": str(job_id),
                        "status": "pending",
                        "type": job.job_type.value,
                        "priority": job.priority.name,
                        "created_at": job.created_at.isoformat(),
                        "position": self._pending.index(job) + 1,
                    }

            # Check running
            if job_id in self._running:
                job = self._running[job_id]
                return {
                    "id": str(job_id),
                    "status": "running",
                    "type": job.job_type.value,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                }

            # Check completed
            if job_id in self._completed:
                result = self._completed[job_id]
                return {
                    "id": str(job_id),
                    "status": "completed" if result.success else "failed",
                    "success": result.success,
                    "error": result.error,
                    "duration_seconds": result.duration_seconds,
                }

        return None

    async def get_queue_status(self) -> dict[str, Any]:
        """Get overall queue status."""
        async with self._lock:
            pending_by_type = {}
            for job in self._pending:
                job_type = job.job_type.value
                pending_by_type[job_type] = pending_by_type.get(job_type, 0) + 1

            running_by_type = {}
            for job in self._running.values():
                job_type = job.job_type.value
                running_by_type[job_type] = running_by_type.get(job_type, 0) + 1

            return {
                "pending": len(self._pending),
                "running": len(self._running),
                "completed": len(self._completed),
                "total_processed": self._total_processed,
                "total_failed": self._total_failed,
                "total_retried": self._total_retried,
                "max_concurrent": self.max_concurrent,
                "pending_by_type": pending_by_type,
                "running_by_type": running_by_type,
                "is_running": self._processor_task is not None,
            }

    async def wait_for_job(self, job_id: UUID, timeout: float | None = None) -> JobResult | None:
        """Wait for a job to complete.

        Args:
            job_id: Job ID to wait for
            timeout: Maximum wait time in seconds

        Returns:
            JobResult if completed, None if timeout or not found
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            async with self._lock:
                if job_id in self._completed:
                    return self._completed[job_id]

                # Check if job exists
                is_pending = any(j.id == job_id for j in self._pending)
                is_running = job_id in self._running

                if not is_pending and not is_running and job_id not in self._completed:
                    return None  # Job not found

            # Check timeout
            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    return None

            await asyncio.sleep(0.1)

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while not self._shutdown:
            try:
                await self._process_pending()
            except Exception as e:
                logger.exception(f"Error in job processor: {e}")

            await asyncio.sleep(0.1)

    async def _process_pending(self) -> None:
        """Process pending jobs up to concurrency limit."""
        async with self._lock:
            while len(self._running) < self.max_concurrent and self._pending and not self._shutdown:
                job = self._pending.pop(0)
                self._running[job.id] = job

                # Start job execution
                task = asyncio.create_task(self._execute_job(job))
                self._running_tasks[job.id] = task

    async def _execute_job(self, job: QueuedJob) -> None:
        """Execute a single job with timeout and error handling."""
        job.started_at = datetime.now(UTC)

        logger.info(f"Job {job.id} started ({job.job_type.value})")

        # Update database status
        if job.db_job_id and self.session_factory:
            await self._update_db_job_status(
                job.db_job_id,
                JobStatus.RUNNING,
                started_at=job.started_at,
            )

        result: Any | None = None
        error: str | None = None

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                job.handler(*job.args, **job.kwargs),
                timeout=job.timeout_seconds,
            )

            # Success
            duration = (datetime.now(UTC) - job.started_at).total_seconds()
            JobResult(
                job_id=job.id,
                success=True,
                result=result,
                duration_seconds=duration,
                retry_count=job.retry_count,
            )

            logger.info(f"Job {job.id} completed successfully in {duration:.2f}s")
            self._total_processed += 1

            # Update database
            if job.db_job_id and self.session_factory:
                await self._update_db_job_status(
                    job.db_job_id,
                    JobStatus.COMPLETED,
                    completed_at=datetime.now(UTC),
                )

            # Call completion callback
            if job.on_complete:
                try:
                    await job.on_complete(result)
                except Exception as e:
                    logger.warning(f"Error in job completion callback: {e}")

        except TimeoutError:
            error = f"Job timed out after {job.timeout_seconds}s"
            logger.error(f"Job {job.id} timed out")

            if job.db_job_id and self.session_factory:
                await self._update_db_job_status(
                    job.db_job_id,
                    JobStatus.TIMEOUT,
                    error_message=error,
                )

        except asyncio.CancelledError:
            if job.id in self._cancelled:
                error = "Job cancelled by user"
                logger.info(f"Job {job.id} cancelled")

                if job.db_job_id and self.session_factory:
                    await self._update_db_job_status(
                        job.db_job_id,
                        JobStatus.CANCELLED,
                    )
            else:
                error = "Job cancelled (shutdown)"
            raise

        except Exception as e:
            error = str(e)
            logger.exception(f"Job {job.id} failed: {e}")

            # Retry logic
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                self._total_retried += 1

                # Exponential backoff
                delay = min(30, 2**job.retry_count)
                logger.info(
                    f"Job {job.id} will retry in {delay}s (attempt {job.retry_count}/{job.max_retries})"
                )

                # Re-queue with delay
                async with self._lock:
                    self._pending.append(job)
                    self._pending.sort()

                if job.db_job_id and self.session_factory:
                    await self._update_db_job_status(
                        job.db_job_id,
                        JobStatus.PENDING,
                        retry_count=job.retry_count,
                    )

                # Remove from running and wait before processing
                async with self._lock:
                    self._running.pop(job.id, None)
                    self._running_tasks.pop(job.id, None)

                await asyncio.sleep(delay)
                return

            # Max retries exceeded
            self._total_failed += 1

            if job.db_job_id and self.session_factory:
                await self._update_db_job_status(
                    job.db_job_id,
                    JobStatus.FAILED,
                    error_message=error,
                    completed_at=datetime.now(UTC),
                )

            # Call error callback
            if job.on_error:
                try:
                    await job.on_error(Exception(error))
                except Exception as cb_error:
                    logger.warning(f"Error in job error callback: {cb_error}")

        finally:
            # Clean up
            async with self._lock:
                self._running.pop(job.id, None)
                self._running_tasks.pop(job.id, None)
                self._cancelled.discard(job.id)

                # Store result
                duration = (datetime.now(UTC) - job.started_at).total_seconds()
                self._completed[job.id] = JobResult(
                    job_id=job.id,
                    success=error is None,
                    result=result,
                    error=error,
                    duration_seconds=duration,
                    retry_count=job.retry_count,
                )

                # Limit completed job history
                if len(self._completed) > 1000:
                    oldest = min(
                        self._completed.keys(), key=lambda k: self._completed[k].duration_seconds
                    )
                    del self._completed[oldest]

    async def _update_db_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        """Update job status in database."""
        if not self.session_factory:
            return

        try:
            async with self.session_factory() as session:
                values: dict[str, Any] = {"status": status}

                if started_at:
                    values["started_at"] = started_at
                if completed_at:
                    values["completed_at"] = completed_at
                if error_message:
                    values["error_message"] = error_message
                if retry_count is not None:
                    values["retry_count"] = retry_count

                stmt = update(GenerationJob).where(GenerationJob.id == job_id).values(**values)
                await session.execute(stmt)
                await session.commit()

        except Exception as e:
            logger.warning(f"Failed to update job status in database: {e}")


# Global job queue instance
_job_queue: BackgroundJobQueue | None = None


def get_job_queue() -> BackgroundJobQueue:
    """Get or create the global job queue instance."""
    global _job_queue

    if _job_queue is None:
        settings = get_settings()
        _job_queue = BackgroundJobQueue(
            max_concurrent=settings.max_concurrent_generations,
        )

    return _job_queue


async def init_job_queue(
    session_factory: Callable[[], AsyncSession] | None = None,
) -> BackgroundJobQueue:
    """Initialize and start the global job queue."""
    global _job_queue

    settings = get_settings()
    _job_queue = BackgroundJobQueue(
        max_concurrent=settings.max_concurrent_generations,
        session_factory=session_factory,
    )
    await _job_queue.start()

    return _job_queue


async def shutdown_job_queue() -> None:
    """Shutdown the global job queue."""
    global _job_queue

    if _job_queue:
        await _job_queue.stop()
        _job_queue = None


# Backwards compatibility aliases
JobQueueService = BackgroundJobQueue
