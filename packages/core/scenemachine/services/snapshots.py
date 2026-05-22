"""
Snapshot Service - Immutable project snapshots for audit trail.

Provides:
- Create snapshots of project state
- Compare snapshots (delta reports)
- Restore from snapshots
- Export snapshots for audit
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from scenemachine.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """Immutable snapshot of project state."""

    id: UUID
    project_id: UUID
    created_at: datetime
    created_by: UUID | None = None
    label: str = ""
    description: str = ""

    # Hashes for verification
    project_hash: str = ""
    scenes_hash: str = ""
    characters_hash: str = ""
    shots_hash: str = ""

    # Content
    project_data: dict[str, Any] = field(default_factory=dict)
    scenes_data: list[dict[str, Any]] = field(default_factory=list)
    characters_data: list[dict[str, Any]] = field(default_factory=list)
    shots_data: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "created_at": self.created_at.isoformat(),
            "created_by": str(self.created_by) if self.created_by else None,
            "label": self.label,
            "description": self.description,
            "project_hash": self.project_hash,
            "scenes_hash": self.scenes_hash,
            "characters_hash": self.characters_hash,
            "shots_hash": self.shots_hash,
            "project_data": self.project_data,
            "scenes_data": self.scenes_data,
            "characters_data": self.characters_data,
            "shots_data": self.shots_data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]),
            project_id=UUID(data["project_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=UUID(data["created_by"]) if data.get("created_by") else None,
            label=data.get("label", ""),
            description=data.get("description", ""),
            project_hash=data.get("project_hash", ""),
            scenes_hash=data.get("scenes_hash", ""),
            characters_hash=data.get("characters_hash", ""),
            shots_hash=data.get("shots_hash", ""),
            project_data=data.get("project_data", {}),
            scenes_data=data.get("scenes_data", []),
            characters_data=data.get("characters_data", []),
            shots_data=data.get("shots_data", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DeltaItem:
    """A single change between snapshots."""

    entity_type: str  # project, scene, character, shot
    entity_id: str
    change_type: str  # added, removed, modified
    field_name: str | None = None
    old_value: Any = None
    new_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "change_type": self.change_type,
            "field_name": self.field_name,
            "old_value": str(self.old_value)[:100] if self.old_value else None,
            "new_value": str(self.new_value)[:100] if self.new_value else None,
        }


@dataclass
class DeltaReport:
    """Comparison between two snapshots."""

    from_snapshot_id: UUID
    to_snapshot_id: UUID
    from_label: str
    to_label: str
    generated_at: datetime
    changes: list[DeltaItem] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.changes)

    @property
    def additions(self) -> int:
        return sum(1 for c in self.changes if c.change_type == "added")

    @property
    def removals(self) -> int:
        return sum(1 for c in self.changes if c.change_type == "removed")

    @property
    def modifications(self) -> int:
        return sum(1 for c in self.changes if c.change_type == "modified")

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_snapshot_id": str(self.from_snapshot_id),
            "to_snapshot_id": str(self.to_snapshot_id),
            "from_label": self.from_label,
            "to_label": self.to_label,
            "generated_at": self.generated_at.isoformat(),
            "total_changes": self.total_changes,
            "additions": self.additions,
            "removals": self.removals,
            "modifications": self.modifications,
            "changes": [c.to_dict() for c in self.changes],
        }


class SnapshotService:
    """
    Service for creating and managing immutable project snapshots.

    Used for:
    - Audit compliance (immutable history)
    - Version control (compare states)
    - Reproducibility (restore from snapshot)
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        settings = get_settings()
        self._storage_path = storage_path or Path(settings.data_dir) / "snapshots"
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def _hash_data(self, data: Any) -> str:
        """Create SHA-256 hash of data."""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def create_snapshot(
        self,
        project_id: UUID,
        project_data: dict[str, Any],
        scenes_data: list[dict[str, Any]],
        characters_data: list[dict[str, Any]],
        shots_data: list[dict[str, Any]],
        label: str = "",
        description: str = "",
        created_by: UUID | None = None,
    ) -> Snapshot:
        """Create an immutable snapshot of project state."""
        snapshot = Snapshot(
            id=uuid4(),
            project_id=project_id,
            created_at=datetime.now(UTC),
            created_by=created_by,
            label=label or f"Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description=description,
            project_hash=self._hash_data(project_data),
            scenes_hash=self._hash_data(scenes_data),
            characters_hash=self._hash_data(characters_data),
            shots_hash=self._hash_data(shots_data),
            project_data=project_data,
            scenes_data=scenes_data,
            characters_data=characters_data,
            shots_data=shots_data,
            metadata={
                "scene_count": len(scenes_data),
                "character_count": len(characters_data),
                "shot_count": len(shots_data),
            },
        )

        # Save to disk
        await self._save_snapshot(snapshot)

        logger.info(f"Created snapshot {snapshot.id} for project {project_id}")
        return snapshot

    async def _save_snapshot(self, snapshot: Snapshot) -> None:
        """Save snapshot to disk."""
        project_dir = self._storage_path / str(snapshot.project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        file_path = project_dir / f"{snapshot.id}.json"
        with open(file_path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    async def get_snapshot(self, project_id: UUID, snapshot_id: UUID) -> Snapshot | None:
        """Load a snapshot from disk."""
        file_path = self._storage_path / str(project_id) / f"{snapshot_id}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)

        return Snapshot.from_dict(data)

    async def list_snapshots(self, project_id: UUID) -> list[Snapshot]:
        """List all snapshots for a project."""
        project_dir = self._storage_path / str(project_id)

        if not project_dir.exists():
            return []

        snapshots = []
        for file_path in project_dir.glob("*.json"):
            with open(file_path) as f:
                data = json.load(f)
            snapshots.append(Snapshot.from_dict(data))

        # Sort by creation time, newest first
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots

    async def compare_snapshots(
        self,
        project_id: UUID,
        from_id: UUID,
        to_id: UUID,
    ) -> DeltaReport:
        """Generate delta report between two snapshots."""
        from_snapshot = await self.get_snapshot(project_id, from_id)
        to_snapshot = await self.get_snapshot(project_id, to_id)

        if not from_snapshot or not to_snapshot:
            raise ValueError("One or both snapshots not found")

        changes: list[DeltaItem] = []

        # Compare scenes
        changes.extend(
            self._compare_lists(
                "scene",
                from_snapshot.scenes_data,
                to_snapshot.scenes_data,
                id_key="id",
            )
        )

        # Compare characters
        changes.extend(
            self._compare_lists(
                "character",
                from_snapshot.characters_data,
                to_snapshot.characters_data,
                id_key="id",
            )
        )

        # Compare shots
        changes.extend(
            self._compare_lists(
                "shot",
                from_snapshot.shots_data,
                to_snapshot.shots_data,
                id_key="id",
            )
        )

        # Compare project settings
        changes.extend(
            self._compare_dicts(
                "project",
                str(project_id),
                from_snapshot.project_data,
                to_snapshot.project_data,
            )
        )

        return DeltaReport(
            from_snapshot_id=from_id,
            to_snapshot_id=to_id,
            from_label=from_snapshot.label,
            to_label=to_snapshot.label,
            generated_at=datetime.now(UTC),
            changes=changes,
        )

    def _compare_lists(
        self,
        entity_type: str,
        from_list: list[dict[str, Any]],
        to_list: list[dict[str, Any]],
        id_key: str = "id",
    ) -> list[DeltaItem]:
        """Compare two lists and return changes."""
        changes = []

        from_by_id = {str(item.get(id_key, "")): item for item in from_list}
        to_by_id = {str(item.get(id_key, "")): item for item in to_list}

        # Find additions
        for item_id in to_by_id:
            if item_id not in from_by_id:
                changes.append(
                    DeltaItem(
                        entity_type=entity_type,
                        entity_id=item_id,
                        change_type="added",
                    )
                )

        # Find removals
        for item_id in from_by_id:
            if item_id not in to_by_id:
                changes.append(
                    DeltaItem(
                        entity_type=entity_type,
                        entity_id=item_id,
                        change_type="removed",
                    )
                )

        # Find modifications
        for item_id in from_by_id:
            if item_id in to_by_id:
                from_item = from_by_id[item_id]
                to_item = to_by_id[item_id]

                changes.extend(
                    self._compare_dicts(
                        entity_type,
                        item_id,
                        from_item,
                        to_item,
                    )
                )

        return changes

    def _compare_dicts(
        self,
        entity_type: str,
        entity_id: str,
        from_dict: dict[str, Any],
        to_dict: dict[str, Any],
    ) -> list[DeltaItem]:
        """Compare two dictionaries and return field-level changes."""
        changes = []

        all_keys = set(from_dict.keys()) | set(to_dict.keys())

        for key in all_keys:
            from_val = from_dict.get(key)
            to_val = to_dict.get(key)

            if from_val != to_val:
                changes.append(
                    DeltaItem(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        change_type="modified",
                        field_name=key,
                        old_value=from_val,
                        new_value=to_val,
                    )
                )

        return changes

    async def verify_snapshot(self, snapshot: Snapshot) -> bool:
        """Verify snapshot integrity using hashes."""
        return (
            self._hash_data(snapshot.project_data) == snapshot.project_hash
            and self._hash_data(snapshot.scenes_data) == snapshot.scenes_hash
            and self._hash_data(snapshot.characters_data) == snapshot.characters_hash
            and self._hash_data(snapshot.shots_data) == snapshot.shots_hash
        )
