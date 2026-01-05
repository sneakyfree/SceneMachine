"""
Authentication routes for SceneMachine Network.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.config import get_settings
from ....shared.database import get_session
from ....shared.models import CreatorProfile, User, UserSettings
from ..dependencies import CurrentUser
from ..schemas import (
    MessageResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from ..security import jwt_handler, password_hasher

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """
    Register a new user account.

    Returns access and refresh tokens on success.
    """
    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == request.email.lower())
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if username already exists
    result = await session.execute(
        select(User).where(User.username == request.username.lower())
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create user
    user = User(
        email=request.email.lower(),
        username=request.username.lower(),
        display_name=request.display_name,
        password_hash=password_hasher.hash(request.password),
        is_active=True,
        is_verified=False,
        is_creator=False,
        email_verified=False,
    )
    session.add(user)

    # Create default settings
    settings = UserSettings(user_id=user.id)
    session.add(settings)

    await session.flush()

    # Generate tokens
    access_token = jwt_handler.create_access_token(user.id)
    refresh_token = jwt_handler.create_refresh_token(user.id)

    settings_obj = get_settings()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings_obj.jwt_access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """
    Log in with email and password.

    Returns access and refresh tokens on success.
    """
    # Find user by email
    result = await session.execute(
        select(User).where(User.email == request.email.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not password_hasher.verify(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Generate tokens
    access_token = jwt_handler.create_access_token(user.id)
    refresh_token = jwt_handler.create_refresh_token(user.id)

    settings = get_settings()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """
    Refresh access token using a refresh token.
    """
    # Verify refresh token
    user_id = jwt_handler.verify_refresh_token(request.refresh_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new tokens
    access_token = jwt_handler.create_access_token(user.id)
    new_refresh_token = jwt_handler.create_refresh_token(user.id)

    settings = get_settings()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: CurrentUser,
) -> MessageResponse:
    """
    Log out the current user.

    Note: This is a placeholder. In production, you would want to
    invalidate the refresh token in Redis or a database.
    """
    # In a production system, you would:
    # 1. Add the refresh token to a blacklist in Redis
    # 2. Or track active sessions and invalidate them
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get the current authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """
    Update the current user's profile.
    """
    if request.display_name is not None:
        current_user.display_name = request.display_name
    if request.bio is not None:
        current_user.bio = request.bio
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    await session.flush()
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """
    Change the current user's password.
    """
    # Verify current password
    if current_user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth-only accounts",
        )

    if not password_hasher.verify(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = password_hasher.hash(request.new_password)
    await session.flush()

    return MessageResponse(message="Password changed successfully")


@router.post("/become-creator", response_model=MessageResponse)
async def become_creator(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """
    Convert the current user account to a creator account.
    """
    if current_user.is_creator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a creator account",
        )

    # Create creator profile
    creator_profile = CreatorProfile(
        user_id=current_user.id,
        channel_name=current_user.display_name,
    )
    session.add(creator_profile)

    # Update user
    current_user.is_creator = True
    await session.flush()

    return MessageResponse(message="Creator account activated")
