"""
Authentication Dependencies

FastAPI dependencies for extracting and validating user authentication.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.jwt import (
    AuthenticationError,
    TokenData,
    TokenType,
    decode_token,
)
from scenemachine.database import get_session
from scenemachine.models.user import User

# HTTP Bearer token extractor
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(security)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        session: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: 401 if not authenticated or token invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = decode_token(credentials.credentials)

        # Verify this is an access token
        if token_data.token_type != TokenType.ACCESS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        result = await session.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current user and verify they are active.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active User object

    Raises:
        HTTPException: 403 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


async def get_optional_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(security)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Optional[User]:
    """Get the current user if authenticated, or None if not.

    Useful for endpoints that work differently for authenticated vs anonymous users.

    Args:
        credentials: HTTP Bearer credentials (optional)
        session: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token_data = decode_token(credentials.credentials)

        if token_data.token_type != TokenType.ACCESS:
            return None

        result = await session.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        if user and user.is_active:
            return user
        return None

    except AuthenticationError:
        return None


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
