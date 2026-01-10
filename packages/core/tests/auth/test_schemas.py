"""Tests for authentication schemas."""

import pytest
from pydantic import ValidationError

from scenemachine.auth.schemas import (
    PasswordChangeRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserUpdateRequest,
)


class TestUserRegisterRequest:
    """Test user registration schema."""

    def test_valid_registration(self):
        """Valid registration data should pass validation."""
        data = UserRegisterRequest(
            email="test@example.com",
            username="testuser",
            password="Password123",
            full_name="Test User",
        )
        assert data.email == "test@example.com"
        assert data.username == "testuser"
        assert data.password == "Password123"

    def test_username_lowercase(self):
        """Username should be converted to lowercase."""
        data = UserRegisterRequest(
            email="test@example.com",
            username="TestUser",
            password="Password123",
        )
        assert data.username == "testuser"

    def test_invalid_email(self):
        """Invalid email should fail validation."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="not-an-email",
                username="testuser",
                password="Password123",
            )

    def test_username_too_short(self):
        """Username shorter than 3 chars should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="ab",
                password="Password123",
            )

    def test_username_too_long(self):
        """Username longer than 50 chars should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="a" * 51,
                password="Password123",
            )

    def test_username_invalid_chars(self):
        """Username with invalid characters should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="test@user",  # @ is not allowed
                password="Password123",
            )

    def test_username_starts_with_underscore(self):
        """Username starting with underscore should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="_testuser",
                password="Password123",
            )

    def test_username_starts_with_hyphen(self):
        """Username starting with hyphen should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="-testuser",
                password="Password123",
            )

    def test_username_with_underscore_allowed(self):
        """Username with underscore in middle should pass."""
        data = UserRegisterRequest(
            email="test@example.com",
            username="test_user",
            password="Password123",
        )
        assert data.username == "test_user"

    def test_password_too_short(self):
        """Password shorter than 8 chars should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="testuser",
                password="Pass1",
            )

    def test_password_no_uppercase(self):
        """Password without uppercase should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="testuser",
                password="password123",
            )

    def test_password_no_lowercase(self):
        """Password without lowercase should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="testuser",
                password="PASSWORD123",
            )

    def test_password_no_digit(self):
        """Password without digit should fail."""
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                username="testuser",
                password="Passworddd",
            )


class TestUserLoginRequest:
    """Test user login schema."""

    def test_valid_login(self):
        """Valid login data should pass validation."""
        data = UserLoginRequest(
            email="test@example.com",
            password="anypassword",
        )
        assert data.email == "test@example.com"
        assert data.password == "anypassword"

    def test_invalid_email(self):
        """Invalid email should fail validation."""
        with pytest.raises(ValidationError):
            UserLoginRequest(
                email="not-an-email",
                password="password",
            )


class TestPasswordChangeRequest:
    """Test password change schema."""

    def test_valid_password_change(self):
        """Valid password change should pass validation."""
        data = PasswordChangeRequest(
            current_password="OldPassword123",
            new_password="NewPassword456",
        )
        assert data.current_password == "OldPassword123"
        assert data.new_password == "NewPassword456"

    def test_new_password_validation(self):
        """New password should meet strength requirements."""
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password="OldPassword123",
                new_password="weak",  # Too short, no uppercase, no digit
            )


class TestUserUpdateRequest:
    """Test user update schema."""

    def test_valid_update(self):
        """Valid update data should pass validation."""
        data = UserUpdateRequest(
            full_name="New Name",
            bio="This is my bio",
            avatar_url="https://example.com/avatar.png",
        )
        assert data.full_name == "New Name"

    def test_all_fields_optional(self):
        """All fields should be optional."""
        data = UserUpdateRequest()
        assert data.full_name is None
        assert data.bio is None
        assert data.avatar_url is None

    def test_bio_max_length(self):
        """Bio exceeding max length should fail."""
        with pytest.raises(ValidationError):
            UserUpdateRequest(bio="a" * 1001)
