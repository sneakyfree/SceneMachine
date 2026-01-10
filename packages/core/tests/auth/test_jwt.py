"""Tests for JWT token utilities."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from scenemachine.auth.jwt import (
    AuthenticationError,
    TokenData,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
)


class TestCreateAccessToken:
    """Test access token creation."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a JWT string."""
        user_id = uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_jwt_format(self):
        """Token should have JWT format (3 parts separated by dots)."""
        user_id = uuid4()
        token = create_access_token(user_id)
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_access_token_decodable(self):
        """Token should be decodable back to original data."""
        user_id = uuid4()
        token = create_access_token(user_id)
        data = decode_token(token)

        assert data.user_id == user_id
        assert data.token_type == TokenType.ACCESS

    def test_create_access_token_custom_expiry(self):
        """Token should support custom expiration."""
        user_id = uuid4()
        expires_delta = timedelta(hours=1)
        token = create_access_token(user_id, expires_delta=expires_delta)
        data = decode_token(token)

        # Check expiry is approximately 1 hour from now
        expected_exp = datetime.now(timezone.utc) + expires_delta
        assert abs((data.exp - expected_exp).total_seconds()) < 5

    def test_create_access_token_extra_claims(self):
        """Token should support extra claims."""
        user_id = uuid4()
        extra = {"role": "admin", "permissions": ["read", "write"]}
        token = create_access_token(user_id, extra_claims=extra)

        # Token should still decode
        data = decode_token(token)
        assert data.user_id == user_id


class TestCreateRefreshToken:
    """Test refresh token creation."""

    def test_create_refresh_token_returns_string(self):
        """create_refresh_token should return a JWT string."""
        user_id = uuid4()
        jti = "unique-id-123"
        token = create_refresh_token(user_id, jti)
        assert isinstance(token, str)

    def test_create_refresh_token_decodable(self):
        """Refresh token should be decodable."""
        user_id = uuid4()
        jti = "unique-id-456"
        token = create_refresh_token(user_id, jti)
        data = decode_token(token)

        assert data.user_id == user_id
        assert data.token_type == TokenType.REFRESH
        assert data.jti == jti

    def test_create_refresh_token_custom_expiry(self):
        """Refresh token should support custom expiration."""
        user_id = uuid4()
        jti = "unique-id-789"
        expires_delta = timedelta(days=30)
        token = create_refresh_token(user_id, jti, expires_delta=expires_delta)
        data = decode_token(token)

        expected_exp = datetime.now(timezone.utc) + expires_delta
        assert abs((data.exp - expected_exp).total_seconds()) < 5


class TestDecodeToken:
    """Test token decoding."""

    def test_decode_token_valid(self):
        """decode_token should return TokenData for valid token."""
        user_id = uuid4()
        token = create_access_token(user_id)
        data = decode_token(token)

        assert isinstance(data, TokenData)
        assert data.user_id == user_id
        assert data.token_type == TokenType.ACCESS
        assert isinstance(data.exp, datetime)
        assert isinstance(data.iat, datetime)

    def test_decode_token_invalid_format(self):
        """decode_token should raise AuthenticationError for invalid format."""
        with pytest.raises(AuthenticationError) as exc_info:
            decode_token("not-a-valid-token")
        assert "Invalid token" in str(exc_info.value.message)

    def test_decode_token_expired(self):
        """decode_token should raise AuthenticationError for expired token."""
        user_id = uuid4()
        # Create a token that expires immediately
        token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(token)
        assert "Invalid token" in str(exc_info.value.message)

    def test_decode_token_wrong_secret(self):
        """decode_token should fail with wrong secret."""
        user_id = uuid4()
        token = create_access_token(user_id)

        # Patch settings to use different secret
        with patch("scenemachine.auth.jwt.get_settings") as mock_settings:
            mock_settings.return_value.jwt_secret_key = "different-secret"
            mock_settings.return_value.jwt_algorithm = "HS256"

            with pytest.raises(AuthenticationError):
                decode_token(token)

    def test_decode_token_missing_claims(self):
        """decode_token should raise error for tokens missing required claims."""
        from jose import jwt as jose_jwt

        from scenemachine.config import get_settings

        settings = get_settings()

        # Create token without required claims
        invalid_token = jose_jwt.encode(
            {"foo": "bar"},  # Missing sub and type
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(invalid_token)
        assert "Invalid token payload" in str(exc_info.value.message)


class TestGetTokenExpiry:
    """Test token expiry calculation."""

    def test_get_token_expiry_access(self):
        """get_token_expiry should return future datetime for access token."""
        expiry = get_token_expiry(TokenType.ACCESS)
        assert isinstance(expiry, datetime)
        assert expiry > datetime.now(timezone.utc)

    def test_get_token_expiry_refresh(self):
        """get_token_expiry should return future datetime for refresh token."""
        expiry = get_token_expiry(TokenType.REFRESH)
        assert isinstance(expiry, datetime)
        assert expiry > datetime.now(timezone.utc)

    def test_refresh_expiry_longer_than_access(self):
        """Refresh token expiry should be longer than access token."""
        access_expiry = get_token_expiry(TokenType.ACCESS)
        refresh_expiry = get_token_expiry(TokenType.REFRESH)
        assert refresh_expiry > access_expiry


class TestTokenType:
    """Test TokenType enum."""

    def test_token_type_values(self):
        """TokenType should have expected values."""
        assert TokenType.ACCESS.value == "access"
        assert TokenType.REFRESH.value == "refresh"

    def test_token_type_string_conversion(self):
        """TokenType should convert to string."""
        assert str(TokenType.ACCESS) == "TokenType.ACCESS"


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_default_message(self):
        """AuthenticationError should have default message."""
        error = AuthenticationError()
        assert error.message == "Authentication failed"

    def test_authentication_error_custom_message(self):
        """AuthenticationError should accept custom message."""
        error = AuthenticationError("Custom error")
        assert error.message == "Custom error"
