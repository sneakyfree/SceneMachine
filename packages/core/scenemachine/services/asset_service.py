"""
Asset Service

Business logic for asset management - CRUD, search, tagging.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models.asset import Asset, AssetStatus, AssetType


class AssetServiceError(Exception):
    """Base exception for asset service errors."""

    def __init__(self, message: str, code: str = "asset_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AssetNotFoundError(AssetServiceError):
    """Raised when asset is not found."""

    def __init__(self, asset_id: UUID):
        super().__init__(
            f"Asset {asset_id} not found",
            code="asset_not_found",
        )


class AssetService:
    """Service for asset management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize asset service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()

    async def create_asset(
        self,
        project_id: UUID,
        filename: str,
        file_path: str,
        asset_type: AssetType,
        file_size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        character_id: Optional[UUID] = None,
        shot_id: Optional[UUID] = None,
        scene_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> Asset:
        """Create a new asset.

        Args:
            project_id: Project this asset belongs to
            filename: Original filename
            file_path: Storage path
            asset_type: Type of asset
            file_size_bytes: File size in bytes
            mime_type: MIME type
            display_name: Display name
            description: Description
            character_id: Optional character association
            shot_id: Optional shot association
            scene_id: Optional scene association
            metadata: Type-specific metadata

        Returns:
            Created Asset object
        """
        # Calculate file hash if file exists
        file_hash = None
        full_path = Path(file_path)
        if full_path.exists():
            file_hash = self._calculate_file_hash(full_path)
            if file_size_bytes is None:
                file_size_bytes = full_path.stat().st_size

        asset = Asset(
            project_id=project_id,
            filename=filename,
            file_path=file_path,
            asset_type=asset_type,
            status=AssetStatus.READY,
            file_size_bytes=file_size_bytes,
            file_hash=file_hash,
            mime_type=mime_type,
            display_name=display_name or filename,
            description=description,
            character_id=character_id,
            shot_id=shot_id,
            scene_id=scene_id,
            asset_metadata=metadata,
        )

        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)

        return asset

    async def get_asset(
        self,
        asset_id: UUID,
        project_id: Optional[UUID] = None,
    ) -> Optional[Asset]:
        """Get asset by ID.

        Args:
            asset_id: Asset UUID
            project_id: Optional project ID for access control

        Returns:
            Asset object or None
        """
        query = select(Asset).where(Asset.id == asset_id)
        if project_id:
            query = query.where(Asset.project_id == project_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_assets(
        self,
        project_id: UUID,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None,
        character_id: Optional[UUID] = None,
        shot_id: Optional[UUID] = None,
        scene_id: Optional[UUID] = None,
        search_query: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Asset], int]:
        """List assets with filtering.

        Args:
            project_id: Project ID
            asset_type: Filter by type
            status: Filter by status
            character_id: Filter by character
            shot_id: Filter by shot
            scene_id: Filter by scene
            search_query: Search in filename and display_name
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (assets list, total count)
        """
        query = select(Asset).where(Asset.project_id == project_id)
        count_query = select(func.count(Asset.id)).where(Asset.project_id == project_id)

        if asset_type:
            query = query.where(Asset.asset_type == asset_type)
            count_query = count_query.where(Asset.asset_type == asset_type)

        if status:
            query = query.where(Asset.status == status)
            count_query = count_query.where(Asset.status == status)

        if character_id:
            query = query.where(Asset.character_id == character_id)
            count_query = count_query.where(Asset.character_id == character_id)

        if shot_id:
            query = query.where(Asset.shot_id == shot_id)
            count_query = count_query.where(Asset.shot_id == shot_id)

        if scene_id:
            query = query.where(Asset.scene_id == scene_id)
            count_query = count_query.where(Asset.scene_id == scene_id)

        if search_query:
            search_term = f"%{search_query}%"
            search_filter = or_(
                Asset.filename.ilike(search_term),
                Asset.display_name.ilike(search_term),
                Asset.description.ilike(search_term),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        assets = list(result.scalars().all())

        return assets, total

    async def update_asset(
        self,
        asset_id: UUID,
        project_id: UUID,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[AssetStatus] = None,
        metadata: Optional[dict] = None,
    ) -> Asset:
        """Update asset.

        Args:
            asset_id: Asset ID
            project_id: Project ID for access control
            display_name: New display name
            description: New description
            status: New status
            metadata: New metadata (merged with existing)

        Returns:
            Updated Asset object

        Raises:
            AssetNotFoundError: If asset not found
        """
        asset = await self.get_asset(asset_id, project_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        if display_name is not None:
            asset.display_name = display_name

        if description is not None:
            asset.description = description

        if status is not None:
            asset.status = status

        if metadata is not None:
            # Merge metadata
            existing = asset.asset_metadata or {}
            existing.update(metadata)
            asset.asset_metadata = existing

        await self.session.commit()
        await self.session.refresh(asset)

        return asset

    async def delete_asset(
        self,
        asset_id: UUID,
        project_id: UUID,
        delete_file: bool = True,
    ) -> bool:
        """Delete asset.

        Args:
            asset_id: Asset ID
            project_id: Project ID for access control
            delete_file: Whether to delete the actual file

        Returns:
            True if deleted

        Raises:
            AssetNotFoundError: If asset not found
        """
        asset = await self.get_asset(asset_id, project_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        # Delete file if requested
        if delete_file and asset.file_path:
            file_path = Path(asset.file_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass  # Log but don't fail

        await self.session.delete(asset)
        await self.session.commit()

        return True

    async def bulk_delete_assets(
        self,
        asset_ids: List[UUID],
        project_id: UUID,
        delete_files: bool = True,
    ) -> int:
        """Delete multiple assets.

        Args:
            asset_ids: List of asset IDs
            project_id: Project ID for access control
            delete_files: Whether to delete actual files

        Returns:
            Number of assets deleted
        """
        deleted_count = 0
        for asset_id in asset_ids:
            try:
                await self.delete_asset(asset_id, project_id, delete_files)
                deleted_count += 1
            except AssetNotFoundError:
                pass  # Skip not found

        return deleted_count

    async def duplicate_asset(
        self,
        asset_id: UUID,
        project_id: UUID,
        new_name: Optional[str] = None,
    ) -> Asset:
        """Duplicate an asset.

        Args:
            asset_id: Asset to duplicate
            project_id: Project ID for access control
            new_name: Optional new display name

        Returns:
            New duplicated Asset

        Raises:
            AssetNotFoundError: If asset not found
        """
        asset = await self.get_asset(asset_id, project_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        # Copy file if exists
        new_file_path = asset.file_path
        if asset.file_path:
            source_path = Path(asset.file_path)
            if source_path.exists():
                new_file_path = str(source_path.parent / f"copy_{source_path.name}")
                shutil.copy2(source_path, new_file_path)

        # Create new asset
        new_asset = await self.create_asset(
            project_id=asset.project_id,
            filename=f"Copy of {asset.filename}",
            file_path=new_file_path,
            asset_type=asset.asset_type,
            file_size_bytes=asset.file_size_bytes,
            mime_type=asset.mime_type,
            display_name=new_name or f"Copy of {asset.display_name}",
            description=asset.description,
            character_id=asset.character_id,
            shot_id=asset.shot_id,
            scene_id=asset.scene_id,
            metadata=asset.asset_metadata,
        )

        return new_asset

    async def move_asset(
        self,
        asset_id: UUID,
        project_id: UUID,
        target_character_id: Optional[UUID] = None,
        target_shot_id: Optional[UUID] = None,
        target_scene_id: Optional[UUID] = None,
    ) -> Asset:
        """Move asset to different association.

        Args:
            asset_id: Asset ID
            project_id: Project ID
            target_character_id: New character association
            target_shot_id: New shot association
            target_scene_id: New scene association

        Returns:
            Updated Asset

        Raises:
            AssetNotFoundError: If asset not found
        """
        asset = await self.get_asset(asset_id, project_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        asset.character_id = target_character_id
        asset.shot_id = target_shot_id
        asset.scene_id = target_scene_id

        await self.session.commit()
        await self.session.refresh(asset)

        return asset

    async def get_asset_stats(self, project_id: UUID) -> dict:
        """Get asset statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Statistics dictionary
        """
        # Count by type
        type_query = select(
            Asset.asset_type, func.count(Asset.id)
        ).where(
            Asset.project_id == project_id
        ).group_by(Asset.asset_type)

        type_result = await self.session.execute(type_query)
        type_counts = {str(row[0].value): row[1] for row in type_result}

        # Count by status
        status_query = select(
            Asset.status, func.count(Asset.id)
        ).where(
            Asset.project_id == project_id
        ).group_by(Asset.status)

        status_result = await self.session.execute(status_query)
        status_counts = {str(row[0].value): row[1] for row in status_result}

        # Total size
        size_query = select(
            func.sum(Asset.file_size_bytes)
        ).where(Asset.project_id == project_id)

        size_result = await self.session.execute(size_query)
        total_size = size_result.scalar() or 0

        return {
            "by_type": type_counts,
            "by_status": status_counts,
            "total_size_bytes": total_size,
            "total_count": sum(type_counts.values()),
        }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
