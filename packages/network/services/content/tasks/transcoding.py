"""
Video transcoding tasks for SceneMachine Network.

Handles background processing of uploaded videos:
- Transcoding to multiple quality levels (360p, 480p, 720p, 1080p, 4K)
- Thumbnail generation
- HLS segmentation for adaptive streaming
- Storage upload to R2/S3
"""

import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from typing import Optional
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger

from .celery_app import celery_app

logger = get_task_logger(__name__)


def run_async(coro):
    """Run an async function in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="services.content.tasks.transcoding.transcode_video_task",
    max_retries=3,
    default_retry_delay=60,
)
def transcode_video_task(
    self,
    video_id: str,
    source_path: str,
    target_quality: str,
    output_dir: str,
) -> dict:
    """
    Transcode a video to a specific quality level.

    Args:
        video_id: UUID of the video
        source_path: Path to source video file
        target_quality: Target quality (360p, 480p, 720p, 1080p, 2160p)
        output_dir: Directory to save output

    Returns:
        Dict with transcoding result
    """
    logger.info(f"Starting transcode for video {video_id} to {target_quality}")

    try:
        # Import here to avoid circular imports
        from ..transcoding import transcode_video, TRANSCODE_PROFILES

        # Find the target profile
        profile = next(
            (p for p in TRANSCODE_PROFILES if p.name == target_quality),
            None
        )
        if not profile:
            raise ValueError(f"Unknown quality: {target_quality}")

        # Create output path
        output_path = os.path.join(output_dir, f"{target_quality}.mp4")
        os.makedirs(output_dir, exist_ok=True)

        # Track progress
        def progress_callback(progress: int):
            self.update_state(
                state="PROGRESS",
                meta={"progress": progress, "quality": target_quality}
            )

        # Run async transcoding
        result = run_async(
            transcode_video(
                source_path,
                output_path,
                profile,
                progress_callback=progress_callback,
            )
        )

        logger.info(f"Completed transcode for video {video_id} to {target_quality}")

        return {
            "video_id": video_id,
            "quality": target_quality,
            "output_path": result,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Transcode failed for video {video_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="services.content.tasks.transcoding.generate_thumbnails_task",
    max_retries=3,
)
def generate_thumbnails_task(
    self,
    video_id: str,
    source_path: str,
    output_dir: str,
    count: int = 3,
) -> dict:
    """
    Generate thumbnails from a video.

    Args:
        video_id: UUID of the video
        source_path: Path to source video file
        output_dir: Directory to save thumbnails
        count: Number of thumbnails to generate

    Returns:
        Dict with thumbnail paths
    """
    logger.info(f"Generating {count} thumbnails for video {video_id}")

    try:
        from ..transcoding import generate_thumbnails

        os.makedirs(output_dir, exist_ok=True)

        thumbnails = run_async(
            generate_thumbnails(source_path, output_dir, count=count)
        )

        logger.info(f"Generated {len(thumbnails)} thumbnails for video {video_id}")

        return {
            "video_id": video_id,
            "thumbnails": thumbnails,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Thumbnail generation failed for video {video_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="services.content.tasks.transcoding.create_hls_variants_task",
    max_retries=3,
    time_limit=7200,  # 2 hour limit for HLS creation
)
def create_hls_variants_task(
    self,
    video_id: str,
    source_path: str,
    output_dir: str,
) -> dict:
    """
    Create HLS variants for adaptive streaming.

    Args:
        video_id: UUID of the video
        source_path: Path to source video file
        output_dir: Directory to save HLS files

    Returns:
        Dict with HLS manifest paths
    """
    logger.info(f"Creating HLS variants for video {video_id}")

    try:
        from ..transcoding import transcode_to_hls

        os.makedirs(output_dir, exist_ok=True)

        def progress_callback(profile: str, progress: int):
            self.update_state(
                state="PROGRESS",
                meta={"profile": profile, "progress": progress}
            )

        result = run_async(
            transcode_to_hls(
                source_path,
                output_dir,
                progress_callback=progress_callback,
            )
        )

        logger.info(f"Created HLS variants for video {video_id}")

        return {
            "video_id": video_id,
            "master_playlist": result["master_playlist"],
            "variants": list(result["variants"].keys()),
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"HLS creation failed for video {video_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="services.content.tasks.transcoding.process_video_upload_task",
    max_retries=2,
    time_limit=10800,  # 3 hour limit for full processing
)
def process_video_upload_task(
    self,
    video_id: str,
    source_key: str,
    creator_id: str,
) -> dict:
    """
    Process a newly uploaded video through the full pipeline.

    This is the main entry point that orchestrates:
    1. Download source from storage
    2. Generate thumbnails
    3. Transcode to HLS variants
    4. Upload outputs to storage
    5. Update database with URLs

    Args:
        video_id: UUID of the video
        source_key: Storage key of the uploaded source file
        creator_id: UUID of the creator

    Returns:
        Dict with processing results
    """
    logger.info(f"Starting full video processing for {video_id}")

    # Create temporary work directory
    work_dir = tempfile.mkdtemp(prefix=f"video_{video_id}_")

    try:
        self.update_state(state="PROGRESS", meta={"stage": "downloading", "progress": 0})

        # Import storage and transcoding modules
        from ....shared.storage import get_storage
        from ..transcoding import TranscodingPipeline

        storage = get_storage()
        source_path = os.path.join(work_dir, "source.mp4")

        # Download source file
        run_async(storage.download_file(source_key, source_path))
        self.update_state(state="PROGRESS", meta={"stage": "downloading", "progress": 100})

        # Initialize pipeline
        pipeline = TranscodingPipeline(work_dir)

        def pipeline_progress(stage: str, progress: int):
            self.update_state(
                state="PROGRESS",
                meta={"stage": stage, "progress": progress}
            )

        # Process video
        result = run_async(
            pipeline.process(source_path, video_id, progress_callback=pipeline_progress)
        )

        self.update_state(state="PROGRESS", meta={"stage": "uploading", "progress": 0})

        # Upload outputs to storage
        outputs = {}

        # Upload thumbnails
        for i, thumb_path in enumerate(result.get("thumbnails", [])):
            thumb_key = f"videos/{creator_id}/{video_id}/thumbnails/thumb_{i}.jpg"
            run_async(storage.upload_file(thumb_path, thumb_key))
            outputs[f"thumbnail_{i}"] = thumb_key

        # Upload HLS files
        hls_dir = result.get("hls", {}).get("master_playlist", "")
        if hls_dir and os.path.dirname(hls_dir):
            hls_base_dir = os.path.dirname(hls_dir)
            for root, dirs, files in os.walk(hls_base_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    rel_path = os.path.relpath(local_path, hls_base_dir)
                    storage_key = f"videos/{creator_id}/{video_id}/hls/{rel_path}"
                    run_async(storage.upload_file(local_path, storage_key))

        outputs["hls_master"] = f"videos/{creator_id}/{video_id}/hls/master.m3u8"

        self.update_state(state="PROGRESS", meta={"stage": "uploading", "progress": 100})

        # Update database (would be done via API call in production)
        logger.info(f"Video processing completed for {video_id}")

        return {
            "video_id": video_id,
            "status": "completed",
            "outputs": outputs,
            "source_info": result.get("source_info", {}),
        }

    except Exception as e:
        logger.error(f"Video processing failed for {video_id}: {e}")
        raise self.retry(exc=e)

    finally:
        # Cleanup temporary files
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)


@celery_app.task(name="services.content.tasks.transcoding.cleanup_temp_files_task")
def cleanup_temp_files_task() -> dict:
    """
    Periodic task to clean up old temporary files.

    Runs hourly via Celery Beat.
    """
    import glob
    import time

    temp_dir = tempfile.gettempdir()
    pattern = os.path.join(temp_dir, "video_*")
    max_age_hours = 24

    deleted = 0
    for path in glob.glob(pattern):
        if os.path.isdir(path):
            # Check age
            mtime = os.path.getmtime(path)
            age_hours = (time.time() - mtime) / 3600
            if age_hours > max_age_hours:
                try:
                    shutil.rmtree(path)
                    deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {path}: {e}")

    logger.info(f"Cleaned up {deleted} old temporary directories")
    return {"deleted": deleted}


@celery_app.task(name="services.content.tasks.transcoding.update_video_stats_task")
def update_video_stats_task() -> dict:
    """
    Periodic task to update video statistics.

    Aggregates view counts, watch time, etc.
    Runs every 5 minutes via Celery Beat.
    """
    # This would query Redis for recent events and batch update the database
    logger.info("Updating video statistics")
    return {"status": "completed"}
