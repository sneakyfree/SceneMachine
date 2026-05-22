"""Background queue worker for processing generation jobs.

This worker continuously polls for pending jobs and processes them
using the configured generation providers.
"""

import asyncio
import logging
import signal
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from scenemachine.config import get_settings
from scenemachine.database import get_db_manager
from scenemachine.services.generation import GenerationService

logger = logging.getLogger(__name__)


@dataclass
class WorkerStats:
    """Statistics for the queue worker."""

    started_at: datetime
    jobs_processed: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    current_job_id: str | None = None
    last_job_completed_at: datetime | None = None
    is_running: bool = False
    is_paused: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        uptime = (datetime.now(UTC) - self.started_at).total_seconds()
        return {
            "started_at": self.started_at.isoformat(),
            "uptime_seconds": uptime,
            "jobs_processed": self.jobs_processed,
            "jobs_succeeded": self.jobs_succeeded,
            "jobs_failed": self.jobs_failed,
            "success_rate": (
                self.jobs_succeeded / self.jobs_processed
                if self.jobs_processed > 0
                else 0.0
            ),
            "current_job_id": self.current_job_id,
            "last_job_completed_at": (
                self.last_job_completed_at.isoformat()
                if self.last_job_completed_at
                else None
            ),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
        }


class QueueWorker:
    """Background worker for processing generation jobs.

    Features:
    - Continuous polling for pending jobs
    - Configurable concurrency
    - Graceful shutdown
    - Progress tracking
    - Error handling with retries
    - Pause/resume support
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        poll_interval: float = 2.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize queue worker.

        Args:
            max_concurrent: Maximum concurrent jobs to process
            poll_interval: Seconds between polling for new jobs
            max_retries: Maximum retry attempts for failed jobs
        """
        self.max_concurrent = max_concurrent
        self.poll_interval = poll_interval
        self.max_retries = max_retries

        self._running = False
        self._paused = False
        self._shutdown_event = asyncio.Event()
        self._active_tasks: dict[UUID, asyncio.Task] = {}
        self._stats = WorkerStats(started_at=datetime.now(UTC))
        self._on_job_complete: Callable | None = None
        self._on_job_failed: Callable | None = None

    @property
    def stats(self) -> WorkerStats:
        """Get worker statistics."""
        self._stats.is_running = self._running
        self._stats.is_paused = self._paused
        return self._stats

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @property
    def active_job_count(self) -> int:
        """Get number of actively processing jobs."""
        return len(self._active_tasks)

    def set_callbacks(
        self,
        on_complete: Callable | None = None,
        on_failed: Callable | None = None,
    ) -> None:
        """Set callback functions for job events.

        Args:
            on_complete: Called when a job completes successfully
            on_failed: Called when a job fails
        """
        self._on_job_complete = on_complete
        self._on_job_failed = on_failed

    async def start(self) -> None:
        """Start the queue worker.

        This method runs indefinitely, processing jobs from the queue.
        Call stop() to shut down gracefully.
        """
        if self._running:
            logger.warning("Queue worker is already running")
            return

        self._running = True
        self._stats = WorkerStats(started_at=datetime.now(UTC))
        self._stats.is_running = True
        self._shutdown_event.clear()

        logger.info(
            f"Queue worker started (max_concurrent={self.max_concurrent}, "
            f"poll_interval={self.poll_interval}s)"
        )

        try:
            await self._run_loop()
        except asyncio.CancelledError:
            logger.info("Queue worker cancelled")
        finally:
            await self._cleanup()

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the queue worker gracefully.

        Args:
            timeout: Maximum seconds to wait for active jobs to complete
        """
        if not self._running:
            return

        logger.info("Stopping queue worker...")
        self._running = False
        self._shutdown_event.set()

        # Wait for active tasks with timeout
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active jobs to complete...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks.values(), return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(f"Timeout waiting for jobs, cancelling {len(self._active_tasks)} tasks")
                for task in self._active_tasks.values():
                    task.cancel()

        logger.info("Queue worker stopped")

    def pause(self) -> None:
        """Pause job processing (active jobs continue)."""
        self._paused = True
        logger.info("Queue worker paused")

    def resume(self) -> None:
        """Resume job processing."""
        self._paused = False
        logger.info("Queue worker resumed")

    async def _run_loop(self) -> None:
        """Main processing loop."""
        get_settings()

        while self._running:
            try:
                # Check for shutdown
                if self._shutdown_event.is_set():
                    break

                # Skip if paused
                if self._paused:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Check if we have capacity
                if len(self._active_tasks) >= self.max_concurrent:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Get pending jobs
                slots_available = self.max_concurrent - len(self._active_tasks)
                jobs = await self._get_pending_jobs(slots_available)

                if not jobs:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Start processing jobs
                for job in jobs:
                    if len(self._active_tasks) >= self.max_concurrent:
                        break

                    task = asyncio.create_task(self._process_job(job.id))
                    self._active_tasks[job.id] = task

                    # Clean up completed tasks
                    self._cleanup_completed_tasks()

            except Exception as e:
                logger.exception(f"Error in queue worker loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _get_pending_jobs(self, limit: int):
        """Get pending jobs from the database."""
        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = GenerationService(session)
            return await service.get_pending_jobs(limit)

    async def _process_job(self, job_id: UUID) -> None:
        """Process a single job.

        Args:
            job_id: Job UUID to process
        """
        self._stats.current_job_id = str(job_id)
        logger.info(f"Processing job {job_id}")

        try:
            db_manager = get_db_manager()
            async with db_manager.session() as session:
                service = GenerationService(session)

                # Process the job
                result = await service.process_job(job_id)

                self._stats.jobs_processed += 1
                self._stats.last_job_completed_at = datetime.now(UTC)

                if result.success:
                    self._stats.jobs_succeeded += 1
                    logger.info(f"Job {job_id} completed successfully")

                    if self._on_job_complete:
                        try:
                            await self._on_job_complete(job_id, result)
                        except Exception as e:
                            logger.error(f"Error in job complete callback: {e}")
                else:
                    self._stats.jobs_failed += 1
                    logger.warning(
                        f"Job {job_id} failed: {result.error_message}"
                    )

                    if self._on_job_failed:
                        try:
                            await self._on_job_failed(job_id, result)
                        except Exception as e:
                            logger.error(f"Error in job failed callback: {e}")

        except Exception as e:
            self._stats.jobs_failed += 1
            logger.exception(f"Exception processing job {job_id}: {e}")

            if self._on_job_failed:
                try:
                    from scenemachine.services.generation import GenerationResult
                    await self._on_job_failed(
                        job_id,
                        GenerationResult(
                            success=False,
                            error_message=str(e),
                            error_code="WORKER_EXCEPTION",
                        ),
                    )
                except Exception as callback_error:
                    logger.error(f"Error in job failed callback: {callback_error}")

        finally:
            self._stats.current_job_id = None
            # Remove from active tasks
            self._active_tasks.pop(job_id, None)

    def _cleanup_completed_tasks(self) -> None:
        """Remove completed tasks from active list."""
        completed = [
            job_id
            for job_id, task in self._active_tasks.items()
            if task.done()
        ]
        for job_id in completed:
            del self._active_tasks[job_id]

    async def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        self._running = False
        self._stats.is_running = False
        self._active_tasks.clear()


# Global worker instance
_worker: QueueWorker | None = None


def get_queue_worker() -> QueueWorker:
    """Get the global queue worker instance."""
    global _worker
    if _worker is None:
        settings = get_settings()
        _worker = QueueWorker(
            max_concurrent=settings.max_concurrent_generations,
            poll_interval=2.0,
        )
    return _worker


async def start_queue_worker() -> None:
    """Start the global queue worker."""
    worker = get_queue_worker()
    await worker.start()


async def stop_queue_worker() -> None:
    """Stop the global queue worker."""
    global _worker
    if _worker:
        await _worker.stop()


@asynccontextmanager
async def managed_queue_worker():
    """Context manager for running the queue worker.

    Usage:
        async with managed_queue_worker():
            # Worker is running
            await some_async_operation()
        # Worker is stopped
    """
    worker = get_queue_worker()
    task = asyncio.create_task(worker.start())

    try:
        yield worker
    finally:
        await worker.stop()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


# CLI entry point
async def run_worker_cli() -> None:
    """Run the queue worker from command line."""

    settings = get_settings()
    settings.configure_logging()

    logger.info("Starting SceneMachine Queue Worker")

    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize()

    worker = get_queue_worker()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def handle_signal(sig) -> None:
        logger.info(f"Received signal {sig}")
        asyncio.create_task(worker.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await db_manager.close()
        logger.info("Queue worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_worker_cli())
