"""
Celery application configuration for SceneMachine Network.

Configures the Celery app with Redis as broker and result backend.
"""

import os
from celery import Celery

# Get broker URL from environment
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Create Celery app
celery_app = Celery(
    "scenemachine_network",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "services.content.tasks.transcoding",
        "services.content.tasks.notifications",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "services.content.tasks.transcoding.*": {"queue": "transcoding"},
        "services.content.tasks.notifications.*": {"queue": "notifications"},
    },

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 min soft limit (gives time to cleanup)

    # Worker settings
    worker_prefetch_multiplier=1,  # Don't prefetch more than 1 task
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory cleanup)

    # Result settings
    result_expires=86400,  # Results expire after 24 hours

    # Retry settings
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,

    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-temp-files": {
            "task": "services.content.tasks.transcoding.cleanup_temp_files_task",
            "schedule": 3600.0,  # Every hour
        },
        "update-video-stats": {
            "task": "services.content.tasks.transcoding.update_video_stats_task",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)


# Optional: Set concurrency based on CPU cores for transcoding
def get_transcoding_concurrency() -> int:
    """Get optimal concurrency for transcoding tasks."""
    import multiprocessing
    # Use half of CPU cores for transcoding (leave room for other processes)
    return max(1, multiprocessing.cpu_count() // 2)
