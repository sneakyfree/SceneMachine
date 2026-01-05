"""Settings API endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.services.settings import SettingsService

router = APIRouter()


# Request Models
class UpdateSettingsRequest(BaseModel):
    """Request to update settings."""

    llm_provider: Optional[str] = None
    video_provider: Optional[str] = None
    max_concurrent_generations: Optional[int] = None
    generation_timeout_seconds: Optional[int] = None
    default_video_resolution: Optional[str] = None
    default_video_fps: Optional[int] = None
    theme_mode: Optional[str] = None
    auto_save_enabled: Optional[bool] = None
    show_advanced_options: Optional[bool] = None
    auto_cleanup_temp_files: Optional[bool] = None
    max_cache_size_gb: Optional[int] = None
    default_export_format: Optional[str] = None
    default_export_quality: Optional[str] = None
    # Accessibility settings
    font_size_scale: Optional[str] = None
    high_contrast_enabled: Optional[bool] = None
    reduce_motion_enabled: Optional[bool] = None
    large_click_targets_enabled: Optional[bool] = None
    additional_settings: Optional[Dict[str, Any]] = None


class SetApiKeyRequest(BaseModel):
    """Request to set an API key."""

    provider: str
    api_key: str


class ImportSettingsRequest(BaseModel):
    """Request to import settings."""

    settings: Dict[str, Any]


# Routes
@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get current user settings."""
    service = SettingsService(db)
    settings = await service.get_settings()

    return settings.to_dict(include_keys=False)


@router.patch("")
async def update_settings(
    request: UpdateSettingsRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update user settings."""
    service = SettingsService(db)

    try:
        settings = await service.update_settings(
            llm_provider=request.llm_provider,
            video_provider=request.video_provider,
            max_concurrent_generations=request.max_concurrent_generations,
            generation_timeout_seconds=request.generation_timeout_seconds,
            default_video_resolution=request.default_video_resolution,
            default_video_fps=request.default_video_fps,
            theme_mode=request.theme_mode,
            auto_save_enabled=request.auto_save_enabled,
            show_advanced_options=request.show_advanced_options,
            auto_cleanup_temp_files=request.auto_cleanup_temp_files,
            max_cache_size_gb=request.max_cache_size_gb,
            default_export_format=request.default_export_format,
            default_export_quality=request.default_export_quality,
            # Accessibility settings
            font_size_scale=request.font_size_scale,
            high_contrast_enabled=request.high_contrast_enabled,
            reduce_motion_enabled=request.reduce_motion_enabled,
            large_click_targets_enabled=request.large_click_targets_enabled,
            additional_settings=request.additional_settings,
        )

        return settings.to_dict(include_keys=False)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/api-keys")
async def set_api_key(
    request: SetApiKeyRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Set API key for a provider."""
    service = SettingsService(db)

    try:
        await service.set_api_key(request.provider, request.api_key)
        return {"success": True, "provider": request.provider}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/api-keys/{provider}")
async def remove_api_key(
    provider: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Remove API key for a provider."""
    service = SettingsService(db)

    try:
        await service.remove_api_key(provider)
        return {"success": True, "provider": provider}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/api-keys/{provider}/validate")
async def validate_api_key(
    provider: str,
    api_key: Optional[str] = Query(None, description="API key to test (uses stored if not provided)"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Validate an API key by testing the provider."""
    service = SettingsService(db)
    status_result = await service.validate_api_key(provider, api_key)

    return {
        "provider": status_result.provider,
        "name": status_result.name,
        "available": status_result.available,
        "configured": status_result.configured,
        "message": status_result.message,
        "latencyMs": status_result.latency_ms,
    }


@router.get("/providers/status")
async def check_all_providers(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Check status of all configured providers."""
    service = SettingsService(db)
    statuses = await service.check_all_providers()

    return [
        {
            "provider": s.provider,
            "name": s.name,
            "available": s.available,
            "configured": s.configured,
            "message": s.message,
            "latencyMs": s.latency_ms,
        }
        for s in statuses
    ]


@router.get("/providers/llm")
async def get_llm_providers(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get list of available LLM providers."""
    service = SettingsService(db)
    return await service.get_available_llm_providers()


@router.get("/providers/video")
async def get_video_providers(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get list of available video generation providers."""
    service = SettingsService(db)
    return await service.get_available_video_providers()


@router.get("/themes")
async def get_themes(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, str]]:
    """Get available theme options."""
    service = SettingsService(db)
    return await service.get_theme_options()


@router.get("/storage")
async def get_storage_stats(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get storage statistics."""
    service = SettingsService(db)
    stats = await service.get_storage_stats()

    return {
        "dataDir": stats.data_dir,
        "uploadDir": stats.upload_dir,
        "outputDir": stats.output_dir,
        "cacheDir": stats.cache_dir,
        "totalSizeBytes": stats.total_size_bytes,
        "uploadSizeBytes": stats.upload_size_bytes,
        "outputSizeBytes": stats.output_size_bytes,
        "cacheSizeBytes": stats.cache_size_bytes,
        "tempFilesCount": stats.temp_files_count,
        # Human readable sizes
        "totalSize": _format_size(stats.total_size_bytes),
        "uploadSize": _format_size(stats.upload_size_bytes),
        "outputSize": _format_size(stats.output_size_bytes),
        "cacheSize": _format_size(stats.cache_size_bytes),
    }


@router.post("/storage/clear-cache")
async def clear_cache(
    cache_type: str = Query("all", regex="^(model|temp|output|all)$"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Clear cached files.

    Args:
        cache_type: Type of cache to clear (model, temp, output, all)
    """
    service = SettingsService(db)
    result = await service.clear_cache(cache_type)

    return {
        "success": True,
        "modelCacheCleared": result["model_cache"],
        "tempFilesCleared": result["temp_files"],
        "bytesFreed": result["bytes_freed"],
        "bytesFreedDisplay": _format_size(result["bytes_freed"]),
    }


@router.get("/export")
async def export_settings(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Export settings for backup (excluding API keys)."""
    service = SettingsService(db)
    return await service.export_settings()


@router.post("/import")
async def import_settings(
    request: ImportSettingsRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Import settings from backup."""
    service = SettingsService(db)

    try:
        settings = await service.import_settings(request.settings)
        return {
            "success": True,
            "settings": settings.to_dict(include_keys=False),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
