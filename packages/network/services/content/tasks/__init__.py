"""
Celery tasks for SceneMachine Network content processing.

This module provides background task processing for:
- Video transcoding to multiple quality levels
- Thumbnail generation
- HLS segmentation
- Notification dispatch
"""

from .celery_app import celery_app
from .transcoding import (
    transcode_video_task,
    generate_thumbnails_task,
    create_hls_variants_task,
    process_video_upload_task,
)
from .notifications import (
    send_email_notification_task,
    send_push_notification_task,
)

__all__ = [
    "celery_app",
    "transcode_video_task",
    "generate_thumbnails_task",
    "create_hls_variants_task",
    "process_video_upload_task",
    "send_email_notification_task",
    "send_push_notification_task",
]
