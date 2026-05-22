"""Watermark management API routes."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from scenemachine.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class WatermarkInfo(BaseModel):
    """Information about a watermark file."""

    id: str
    filename: str
    path: str
    size_bytes: int
    created_at: str
    is_default: bool = False


class WatermarkListResponse(BaseModel):
    """Response for listing watermarks."""

    watermarks: list[WatermarkInfo]
    total_count: int


class WatermarkUploadResponse(BaseModel):
    """Response for watermark upload."""

    success: bool
    watermark: WatermarkInfo | None = None
    error: str | None = None


def get_watermarks_dir() -> Path:
    """Get the watermarks directory, creating it if needed."""
    settings = get_settings()
    watermarks_dir = Path(settings.data_dir).expanduser() / "assets" / "watermarks"
    watermarks_dir.mkdir(parents=True, exist_ok=True)
    return watermarks_dir


def get_default_watermarks_dir() -> Path:
    """Get the built-in default watermarks directory."""
    # Default watermarks shipped with the app
    package_dir = Path(__file__).parent.parent.parent
    return package_dir / "assets" / "watermarks"


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.get("/watermarks", response_model=WatermarkListResponse)
async def list_watermarks() -> WatermarkListResponse:
    """List all available watermarks.

    Returns both user-uploaded watermarks and built-in default watermarks.
    """
    watermarks: list[WatermarkInfo] = []

    # Get user watermarks
    user_dir = get_watermarks_dir()
    if user_dir.exists():
        for file in user_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
                stat = file.stat()
                watermarks.append(
                    WatermarkInfo(
                        id=file.stem,
                        filename=file.name,
                        path=str(file),
                        size_bytes=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        is_default=False,
                    )
                )

    # Get built-in default watermarks
    default_dir = get_default_watermarks_dir()
    if default_dir.exists():
        for file in default_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
                stat = file.stat()
                watermarks.append(
                    WatermarkInfo(
                        id=f"default_{file.stem}",
                        filename=file.name,
                        path=str(file),
                        size_bytes=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        is_default=True,
                    )
                )

    # Sort by created_at descending (newest first), with defaults at the end
    watermarks.sort(key=lambda w: (w.is_default, w.created_at), reverse=True)

    return WatermarkListResponse(
        watermarks=watermarks,
        total_count=len(watermarks),
    )


@router.post("/watermarks/upload", response_model=WatermarkUploadResponse)
async def upload_watermark(
    file: UploadFile = File(...),
) -> WatermarkUploadResponse:
    """Upload a new watermark image.

    Supported formats: PNG, JPG, JPEG, WebP, GIF
    Max size: 5MB
    """
    # Validate file extension
    if not file.filename:
        return WatermarkUploadResponse(
            success=False,
            error="No filename provided",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return WatermarkUploadResponse(
            success=False,
            error=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return WatermarkUploadResponse(
            success=False,
            error=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    # Generate unique filename
    watermark_id = str(uuid4())[:8]
    safe_name = "".join(c for c in Path(file.filename).stem if c.isalnum() or c in "-_")[:32]
    filename = f"{safe_name}_{watermark_id}{ext}"

    # Save file
    watermarks_dir = get_watermarks_dir()
    file_path = watermarks_dir / filename

    try:
        with open(file_path, "wb") as f:
            f.write(content)

        stat = file_path.stat()
        watermark = WatermarkInfo(
            id=file_path.stem,
            filename=filename,
            path=str(file_path),
            size_bytes=stat.st_size,
            created_at=datetime.now().isoformat(),
            is_default=False,
        )

        logger.info(f"Uploaded watermark: {filename}")

        return WatermarkUploadResponse(
            success=True,
            watermark=watermark,
        )

    except Exception as e:
        logger.error(f"Failed to upload watermark: {e}")
        # Clean up on failure
        if file_path.exists():
            file_path.unlink()
        return WatermarkUploadResponse(
            success=False,
            error=f"Failed to save watermark: {str(e)}",
        )


@router.delete("/watermarks/{watermark_id}")
async def delete_watermark(watermark_id: str) -> dict[str, Any]:
    """Delete a user-uploaded watermark.

    Cannot delete built-in default watermarks.
    """
    # Prevent deletion of default watermarks
    if watermark_id.startswith("default_"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete built-in default watermarks",
        )

    # Find the watermark file
    watermarks_dir = get_watermarks_dir()
    matching_files = list(watermarks_dir.glob(f"{watermark_id}.*"))

    if not matching_files:
        # Try to match by stem (filename without extension)
        for file in watermarks_dir.iterdir():
            if file.is_file() and file.stem == watermark_id:
                matching_files.append(file)
                break

    if not matching_files:
        raise HTTPException(
            status_code=404,
            detail=f"Watermark '{watermark_id}' not found",
        )

    try:
        for file in matching_files:
            file.unlink()
            logger.info(f"Deleted watermark: {file.name}")

        return {"success": True, "message": f"Watermark '{watermark_id}' deleted"}

    except Exception as e:
        logger.error(f"Failed to delete watermark: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete watermark: {str(e)}",
        )


@router.get("/watermarks/{watermark_id}")
async def get_watermark(watermark_id: str) -> WatermarkInfo:
    """Get information about a specific watermark."""
    # Check user watermarks
    watermarks_dir = get_watermarks_dir()
    for file in watermarks_dir.iterdir():
        if file.is_file() and file.stem == watermark_id:
            stat = file.stat()
            return WatermarkInfo(
                id=file.stem,
                filename=file.name,
                path=str(file),
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                is_default=False,
            )

    # Check default watermarks
    if watermark_id.startswith("default_"):
        actual_id = watermark_id.replace("default_", "", 1)
        default_dir = get_default_watermarks_dir()
        if default_dir.exists():
            for file in default_dir.iterdir():
                if file.is_file() and file.stem == actual_id:
                    stat = file.stat()
                    return WatermarkInfo(
                        id=watermark_id,
                        filename=file.name,
                        path=str(file),
                        size_bytes=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        is_default=True,
                    )

    raise HTTPException(
        status_code=404,
        detail=f"Watermark '{watermark_id}' not found",
    )
