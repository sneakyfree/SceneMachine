"""
FastAPI dependencies for auth service.
"""

import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...shared.database import get_session
from ...shared.models import User
from .security import jwt_handler

# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> uuid.UUID:
    """
    Extract and verify the current user ID from the access token.

    Raises HTTPException if token is invalid or missing.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = jwt_handler.verify_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user(
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get the current authenticated user from the database.

    Raises HTTPException if user not found or inactive.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current active user.

    Same as get_current_user but with explicit active check.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


async def get_current_verified_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current verified user.

    Raises HTTPException if email is not verified.
    """
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return user


async def get_current_creator(
    user: Annotated[User, Depends(get_current_verified_user)],
) -> User:
    """
    Get the current user if they are a creator.

    Raises HTTPException if user is not a creator.
    """
    if not user.is_creator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creator account required",
        )
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current user if they are an admin.

    Raises HTTPException if user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_optional_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.

    Does not raise exceptions for missing/invalid tokens.
    """
    if credentials is None:
        return None

    user_id = jwt_handler.verify_access_token(credentials.credentials)
    if user_id is None:
        return None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    return user


# Type aliases for cleaner dependency injection
CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]
CurrentCreator = Annotated[User, Depends(get_current_creator)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
