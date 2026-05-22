"""Archive API endpoints for project import/export."""

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.config import get_settings
from scenemachine.services.project_archive import ProjectArchiveService

router = APIRouter()


# Request Models
class ExportRequest(BaseModel):
    """Request to export a project."""

    project_id: UUID
    include_assets: bool = True
    include_outputs: bool = True
    include_generated_videos: bool = False


class ImportOptions(BaseModel):
    """Options for importing a project."""

    new_name: str | None = None
    import_assets: bool = True


# Routes
@router.post("/export")
async def export_project(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Export a project to a ZIP archive.

    Creates a .smproject archive containing project data, assets, and optionally generated videos.
    """
    service = ProjectArchiveService(db)
    result = await service.export_project(
        project_id=request.project_id,
        include_assets=request.include_assets,
        include_outputs=request.include_outputs,
        include_generated_videos=request.include_generated_videos,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    return {
        "success": True,
        "archivePath": result.archive_path,
        "fileSizeBytes": result.file_size_bytes,
        "manifest": {
            "version": result.manifest.version if result.manifest else None,
            "createdAt": result.manifest.created_at if result.manifest else None,
            "projectId": result.manifest.project_id if result.manifest else None,
            "projectName": result.manifest.project_name if result.manifest else None,
            "includesAssets": result.manifest.includes_assets if result.manifest else None,
            "includesOutputs": result.manifest.includes_outputs if result.manifest else None,
            "fileCount": result.manifest.file_count if result.manifest else None,
            "totalSizeBytes": result.manifest.total_size_bytes if result.manifest else None,
        } if result.manifest else None,
    }


@router.post("/export/{project_id}/download")
async def export_and_download(
    project_id: UUID,
    include_assets: bool = Query(True),
    include_outputs: bool = Query(True),
    include_generated_videos: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Export a project and download the archive directly."""
    service = ProjectArchiveService(db)
    result = await service.export_project(
        project_id=project_id,
        include_assets=include_assets,
        include_outputs=include_outputs,
        include_generated_videos=include_generated_videos,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    archive_path = Path(result.archive_path)
    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export file not found",
        )

    return FileResponse(
        path=archive_path,
        filename=archive_path.name,
        media_type="application/zip",
    )


@router.post("/import")
async def import_project(
    file: UploadFile = File(...),
    new_name: str | None = Query(None),
    import_assets: bool = Query(True),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import a project from a ZIP archive.

    Accepts a .smproject file and imports the project data.
    """
    if not file.filename or not file.filename.endswith(".smproject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Expected .smproject file",
        )

    settings = get_settings()
    temp_dir = settings.data_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    temp_path = temp_dir / f"import_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        service = ProjectArchiveService(db)
        result = await service.import_project(
            archive_path=temp_path,
            new_name=new_name,
            import_assets=import_assets,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error,
            )

        return {
            "success": True,
            "projectId": result.project_id,
            "projectName": result.project_name,
            "scenesImported": result.scenes_imported,
            "shotsImported": result.shots_imported,
            "charactersImported": result.characters_imported,
            "assetsImported": result.assets_imported,
            "warnings": result.warnings,
        }

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("/info")
async def get_archive_info(
    path: str = Query(..., description="Path to archive file"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get information about an archive without importing.

    Reads the manifest from a .smproject file.
    """
    archive_path = Path(path)

    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive file not found",
        )

    service = ProjectArchiveService(db)
    manifest = await service.get_archive_info(archive_path)

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted archive",
        )

    return {
        "version": manifest.version,
        "createdAt": manifest.created_at,
        "projectId": manifest.project_id,
        "projectName": manifest.project_name,
        "includesAssets": manifest.includes_assets,
        "includesOutputs": manifest.includes_outputs,
        "fileCount": manifest.file_count,
        "totalSizeBytes": manifest.total_size_bytes,
    }


@router.get("/list")
async def list_exports(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all exported archives."""
    service = ProjectArchiveService(db)
    archives = await service.list_exports()

    return [
        {
            "path": archive["path"],
            "filename": archive["filename"],
            "sizeBytes": archive["size_bytes"],
            "createdAt": archive["created_at"],
            "manifest": {
                "version": archive["manifest"]["version"],
                "projectId": archive["manifest"]["project_id"],
                "projectName": archive["manifest"]["project_name"],
            } if archive["manifest"] else None,
        }
        for archive in archives
    ]


@router.delete("/export")
async def delete_export(
    path: str = Query(..., description="Path to archive file"),
) -> dict[str, Any]:
    """Delete an exported archive file."""
    archive_path = Path(path)

    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive file not found",
        )

    # Verify it's a .smproject file in the exports directory
    settings = get_settings()
    exports_dir = settings.data_dir / "exports"

    try:
        archive_path.relative_to(exports_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete files outside exports directory",
        )

    if not archive_path.suffix == ".smproject":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete .smproject files",
        )

    archive_path.unlink()

    return {"success": True, "message": f"Deleted {archive_path.name}"}


@router.get("/download/{filename}")
async def download_export(
    filename: str,
) -> FileResponse:
    """Download an exported archive by filename."""
    settings = get_settings()
    exports_dir = settings.data_dir / "exports"
    archive_path = exports_dir / filename

    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive file not found",
        )

    if not archive_path.suffix == ".smproject":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type",
        )

    return FileResponse(
        path=archive_path,
        filename=filename,
        media_type="application/zip",
    )
