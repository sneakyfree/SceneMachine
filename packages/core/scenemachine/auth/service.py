"""
Authentication Service

Business logic for user authentication and management.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.jwt import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
)
from scenemachine.auth.password import hash_password, verify_password
from scenemachine.config import get_settings
from scenemachine.models.user import RefreshToken, User


class AuthServiceError(Exception):
    """Base exception for auth service errors."""

    def __init__(self, message: str, code: str = "auth_error") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class UserExistsError(AuthServiceError):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, field: str) -> None:
        super().__init__(
            f"User with this {field} already exists",
            code="user_exists",
        )


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials are invalid."""

    def __init__(self) -> None:
        super().__init__(
            "Invalid email or password",
            code="invalid_credentials",
        )


class TokenError(AuthServiceError):
    """Raised when there's an issue with a token."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message, code="token_error")


class AccountLockedError(AuthServiceError):
    """Raised when account is locked due to too many failed login attempts."""

    def __init__(self, locked_until: datetime) -> None:
        minutes_remaining = max(
            1, int((locked_until - datetime.now(UTC)).total_seconds() / 60)
        )
        super().__init__(
            f"Account locked due to too many failed attempts. Try again in {minutes_remaining} minute(s).",
            code="account_locked",
        )


logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    # FEAT-006: Account lockout configuration
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    def __init__(self, session: AsyncSession) -> None:
        """Initialize auth service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Register a new user.

        Args:
            email: User's email address
            username: Unique username
            password: Plain text password
            full_name: Optional full name

        Returns:
            Created User object

        Raises:
            UserExistsError: If email or username already exists
        """
        # Check for existing email
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        if result.scalar_one_or_none():
            raise UserExistsError("email")

        # Check for existing username
        result = await self.session.execute(
            select(User).where(User.username == username.lower())
        )
        if result.scalar_one_or_none():
            raise UserExistsError("username")

        # Create user
        user = User(
            email=email.lower(),
            username=username.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def authenticate_user(
        self, email: str, password: str
    ) -> tuple[User, str, str]:
        """Authenticate user and generate tokens.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Tuple of (User, access_token, refresh_token)

        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked due to too many failed attempts
        """
        # Find user
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidCredentialsError()

        # FEAT-006: Check account lockout
        if user.locked_until and user.locked_until > datetime.now(UTC):
            logger.warning(f"Login attempt on locked account: {email}")
            raise AccountLockedError(user.locked_until)

        # Verify password
        if not verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            logger.warning(
                f"Failed login for {email}: attempt {user.failed_login_attempts}"
            )

            # Lock account after MAX_LOGIN_ATTEMPTS failures
            if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=self.LOCKOUT_DURATION_MINUTES
                )
                logger.warning(
                    f"Account locked for {email} until {user.locked_until}"
                )

            await self.session.commit()
            raise InvalidCredentialsError()

        if not user.is_active:
            raise AuthServiceError(
                "User account is inactive",
                code="user_inactive",
            )

        # FEAT-006: Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

        # Generate tokens
        access_token = create_access_token(user.id)
        jti = secrets.token_urlsafe(32)
        refresh_token = create_refresh_token(user.id, jti)

        # Store refresh token
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_password(jti),  # Hash the jti for storage
            expires_at=get_token_expiry(TokenType.REFRESH),
        )
        self.session.add(refresh_token_record)

        await self.session.commit()

        return user, access_token, refresh_token

    async def refresh_tokens(
        self, refresh_token: str
    ) -> tuple[str, str]:
        """Refresh access and refresh tokens.

        Args:
            refresh_token: Current refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token)

        Raises:
            TokenError: If refresh token is invalid or revoked
        """
        try:
            token_data = decode_token(refresh_token)
        except Exception as e:
            raise TokenError(str(e)) from e

        if token_data.token_type != TokenType.REFRESH:
            raise TokenError("Invalid token type")

        if not token_data.jti:
            raise TokenError("Invalid refresh token")

        # Find and validate refresh token in database
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == token_data.user_id,
                RefreshToken.is_revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        stored_tokens = result.scalars().all()

        # Find matching token by verifying hash
        valid_token = None
        for stored_token in stored_tokens:
            if verify_password(token_data.jti, stored_token.token_hash):
                valid_token = stored_token
                break

        if not valid_token:
            raise TokenError("Refresh token not found or revoked")

        # Revoke old refresh token
        valid_token.is_revoked = True
        valid_token.revoked_at = datetime.now(UTC)

        # Generate new tokens
        new_access_token = create_access_token(token_data.user_id)
        new_jti = secrets.token_urlsafe(32)
        new_refresh_token = create_refresh_token(token_data.user_id, new_jti)

        # Store new refresh token
        new_refresh_record = RefreshToken(
            user_id=token_data.user_id,
            token_hash=hash_password(new_jti),
            expires_at=get_token_expiry(TokenType.REFRESH),
        )
        self.session.add(new_refresh_record)

        await self.session.commit()

        return new_access_token, new_refresh_token

    async def logout(self, user_id: UUID, refresh_token: str | None = None) -> None:
        """Logout user by revoking refresh tokens.

        Args:
            user_id: User's ID
            refresh_token: Optional specific refresh token to revoke
        """
        if refresh_token:
            # Revoke specific token
            try:
                token_data = decode_token(refresh_token)
                if token_data.jti:
                    result = await self.session.execute(
                        select(RefreshToken).where(
                            RefreshToken.user_id == user_id,
                            RefreshToken.is_revoked == False,  # noqa: E712
                        )
                    )
                    for stored_token in result.scalars():
                        if verify_password(token_data.jti, stored_token.token_hash):
                            stored_token.is_revoked = True
                            stored_token.revoked_at = datetime.now(UTC)
                            break
            except Exception:
                pass  # Ignore invalid tokens on logout
        else:
            # Revoke all tokens for user
            result = await self.session.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
            )
            for token in result.scalars():
                token.is_revoked = True
                token.revoked_at = datetime.now(UTC)

        await self.session.commit()

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change user's password.

        Args:
            user: User object
            current_password: Current password for verification
            new_password: New password to set

        Raises:
            InvalidCredentialsError: If current password is wrong
        """
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()

        user.hashed_password = hash_password(new_password)

        # Revoke all refresh tokens (force re-login)
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
        )
        for token in result.scalars():
            token.is_revoked = True
            token.revoked_at = datetime.now(UTC)

        await self.session.commit()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User's UUID

        Returns:
            User object or None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User's email address

        Returns:
            User object or None
        """
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user: User,
        full_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        """Update user profile.

        Args:
            user: User object to update
            full_name: New full name (if provided)
            bio: New bio (if provided)
            avatar_url: New avatar URL (if provided)

        Returns:
            Updated User object
        """
        if full_name is not None:
            user.full_name = full_name
        if bio is not None:
            user.bio = bio
        if avatar_url is not None:
            user.avatar_url = avatar_url

        await self.session.commit()
        await self.session.refresh(user)

        return user
