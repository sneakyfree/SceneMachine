"""
Snapshots API Routes - Immutable audit trail.

Provides endpoints for:
- Creating project snapshots
- Listing snapshots
- Comparing snapshots (delta reports)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.services.snapshots import SnapshotService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/snapshots", tags=["snapshots"])


class CreateSnapshotRequest(BaseModel):
    label: str | None = None
    description: str | None = None


class SnapshotResponse(BaseModel):
    id: str
    label: str
    created_at: str
    scene_count: int
    character_count: int
    shot_count: int


class DeltaReportResponse(BaseModel):
    from_label: str
    to_label: str
    total_changes: int
    additions: int
    removals: int
    modifications: int
    changes: list[dict]


@router.post("/{project_id}")
async def create_snapshot(
    project_id: str,
    request: CreateSnapshotRequest,
    db: AsyncSession = Depends(get_db),
) -> SnapshotResponse:
    """Create a new snapshot of the project state."""
    service = SnapshotService()

    # In production, would fetch actual project data from database
    # For now, use placeholder data
    snapshot = await service.create_snapshot(
        project_id=UUID(project_id),
        project_data={"id": project_id, "name": "Demo Project"},
        scenes_data=[],
        characters_data=[],
        shots_data=[],
        label=request.label or "",
        description=request.description or "",
    )

    return SnapshotResponse(
        id=str(snapshot.id),
        label=snapshot.label,
        created_at=snapshot.created_at.isoformat(),
        scene_count=snapshot.metadata.get("scene_count", 0),
        character_count=snapshot.metadata.get("character_count", 0),
        shot_count=snapshot.metadata.get("shot_count", 0),
    )


@router.get("/{project_id}")
async def list_snapshots(project_id: str) -> list[SnapshotResponse]:
    """List all snapshots for a project."""
    service = SnapshotService()
    snapshots = await service.list_snapshots(UUID(project_id))

    return [
        SnapshotResponse(
            id=str(s.id),
            label=s.label,
            created_at=s.created_at.isoformat(),
            scene_count=s.metadata.get("scene_count", 0),
            character_count=s.metadata.get("character_count", 0),
            shot_count=s.metadata.get("shot_count", 0),
        )
        for s in snapshots
    ]


@router.get("/{project_id}/compare")
async def compare_snapshots(
    project_id: str,
    from_id: str,
    to_id: str,
) -> DeltaReportResponse:
    """Compare two snapshots and return delta report."""
    service = SnapshotService()

    try:
        report = await service.compare_snapshots(
            project_id=UUID(project_id),
            from_id=UUID(from_id),
            to_id=UUID(to_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return DeltaReportResponse(
        from_label=report.from_label,
        to_label=report.to_label,
        total_changes=report.total_changes,
        additions=report.additions,
        removals=report.removals,
        modifications=report.modifications,
        changes=[c.to_dict() for c in report.changes[:50]],  # Limit to 50
    )


@router.get("/{project_id}/{snapshot_id}")
async def get_snapshot(project_id: str, snapshot_id: str) -> dict:
    """Get a specific snapshot."""
    service = SnapshotService()
    snapshot = await service.get_snapshot(UUID(project_id), UUID(snapshot_id))

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return snapshot.to_dict()
