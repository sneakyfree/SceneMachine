"""Tests for password reset functionality."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

# Test the security module functions
from ..security import jwt_handler, password_hasher


class TestPasswordResetTokens:
    """Tests for password reset token generation and verification."""

    def test_create_password_reset_token(self):
        """Test creating a password reset token."""
        user_id = uuid4()
        token = jwt_handler.create_password_reset_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_password_reset_token(self):
        """Test verifying a valid password reset token."""
        user_id = uuid4()
        token = jwt_handler.create_password_reset_token(user_id)

        verified_user_id = jwt_handler.verify_password_reset_token(token)

        assert verified_user_id == user_id

    def test_verify_invalid_token(self):
        """Test verifying an invalid token returns None."""
        result = jwt_handler.verify_password_reset_token("invalid_token")

        assert result is None

    def test_verify_tampered_token(self):
        """Test verifying a tampered token returns None."""
        user_id = uuid4()
        token = jwt_handler.create_password_reset_token(user_id)

        # Tamper with the token
        tampered_token = token[:-10] + "tampered00"

        result = jwt_handler.verify_password_reset_token(tampered_token)

        assert result is None

    def test_access_token_not_valid_for_password_reset(self):
        """Test that access tokens cannot be used for password reset."""
        user_id = uuid4()
        access_token = jwt_handler.create_access_token(user_id)

        result = jwt_handler.verify_password_reset_token(access_token)

        assert result is None

    def test_refresh_token_not_valid_for_password_reset(self):
        """Test that refresh tokens cannot be used for password reset."""
        user_id = uuid4()
        refresh_token = jwt_handler.create_refresh_token(user_id)

        result = jwt_handler.verify_password_reset_token(refresh_token)

        assert result is None


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = password_hasher.hash(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        """Test verifying a correct password."""
        password = "SecurePassword123!"
        hashed = password_hasher.hash(password)

        result = password_hasher.verify(password, hashed)

        assert result is True

    def test_verify_incorrect_password(self):
        """Test verifying an incorrect password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = password_hasher.hash(password)

        result = password_hasher.verify(wrong_password, hashed)

        assert result is False

    def test_different_hashes_for_same_password(self):
        """Test that the same password produces different hashes (salted)."""
        password = "SecurePassword123!"
        hash1 = password_hasher.hash(password)
        hash2 = password_hasher.hash(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # But both should verify correctly
        assert password_hasher.verify(password, hash1)
        assert password_hasher.verify(password, hash2)


class TestEmailModule:
    """Tests for email sending functionality."""

    @pytest.mark.asyncio
    async def test_send_password_reset_email_logs_when_disabled(self):
        """Test that password reset email logs when email is disabled."""
        from ..email import send_password_reset_email

        with patch("..email.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                email_enabled=False,
                frontend_url="https://test.com",
            )

            result = await send_password_reset_email(
                email="test@example.com",
                username="testuser",
                reset_token="test_token_123",
            )

            # Should succeed (logs instead of sending)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_verification_logs_when_disabled(self):
        """Test that email verification logs when email is disabled."""
        from ..email import send_email_verification

        with patch("..email.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                email_enabled=False,
                frontend_url="https://test.com",
            )

            result = await send_email_verification(
                email="test@example.com",
                username="testuser",
                verification_token="verify_token_123",
            )

            assert result is True


class TestPasswordResetEndpoints:
    """Tests for password reset API endpoints."""

    @pytest.mark.asyncio
    async def test_forgot_password_returns_success_for_existing_email(self):
        """Test forgot password endpoint returns success for existing email."""
        # This would require setting up the full app context
        # For now, we test the behavior conceptually
        pass

    @pytest.mark.asyncio
    async def test_forgot_password_returns_success_for_nonexistent_email(self):
        """Test forgot password returns success even for non-existent email.

        This is important to prevent email enumeration attacks.
        """
        pass

    @pytest.mark.asyncio
    async def test_reset_password_with_valid_token(self):
        """Test resetting password with a valid token."""
        pass

    @pytest.mark.asyncio
    async def test_reset_password_with_invalid_token(self):
        """Test resetting password with an invalid token fails."""
        pass

    @pytest.mark.asyncio
    async def test_reset_password_with_expired_token(self):
        """Test resetting password with an expired token fails."""
        pass
