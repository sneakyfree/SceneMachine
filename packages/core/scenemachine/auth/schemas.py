"""
Authentication Schemas

Pydantic schemas for authentication requests and responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=200)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        if v.startswith("_") or v.startswith("-"):
            raise ValueError("Username cannot start with underscore or hyphen")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for token endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: UUID
    email: str
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile."""

    full_name: str | None = Field(None, max_length=200)
    bio: str | None = Field(None, max_length=1000)
    avatar_url: str | None = Field(None, max_length=500)


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetRequest(BaseModel):
    """Request schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request schema for confirming password reset."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True
