"""Project sharing service."""

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.models import Project
from scenemachine.models.share import (
    ProjectComment,
    ProjectShare,
    SharePermission,
    ShareStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ShareResult:
    """Result of creating a share."""

    success: bool
    share_id: Optional[str]
    share_code: Optional[str]
    share_url: Optional[str]
    error: Optional[str]


@dataclass
class ShareInfo:
    """Information about a share."""

    id: str
    project_id: str
    project_name: str
    share_code: str
    permission: str
    status: str
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    is_public: bool
    expires_at: Optional[str]
    created_at: str
    access_count: int


class SharingService:
    """Service for managing project sharing."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _generate_share_code(self) -> str:
        """Generate a unique share code."""
        return secrets.token_urlsafe(32)

    async def create_share(
        self,
        project_id: UUID,
        permission: SharePermission = SharePermission.VIEW,
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        message: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        is_public: bool = False,
    ) -> ShareResult:
        """Create a new project share.

        Args:
            project_id: Project to share
            permission: Permission level
            recipient_email: Email of recipient (optional)
            recipient_name: Name of recipient (optional)
            message: Optional message to include
            expires_in_days: Optional expiration in days
            is_public: Whether share is publicly accessible

        Returns:
            ShareResult with share details
        """
        try:
            # Verify project exists
            project = await self.session.get(Project, project_id)
            if not project:
                return ShareResult(
                    success=False,
                    share_id=None,
                    share_code=None,
                    share_url=None,
                    error=f"Project {project_id} not found",
                )

            # Generate unique share code
            share_code = self._generate_share_code()

            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

            # Create share record
            share = ProjectShare(
                project_id=project_id,
                share_code=share_code,
                permission=permission,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                message=message,
                expires_at=expires_at,
                is_public=is_public,
                status=ShareStatus.PENDING,
            )

            self.session.add(share)
            await self.session.commit()
            await self.session.refresh(share)

            # Build share URL (would be configurable in production)
            share_url = f"scenemachine://share/{share_code}"

            logger.info(f"Created share {share.id} for project {project_id}")

            return ShareResult(
                success=True,
                share_id=str(share.id),
                share_code=share_code,
                share_url=share_url,
                error=None,
            )

        except Exception as e:
            logger.exception(f"Failed to create share for project {project_id}")
            await self.session.rollback()
            return ShareResult(
                success=False,
                share_id=None,
                share_code=None,
                share_url=None,
                error=str(e),
            )

    async def get_share_by_code(self, share_code: str) -> Optional[ProjectShare]:
        """Get a share by its code.

        Args:
            share_code: The share code

        Returns:
            ProjectShare or None
        """
        stmt = (
            select(ProjectShare)
            .options(selectinload(ProjectShare.project))
            .where(ProjectShare.share_code == share_code)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_shares(self, project_id: UUID) -> List[ShareInfo]:
        """Get all shares for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of ShareInfo
        """
        stmt = (
            select(ProjectShare)
            .options(selectinload(ProjectShare.project))
            .where(ProjectShare.project_id == project_id)
            .order_by(ProjectShare.created_at.desc())
        )
        result = await self.session.execute(stmt)
        shares = result.scalars().all()

        return [
            ShareInfo(
                id=str(share.id),
                project_id=str(share.project_id),
                project_name=share.project.name,
                share_code=share.share_code,
                permission=share.permission.value,
                status=share.status.value,
                recipient_email=share.recipient_email,
                recipient_name=share.recipient_name,
                is_public=share.is_public,
                expires_at=share.expires_at.isoformat() if share.expires_at else None,
                created_at=share.created_at.isoformat(),
                access_count=share.access_count,
            )
            for share in shares
        ]

    async def accept_share(self, share_code: str) -> Dict[str, Any]:
        """Accept a share invitation.

        Args:
            share_code: The share code

        Returns:
            Dict with project details if successful
        """
        share = await self.get_share_by_code(share_code)

        if not share:
            return {"success": False, "error": "Share not found"}

        if not share.is_valid():
            return {"success": False, "error": "Share is no longer valid"}

        # Update share status
        share.status = ShareStatus.ACCEPTED
        share.last_accessed_at = datetime.now(timezone.utc)
        share.access_count += 1

        await self.session.commit()

        return {
            "success": True,
            "projectId": str(share.project_id),
            "projectName": share.project.name,
            "permission": share.permission.value,
        }

    async def revoke_share(self, share_id: UUID) -> bool:
        """Revoke a share.

        Args:
            share_id: Share UUID

        Returns:
            True if revoked
        """
        share = await self.session.get(ProjectShare, share_id)
        if not share:
            return False

        share.status = ShareStatus.REVOKED
        await self.session.commit()

        logger.info(f"Revoked share {share_id}")
        return True

    async def update_share_permission(
        self,
        share_id: UUID,
        permission: SharePermission,
    ) -> bool:
        """Update share permission level.

        Args:
            share_id: Share UUID
            permission: New permission level

        Returns:
            True if updated
        """
        share = await self.session.get(ProjectShare, share_id)
        if not share:
            return False

        share.permission = permission
        await self.session.commit()

        logger.info(f"Updated share {share_id} permission to {permission}")
        return True

    async def record_access(self, share_code: str) -> bool:
        """Record share access for analytics.

        Args:
            share_code: The share code

        Returns:
            True if recorded
        """
        share = await self.get_share_by_code(share_code)
        if not share or not share.is_valid():
            return False

        share.last_accessed_at = datetime.now(timezone.utc)
        share.access_count += 1
        await self.session.commit()

        return True

    # Comment methods
    async def add_comment(
        self,
        project_id: UUID,
        author_name: str,
        content: str,
        shot_id: Optional[UUID] = None,
        author_email: Optional[str] = None,
        parent_id: Optional[UUID] = None,
        timecode_seconds: Optional[float] = None,
    ) -> Optional[ProjectComment]:
        """Add a comment to a project or shot.

        Args:
            project_id: Project UUID
            author_name: Name of commenter
            content: Comment text
            shot_id: Optional shot UUID for shot-specific comment
            author_email: Optional email
            parent_id: Optional parent comment for replies
            timecode_seconds: Optional timecode for shot comments

        Returns:
            Created comment or None
        """
        try:
            comment = ProjectComment(
                project_id=project_id,
                shot_id=shot_id,
                parent_id=parent_id,
                author_name=author_name,
                author_email=author_email,
                content=content,
                timecode_seconds=timecode_seconds,
            )

            self.session.add(comment)
            await self.session.commit()
            await self.session.refresh(comment)

            logger.info(f"Added comment {comment.id} to project {project_id}")
            return comment

        except Exception as e:
            logger.exception("Failed to add comment")
            await self.session.rollback()
            return None

    async def get_project_comments(
        self,
        project_id: UUID,
        shot_id: Optional[UUID] = None,
        include_resolved: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get comments for a project.

        Args:
            project_id: Project UUID
            shot_id: Optional shot filter
            include_resolved: Include resolved comments

        Returns:
            List of comment dicts
        """
        stmt = select(ProjectComment).where(ProjectComment.project_id == project_id)

        if shot_id:
            stmt = stmt.where(ProjectComment.shot_id == shot_id)

        if not include_resolved:
            stmt = stmt.where(ProjectComment.is_resolved == False)  # noqa: E712

        stmt = stmt.order_by(ProjectComment.created_at.desc())

        result = await self.session.execute(stmt)
        comments = result.scalars().all()

        return [
            {
                "id": str(c.id),
                "projectId": str(c.project_id),
                "shotId": str(c.shot_id) if c.shot_id else None,
                "parentId": str(c.parent_id) if c.parent_id else None,
                "authorName": c.author_name,
                "authorEmail": c.author_email,
                "content": c.content,
                "timecodeSeconds": c.timecode_seconds,
                "isResolved": c.is_resolved,
                "createdAt": c.created_at.isoformat(),
            }
            for c in comments
        ]

    async def resolve_comment(self, comment_id: UUID) -> bool:
        """Mark a comment as resolved.

        Args:
            comment_id: Comment UUID

        Returns:
            True if resolved
        """
        comment = await self.session.get(ProjectComment, comment_id)
        if not comment:
            return False

        comment.is_resolved = True
        comment.resolved_at = datetime.now(timezone.utc)
        await self.session.commit()

        return True

    async def delete_comment(self, comment_id: UUID) -> bool:
        """Delete a comment.

        Args:
            comment_id: Comment UUID

        Returns:
            True if deleted
        """
        comment = await self.session.get(ProjectComment, comment_id)
        if not comment:
            return False

        await self.session.delete(comment)
        await self.session.commit()

        return True

    async def cleanup_expired_shares(self) -> int:
        """Mark expired shares as expired.

        Returns:
            Number of shares expired
        """
        now = datetime.now(timezone.utc)

        stmt = (
            update(ProjectShare)
            .where(
                ProjectShare.expires_at.isnot(None),
                ProjectShare.expires_at < now,
                ProjectShare.status.in_([ShareStatus.PENDING, ShareStatus.ACCEPTED]),
            )
            .values(status=ShareStatus.EXPIRED)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Expired {count} shares")

        return count
