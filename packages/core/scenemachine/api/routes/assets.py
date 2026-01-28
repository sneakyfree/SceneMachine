"""
Asset API Routes

REST endpoints for asset management.
"""

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.dependencies import CurrentActiveUser
from scenemachine.database import get_session
from scenemachine.models.asset import AssetStatus, AssetType
from scenemachine.services.asset_service import (
    AssetNotFoundError,
    AssetService,
    AssetServiceError,
)

router = APIRouter(prefix="/assets", tags=["assets"])


# Schemas
class AssetResponse(BaseModel):
    """Asset response model."""

    id: UUID
    project_id: UUID
    character_id: Optional[UUID] = None
    shot_id: Optional[UUID] = None
    scene_id: Optional[UUID] = None
    asset_type: str
    status: str
    filename: str
    file_path: str
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    asset_metadata: Optional[dict] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Paginated asset list response."""

    items: List[AssetResponse]
    total: int
    offset: int
    limit: int


class AssetCreateRequest(BaseModel):
    """Request to create an asset."""

    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=512)
    asset_type: AssetType
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    character_id: Optional[UUID] = None
    shot_id: Optional[UUID] = None
    scene_id: Optional[UUID] = None
    metadata: Optional[dict] = None


class AssetUpdateRequest(BaseModel):
    """Request to update an asset."""

    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AssetStatus] = None
    metadata: Optional[dict] = None


class BulkDeleteRequest(BaseModel):
    """Request to delete multiple assets."""

    asset_ids: List[UUID]
    delete_files: bool = True


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete."""

    deleted_count: int


class AssetStatsResponse(BaseModel):
    """Asset statistics response."""

    by_type: dict
    by_status: dict
    total_size_bytes: int
    total_count: int


class MoveAssetRequest(BaseModel):
    """Request to move an asset."""

    target_character_id: Optional[UUID] = None
    target_shot_id: Optional[UUID] = None
    target_scene_id: Optional[UUID] = None


# Dependency
def get_asset_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetService:
    """Get asset service instance."""
    return AssetService(session)


# Routes
@router.get(
    "/projects/{project_id}/assets",
    response_model=AssetListResponse,
    summary="List assets in a project",
)
async def list_assets(
    project_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
    asset_type: Optional[AssetType] = None,
    status: Optional[AssetStatus] = None,
    character_id: Optional[UUID] = None,
    shot_id: Optional[UUID] = None,
    scene_id: Optional[UUID] = None,
    search: Optional[str] = Query(None, max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> AssetListResponse:
    """List assets with filtering and pagination."""
    assets, total = await service.list_assets(
        project_id=project_id,
        asset_type=asset_type,
        status=status,
        character_id=character_id,
        shot_id=shot_id,
        scene_id=scene_id,
        search_query=search,
        offset=offset,
        limit=limit,
    )

    return AssetListResponse(
        items=[AssetResponse.model_validate(a) for a in assets],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/projects/{project_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset",
)
async def create_asset(
    project_id: UUID,
    data: AssetCreateRequest,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Create a new asset in a project."""
    asset = await service.create_asset(
        project_id=project_id,
        filename=data.filename,
        file_path=data.file_path,
        asset_type=data.asset_type,
        file_size_bytes=data.file_size_bytes,
        mime_type=data.mime_type,
        display_name=data.display_name,
        description=data.description,
        character_id=data.character_id,
        shot_id=data.shot_id,
        scene_id=data.scene_id,
        metadata=data.metadata,
    )

    return AssetResponse.model_validate(asset)


@router.get(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    summary="Get asset by ID",
)
async def get_asset(
    asset_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Get a single asset by ID."""
    asset = await service.get_asset(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    return AssetResponse.model_validate(asset)


@router.patch(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    summary="Update an asset",
)
async def update_asset(
    asset_id: UUID,
    data: AssetUpdateRequest,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
    project_id: Optional[UUID] = None,
) -> AssetResponse:
    """Update asset properties."""
    try:
        # Get asset first to find project_id if not provided
        asset = await service.get_asset(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        updated = await service.update_asset(
            asset_id=asset_id,
            project_id=asset.project_id,
            display_name=data.display_name,
            description=data.description,
            status=data.status,
            metadata=data.metadata,
        )
        return AssetResponse.model_validate(updated)
    except AssetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an asset",
)
async def delete_asset(
    asset_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
    delete_file: bool = True,
) -> None:
    """Delete an asset and optionally its file."""
    try:
        asset = await service.get_asset(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        await service.delete_asset(asset_id, asset.project_id, delete_file)
    except AssetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )


@router.post(
    "/projects/{project_id}/assets/bulk-delete",
    response_model=BulkDeleteResponse,
    summary="Delete multiple assets",
)
async def bulk_delete_assets(
    project_id: UUID,
    data: BulkDeleteRequest,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> BulkDeleteResponse:
    """Delete multiple assets at once."""
    deleted = await service.bulk_delete_assets(
        asset_ids=data.asset_ids,
        project_id=project_id,
        delete_files=data.delete_files,
    )
    return BulkDeleteResponse(deleted_count=deleted)


@router.post(
    "/assets/{asset_id}/duplicate",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate an asset",
)
async def duplicate_asset(
    asset_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
    new_name: Optional[str] = None,
) -> AssetResponse:
    """Create a copy of an asset."""
    try:
        asset = await service.get_asset(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        duplicate = await service.duplicate_asset(asset_id, asset.project_id, new_name)
        return AssetResponse.model_validate(duplicate)
    except AssetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )


@router.post(
    "/assets/{asset_id}/move",
    response_model=AssetResponse,
    summary="Move asset to different association",
)
async def move_asset(
    asset_id: UUID,
    data: MoveAssetRequest,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Move asset to different character/shot/scene."""
    try:
        asset = await service.get_asset(asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        moved = await service.move_asset(
            asset_id=asset_id,
            project_id=asset.project_id,
            target_character_id=data.target_character_id,
            target_shot_id=data.target_shot_id,
            target_scene_id=data.target_scene_id,
        )
        return AssetResponse.model_validate(moved)
    except AssetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )


@router.get(
    "/projects/{project_id}/assets/stats",
    response_model=AssetStatsResponse,
    summary="Get asset statistics",
)
async def get_asset_stats(
    project_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetStatsResponse:
    """Get asset statistics for a project."""
    stats = await service.get_asset_stats(project_id)
    return AssetStatsResponse(**stats)
