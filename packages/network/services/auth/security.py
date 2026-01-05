"""
Security utilities for JWT authentication and password hashing.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from ...shared.config import get_settings


class PasswordHasher:
    """Password hashing using bcrypt."""

    @staticmethod
    def hash(password: str) -> str:
        """Hash a password."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception:
            return False


class TokenType:
    """Token type constants."""

    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


class JWTHandler:
    """JWT token creation and verification."""

    def __init__(self):
        settings = get_settings()
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    def create_access_token(
        self,
        user_id: uuid.UUID,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create an access token."""
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )

    def create_refresh_token(
        self,
        user_id: uuid.UUID,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a refresh token."""
        expires_delta = timedelta(days=self.refresh_token_expire_days)
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.REFRESH,
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )

    def create_email_verification_token(
        self,
        user_id: uuid.UUID,
        email: str,
    ) -> str:
        """Create an email verification token."""
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.EMAIL_VERIFY,
            expires_delta=timedelta(hours=24),
            additional_claims={"email": email},
        )

    def create_password_reset_token(
        self,
        user_id: uuid.UUID,
    ) -> str:
        """Create a password reset token."""
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.PASSWORD_RESET,
            expires_delta=timedelta(hours=1),
        )

    def _create_token(
        self,
        user_id: uuid.UUID,
        token_type: str,
        expires_delta: timedelta,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a JWT token."""
        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta

        payload = {
            "sub": str(user_id),
            "type": token_type,
            "iat": now,
            "exp": expires_at,
            "jti": str(uuid.uuid4()),  # Unique token ID
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        Decode and verify a JWT token.

        Returns None if the token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except JWTError:
            return None

    def verify_access_token(self, token: str) -> Optional[uuid.UUID]:
        """
        Verify an access token and return the user ID.

        Returns None if the token is invalid.
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        if payload.get("type") != TokenType.ACCESS:
            return None

        try:
            return uuid.UUID(payload["sub"])
        except (KeyError, ValueError):
            return None

    def verify_refresh_token(self, token: str) -> Optional[uuid.UUID]:
        """
        Verify a refresh token and return the user ID.

        Returns None if the token is invalid.
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        if payload.get("type") != TokenType.REFRESH:
            return None

        try:
            return uuid.UUID(payload["sub"])
        except (KeyError, ValueError):
            return None

    def verify_email_token(self, token: str) -> Optional[tuple[uuid.UUID, str]]:
        """
        Verify an email verification token.

        Returns (user_id, email) if valid, None otherwise.
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        if payload.get("type") != TokenType.EMAIL_VERIFY:
            return None

        try:
            user_id = uuid.UUID(payload["sub"])
            email = payload["email"]
            return (user_id, email)
        except (KeyError, ValueError):
            return None

    def verify_password_reset_token(self, token: str) -> Optional[uuid.UUID]:
        """
        Verify a password reset token and return the user ID.

        Returns None if the token is invalid.
        """
        payload = self.decode_token(token)
        if payload is None:
            return None

        if payload.get("type") != TokenType.PASSWORD_RESET:
            return None

        try:
            return uuid.UUID(payload["sub"])
        except (KeyError, ValueError):
            return None


# Singleton instances
password_hasher = PasswordHasher()
jwt_handler = JWTHandler()
