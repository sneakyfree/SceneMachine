"""Sharing API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.dependencies import get_db
from scenemachine.models.share import SharePermission
from scenemachine.services.sharing import SharingService

router = APIRouter()


# Request/Response Models
class CreateShareRequest(BaseModel):
    """Request to create a share."""

    project_id: UUID
    permission: str = "view"
    recipient_email: EmailStr | None = None
    recipient_name: str | None = None
    message: str | None = None
    expires_in_days: int | None = None
    is_public: bool = False


class UpdateShareRequest(BaseModel):
    """Request to update a share."""

    permission: str | None = None


class AddCommentRequest(BaseModel):
    """Request to add a comment."""

    author_name: str
    content: str
    author_email: EmailStr | None = None
    shot_id: UUID | None = None
    parent_id: UUID | None = None
    timecode_seconds: float | None = None


# Routes
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_share(
    request: CreateShareRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new project share.

    Creates a shareable link for a project with specified permissions.
    """
    try:
        permission = SharePermission(request.permission)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission: {request.permission}. Must be one of: view, comment, edit",
        )

    service = SharingService(db)
    result = await service.create_share(
        project_id=request.project_id,
        permission=permission,
        recipient_email=request.recipient_email,
        recipient_name=request.recipient_name,
        message=request.message,
        expires_in_days=request.expires_in_days,
        is_public=request.is_public,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    return {
        "success": True,
        "shareId": result.share_id,
        "shareCode": result.share_code,
        "shareUrl": result.share_url,
    }


@router.get("/project/{project_id}")
async def get_project_shares(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all shares for a project."""
    service = SharingService(db)
    shares = await service.get_project_shares(project_id)

    return [
        {
            "id": share.id,
            "projectId": share.project_id,
            "projectName": share.project_name,
            "shareCode": share.share_code,
            "permission": share.permission,
            "status": share.status,
            "recipientEmail": share.recipient_email,
            "recipientName": share.recipient_name,
            "isPublic": share.is_public,
            "expiresAt": share.expires_at,
            "createdAt": share.created_at,
            "accessCount": share.access_count,
        }
        for share in shares
    ]


@router.get("/code/{share_code}")
async def get_share_by_code(
    share_code: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get share information by code."""
    service = SharingService(db)
    share = await service.get_share_by_code(share_code)

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    if not share.is_valid():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share is no longer valid",
        )

    return {
        "shareCode": share.share_code,
        "projectId": str(share.project_id),
        "projectName": share.project.name if share.project else None,
        "permission": share.permission.value,
        "status": share.status.value,
        "isPublic": share.is_public,
        "expiresAt": share.expires_at.isoformat() if share.expires_at else None,
    }


@router.post("/code/{share_code}/accept")
async def accept_share(
    share_code: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept a share invitation.

    Marks the share as accepted and returns project details.
    """
    service = SharingService(db)
    result = await service.accept_share(share_code)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to accept share"),
        )

    return result


@router.post("/code/{share_code}/access")
async def record_access(
    share_code: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record share access for analytics."""
    service = SharingService(db)
    success = await service.record_access(share_code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or no longer valid",
        )

    return {"success": True}


@router.patch("/{share_id}")
async def update_share(
    share_id: UUID,
    request: UpdateShareRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update share permission."""
    if request.permission:
        try:
            permission = SharePermission(request.permission)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission: {request.permission}",
            )

        service = SharingService(db)
        success = await service.update_share_permission(share_id, permission)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not found",
            )

    return {"success": True}


@router.delete("/{share_id}")
async def revoke_share(
    share_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Revoke a share."""
    service = SharingService(db)
    success = await service.revoke_share(share_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    return {"success": True, "message": "Share revoked"}


# Comment endpoints
@router.post("/projects/{project_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    project_id: UUID,
    request: AddCommentRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a comment to a project or shot."""
    service = SharingService(db)
    comment = await service.add_comment(
        project_id=project_id,
        author_name=request.author_name,
        content=request.content,
        shot_id=request.shot_id,
        author_email=request.author_email,
        parent_id=request.parent_id,
        timecode_seconds=request.timecode_seconds,
    )

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add comment",
        )

    return {
        "id": str(comment.id),
        "projectId": str(comment.project_id),
        "shotId": str(comment.shot_id) if comment.shot_id else None,
        "authorName": comment.author_name,
        "content": comment.content,
        "createdAt": comment.created_at.isoformat(),
    }


@router.get("/projects/{project_id}/comments")
async def get_project_comments(
    project_id: UUID,
    shot_id: UUID | None = None,
    include_resolved: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get comments for a project."""
    service = SharingService(db)
    comments = await service.get_project_comments(
        project_id=project_id,
        shot_id=shot_id,
        include_resolved=include_resolved,
    )

    return comments


@router.post("/comments/{comment_id}/resolve")
async def resolve_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a comment as resolved."""
    service = SharingService(db)
    success = await service.resolve_comment(comment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    return {"success": True}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a comment."""
    service = SharingService(db)
    success = await service.delete_comment(comment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    return {"success": True, "message": "Comment deleted"}


@router.post("/cleanup-expired")
async def cleanup_expired_shares(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark expired shares as expired.

    This endpoint can be called periodically to clean up expired shares.
    """
    service = SharingService(db)
    count = await service.cleanup_expired_shares()

    return {"success": True, "expiredCount": count}
