"""
Studio integration routes for SceneMachine Network.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.database import get_session
from ....shared.models import UserSettings
from ..dependencies import CurrentUser
from ..schemas import MessageResponse, StudioLinkRequest, StudioLinkResponse

router = APIRouter(prefix="/auth/studio", tags=["studio"])


def mask_license_key(key: str) -> str:
    """Mask a license key for display, showing only first and last 4 characters."""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


async def validate_studio_license(license_key: str) -> bool:
    """
    Validate a Studio license key.

    In production, this would call the Studio API to verify the license.
    For now, we accept any key that matches a basic format.
    """
    # Basic validation: must be at least 10 characters
    if len(license_key) < 10:
        return False

    # In production, you would:
    # 1. Call Studio API to verify the license
    # 2. Check if the license is valid and not expired
    # 3. Check if the license is already linked to another account
    # 4. Return license details (tier, features, etc.)

    # For development, accept any key that looks valid
    return True


@router.post("/link", response_model=StudioLinkResponse)
async def link_studio(
    request: StudioLinkRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StudioLinkResponse:
    """
    Link a SceneMachine Studio license to the current account.

    This enables features like:
    - Direct publishing from Studio to Network
    - "Made with Studio" badge on videos
    - Priority support
    """
    # Get user settings
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if settings is None:
        # Create settings if they don't exist
        settings = UserSettings(user_id=current_user.id)
        session.add(settings)

    # Check if already linked
    if settings.studio_linked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Studio already linked. Unlink first to link a different license.",
        )

    # Validate the license
    is_valid = await validate_studio_license(request.license_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Studio license key",
        )

    # Link the license
    settings.studio_linked = True
    settings.studio_license_key = request.license_key
    settings.studio_linked_at = datetime.now(timezone.utc)

    await session.flush()

    return StudioLinkResponse(
        linked=True,
        linked_at=settings.studio_linked_at,
        license_key=mask_license_key(request.license_key),
    )


@router.delete("/link", response_model=MessageResponse)
async def unlink_studio(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """
    Unlink SceneMachine Studio from the current account.
    """
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if settings is None or not settings.studio_linked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Studio license linked",
        )

    # Unlink
    settings.studio_linked = False
    settings.studio_license_key = None
    settings.studio_linked_at = None

    await session.flush()

    return MessageResponse(message="Studio unlinked successfully")


@router.get("/link", response_model=StudioLinkResponse)
async def get_studio_link_status(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StudioLinkResponse:
    """
    Get the Studio link status for the current account.
    """
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if settings is None or not settings.studio_linked:
        return StudioLinkResponse(
            linked=False,
            linked_at=None,
            license_key=None,
        )

    return StudioLinkResponse(
        linked=True,
        linked_at=settings.studio_linked_at,
        license_key=mask_license_key(settings.studio_license_key)
        if settings.studio_license_key
        else None,
    )


@router.post("/verify", response_model=MessageResponse)
async def verify_studio_upload(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """
    Verify that the current user can upload from Studio.

    This is called by Studio before initiating an upload.
    Returns success if the user has a linked Studio license.
    """
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if settings is None or not settings.studio_linked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Studio license not linked. Please link your license in Network settings.",
        )

    # In production, you might also verify:
    # - License is still valid (not expired)
    # - User has upload quota remaining
    # - User is not rate-limited

    return MessageResponse(message="Studio upload authorized")
