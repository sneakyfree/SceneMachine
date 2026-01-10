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


import re
import hashlib
import hmac
import os


# License key format: SM-XXXXX-XXXXX-XXXXX-XXXXX (where X is alphanumeric)
LICENSE_KEY_PATTERN = re.compile(
    r"^SM-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$"
)

# Secret for HMAC validation (in production, use environment variable)
LICENSE_SECRET = os.environ.get("STUDIO_LICENSE_SECRET", "dev-secret-key")


def validate_license_checksum(license_key: str) -> bool:
    """
    Validate license key checksum.

    The last segment is a checksum derived from the first three segments.
    """
    parts = license_key.split("-")
    if len(parts) != 5:
        return False

    # Prefix + first 3 segments
    base = "-".join(parts[:4])

    # Calculate expected checksum
    expected = hmac.new(
        LICENSE_SECRET.encode(),
        base.encode(),
        hashlib.sha256,
    ).hexdigest()[:5].upper()

    return parts[4] == expected


async def validate_studio_license(license_key: str) -> bool:
    """
    Validate a Studio license key.

    Validation includes:
    1. Format check (SM-XXXXX-XXXXX-XXXXX-XXXXX)
    2. Character validation (alphanumeric only)
    3. Checksum verification (HMAC-based)
    4. (Future) Remote API validation

    Args:
        license_key: The license key to validate

    Returns:
        True if the license key is valid
    """
    # Normalize to uppercase
    license_key = license_key.upper().strip()

    # Check minimum length
    if len(license_key) < 10:
        return False

    # Check format pattern
    if not LICENSE_KEY_PATTERN.match(license_key):
        # Also accept legacy format (just alphanumeric, 20+ chars)
        if len(license_key) >= 20 and license_key.replace("-", "").isalnum():
            return True
        return False

    # Validate checksum for new format keys
    if license_key.startswith("SM-"):
        if not validate_license_checksum(license_key):
            return False

    # In production, add remote validation:
    # try:
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(
    #             "https://api.scenemachine.studio/licenses/validate",
    #             json={"key": license_key},
    #             timeout=10.0,
    #         )
    #         return response.status_code == 200
    # except Exception:
    #     # Fail open for development, fail closed for production
    #     return os.environ.get("ENV", "development") == "development"

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
