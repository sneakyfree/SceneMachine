"""
Pydantic schemas for auth service requests and responses.
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# Validation patterns
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
PASSWORD_MIN_LENGTH = 8


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    display_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_PATTERN.match(v):
            raise ValueError(
                "Username must be 3-30 characters and contain only "
                "letters, numbers, and underscores"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
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
    """Response schema for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: uuid.UUID
    email: str
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_verified: bool
    is_creator: bool
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password."""

    current_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetRequest(BaseModel):
    """Request schema for initiating password reset."""

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Request schema for confirming password reset."""

    token: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class EmailVerifyRequest(BaseModel):
    """Request schema for email verification."""

    token: str


class StudioLinkRequest(BaseModel):
    """Request schema for linking Studio license."""

    license_key: str = Field(..., min_length=10)


class StudioLinkResponse(BaseModel):
    """Response schema for Studio link status."""

    linked: bool
    linked_at: Optional[datetime] = None
    license_key: Optional[str] = None  # Masked for security


class CreatorProfileResponse(BaseModel):
    """Response schema for creator profile."""

    channel_name: str
    channel_description: Optional[str] = None
    channel_banner_url: Optional[str] = None
    monetization_enabled: bool
    subscriber_count: int
    total_views: int
    video_count: int
    current_tier: int
    creator_cut_percent: float

    class Config:
        from_attributes = True


class CreatorProfileUpdateRequest(BaseModel):
    """Request schema for updating creator profile."""

    channel_name: Optional[str] = Field(None, min_length=3, max_length=100)
    channel_description: Optional[str] = Field(None, max_length=1000)
    channel_banner_url: Optional[str] = Field(None, max_length=500)


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True
