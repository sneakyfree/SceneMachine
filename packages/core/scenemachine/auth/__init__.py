"""
SceneMachine Authentication Module

Provides JWT-based authentication, password hashing, and user management.
"""

from scenemachine.auth.password import hash_password, verify_password
from scenemachine.auth.jwt import (
    AuthenticationError,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
    TokenData,
    TokenType,
)
from scenemachine.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    CurrentUser,
    CurrentActiveUser,
    OptionalUser,
)
from scenemachine.auth.schemas import (
    MessageResponse,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from scenemachine.auth.service import (
    AccountLockedError,
    AuthService,
    AuthServiceError,
    InvalidCredentialsError,
    TokenError,
    UserExistsError,
)

__all__ = [
    # Password
    "hash_password",
    "verify_password",
    # JWT
    "AuthenticationError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_token_expiry",
    "TokenData",
    "TokenType",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "CurrentUser",
    "CurrentActiveUser",
    "OptionalUser",
    # Schemas
    "MessageResponse",
    "PasswordChangeRequest",
    "PasswordResetConfirm",
    "PasswordResetRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserLoginRequest",
    "UserRegisterRequest",
    "UserResponse",
    "UserUpdateRequest",
    # Service
    "AccountLockedError",
    "AuthService",
    "AuthServiceError",
    "InvalidCredentialsError",
    "TokenError",
    "UserExistsError",
]
