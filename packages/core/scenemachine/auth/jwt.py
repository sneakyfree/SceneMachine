"""
JWT Token Utilities

Provides JWT token creation, validation, and decoding.
"""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from scenemachine.config import get_settings


class TokenType(StrEnum):
    """JWT token type enumeration."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: UUID
    token_type: TokenType
    exp: datetime
    iat: datetime
    jti: str | None = None  # JWT ID for refresh token tracking


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        self.message = message
        super().__init__(self.message)


def create_access_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a new access token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiration time
        extra_claims: Optional additional claims to include

    Returns:
        Encoded JWT access token string
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    now = datetime.now(UTC)

    claims = {
        "sub": str(user_id),
        "type": TokenType.ACCESS.value,
        "exp": expire,
        "iat": now,
    }

    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(
        claims,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: UUID,
    jti: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new refresh token.

    Args:
        user_id: User ID to encode in token
        jti: Unique JWT ID for token tracking
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

    now = datetime.now(UTC)

    claims = {
        "sub": str(user_id),
        "type": TokenType.REFRESH.value,
        "exp": expire,
        "iat": now,
        "jti": jti,
    }

    return jwt.encode(
        claims,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        TokenData containing decoded claims

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = payload.get("sub")
        token_type = payload.get("type")
        exp = payload.get("exp")
        iat = payload.get("iat")
        jti = payload.get("jti")

        if not user_id or not token_type:
            raise AuthenticationError("Invalid token payload")

        return TokenData(
            user_id=UUID(user_id),
            token_type=TokenType(token_type),
            exp=datetime.fromtimestamp(exp, tz=UTC),
            iat=datetime.fromtimestamp(iat, tz=UTC),
            jti=jti,
        )

    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}") from e
    except (ValueError, KeyError) as e:
        raise AuthenticationError(f"Token validation failed: {e}") from e


def get_token_expiry(token_type: TokenType) -> datetime:
    """Get the expiry datetime for a token type.

    Args:
        token_type: Type of token (access or refresh)

    Returns:
        Datetime when token would expire
    """
    settings = get_settings()
    now = datetime.now(UTC)

    if token_type == TokenType.ACCESS:
        return now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    else:
        return now + timedelta(days=settings.jwt_refresh_token_expire_days)
