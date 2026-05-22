"""
Authentication API Routes

Endpoints for user registration, login, token refresh, and logout.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.dependencies import CurrentActiveUser
from scenemachine.auth.schemas import (
    MessageResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from scenemachine.auth.service import (
    AccountLockedError,
    AuthService,
    AuthServiceError,
    InvalidCredentialsError,
    TokenError,
    UserExistsError,
)
from scenemachine.config import get_settings
from scenemachine.database import get_session

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """Get auth service instance."""
    return AuthService(session)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    data: UserRegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Register a new user account.

    - **email**: Valid email address (must be unique)
    - **username**: Unique username (3-50 chars, alphanumeric with _ and -)
    - **password**: Strong password (8+ chars, mixed case, digit)
    - **full_name**: Optional display name
    """
    try:
        user = await service.register_user(
            email=data.email,
            username=data.username,
            password=data.password,
            full_name=data.full_name,
        )
        return UserResponse.model_validate(user)
    except UserExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access tokens",
)
async def login(
    data: UserLoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate user and get access/refresh tokens.

    - **email**: User's email address
    - **password**: User's password

    Returns JWT access and refresh tokens.
    """
    try:
        user, access_token, refresh_token = await service.authenticate_user(
            email=data.email,
            password=data.password,
        )

        settings = get_settings()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
        ) from e
    except AuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Get new access and refresh tokens using a valid refresh token.

    - **refresh_token**: Current valid refresh token

    The old refresh token will be invalidated.
    """
    try:
        access_token, new_refresh_token = await service.refresh_tokens(
            refresh_token=data.refresh_token,
        )

        settings = get_settings()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke tokens",
)
async def logout(
    current_user: CurrentActiveUser,
    service: Annotated[AuthService, Depends(get_auth_service)],
    data: RefreshTokenRequest | None = None,
) -> MessageResponse:
    """Logout user and revoke refresh tokens.

    If a refresh token is provided, only that token is revoked.
    Otherwise, all refresh tokens for the user are revoked.
    """
    await service.logout(
        user_id=current_user.id,
        refresh_token=data.refresh_token if data else None,
    )

    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: CurrentActiveUser,
) -> UserResponse:
    """Get the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_current_user_profile(
    data: UserUpdateRequest,
    current_user: CurrentActiveUser,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Update the current user's profile.

    - **full_name**: Optional new display name
    - **bio**: Optional user biography
    - **avatar_url**: Optional avatar image URL
    """
    user = await service.update_user(
        user=current_user,
        full_name=data.full_name,
        bio=data.bio,
        avatar_url=data.avatar_url,
    )
    return UserResponse.model_validate(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
)
async def change_password(
    data: PasswordChangeRequest,
    current_user: CurrentActiveUser,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Change the current user's password.

    - **current_password**: Current password for verification
    - **new_password**: New password (must meet strength requirements)

    All existing sessions will be invalidated.
    """
    try:
        await service.change_password(
            user=current_user,
            current_password=data.current_password,
            new_password=data.new_password,
        )
        return MessageResponse(message="Password changed successfully. Please log in again.")
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        ) from e
