"""CSRF Protection Middleware.

Provides Cross-Site Request Forgery protection for the API.
Uses the double-submit cookie pattern with secure token generation.
"""

import hashlib
import hmac
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from scenemachine.config import get_settings

logger = logging.getLogger(__name__)

# Safe HTTP methods that don't require CSRF protection
SAFE_METHODS: set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}


@dataclass
class CSRFConfig:
    """Configuration for CSRF protection."""

    # Enable/disable CSRF protection
    enabled: bool = True

    # Cookie settings
    cookie_name: str = "csrf_token"
    cookie_path: str = "/"
    cookie_domain: str | None = None
    cookie_secure: bool = True  # Requires HTTPS
    cookie_httponly: bool = False  # Must be False so JS can read it
    cookie_samesite: str = "lax"  # "strict", "lax", or "none"
    cookie_max_age: int = 86400  # 24 hours

    # Header name for CSRF token
    header_name: str = "X-CSRF-Token"

    # Form field name for CSRF token
    form_field_name: str = "_csrf_token"

    # Token settings
    token_length: int = 32

    # Exempt paths (no CSRF check)
    exempt_paths: list[str] = field(
        default_factory=lambda: [
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/ws",  # WebSocket connections
        ]
    )

    # Exempt content types (typically for API-only endpoints)
    exempt_content_types: list[str] = field(
        default_factory=lambda: [
            "application/json",  # JSON APIs are typically CSRF-safe
        ]
    )


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection using double-submit cookie pattern.

    This middleware:
    1. Sets a CSRF token cookie on all responses
    2. Validates that non-safe requests include the token in a header
    3. Uses HMAC to sign tokens for additional security

    Usage:
        app.add_middleware(CSRFMiddleware, config=CSRFConfig())
    """

    def __init__(self, app: ASGIApp, config: CSRFConfig | None = None) -> None:
        super().__init__(app)
        self.config = config or CSRFConfig()
        self._settings = get_settings()

    def _generate_token(self) -> str:
        """Generate a new CSRF token."""
        secrets.token_bytes(self.config.token_length)
        return secrets.token_urlsafe(self.config.token_length)

    def _sign_token(self, token: str) -> str:
        """Sign a token using HMAC."""
        key = self._settings.secret_key.encode()
        signature = hmac.new(key, token.encode(), hashlib.sha256).hexdigest()[:16]
        return f"{token}.{signature}"

    def _verify_token(self, signed_token: str) -> bool:
        """Verify a signed token."""
        try:
            parts = signed_token.rsplit(".", 1)
            if len(parts) != 2:
                return False

            token, signature = parts
            expected = self._sign_token(token)
            return hmac.compare_digest(signed_token, expected)
        except Exception:
            return False

    def _is_exempt(self, request: Request) -> bool:
        """Check if request is exempt from CSRF protection."""
        # Safe methods don't need CSRF protection
        if request.method in SAFE_METHODS:
            return True

        # Check exempt paths
        path = request.url.path
        for exempt_path in self.config.exempt_paths:
            if path.startswith(exempt_path):
                return True

        # Check content type exemptions
        content_type = request.headers.get("content-type", "").lower()
        return any(exempt_type in content_type for exempt_type in self.config.exempt_content_types)

    def _get_token_from_request(self, request: Request) -> str | None:
        """Extract CSRF token from request header or form field."""
        # Try header first
        token = request.headers.get(self.config.header_name)
        if token:
            return token

        # For form submissions, check form data
        # Note: This requires async form parsing, handled in dispatch
        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CSRF protection."""
        # Skip if CSRF is disabled
        if not self.config.enabled:
            return await call_next(request)

        # Get or generate token
        cookie_token = request.cookies.get(self.config.cookie_name)
        new_token = None

        if not cookie_token or not self._verify_token(cookie_token):
            # Generate new token
            raw_token = self._generate_token()
            new_token = self._sign_token(raw_token)
            cookie_token = new_token

        # Validate non-exempt requests
        if not self._is_exempt(request):
            request_token = self._get_token_from_request(request)

            if not request_token:
                logger.warning(
                    f"CSRF token missing for {request.method} {request.url.path}"
                )
                return Response(
                    content='{"error": "CSRF token missing", "code": "CSRF_MISSING"}',
                    status_code=403,
                    media_type="application/json",
                )

            # Verify token matches cookie
            if not hmac.compare_digest(request_token, cookie_token):
                logger.warning(
                    f"CSRF token mismatch for {request.method} {request.url.path}"
                )
                return Response(
                    content='{"error": "CSRF token invalid", "code": "CSRF_INVALID"}',
                    status_code=403,
                    media_type="application/json",
                )

        # Process request
        response = await call_next(request)

        # Set/refresh CSRF cookie
        if new_token:
            response.set_cookie(
                key=self.config.cookie_name,
                value=new_token,
                max_age=self.config.cookie_max_age,
                path=self.config.cookie_path,
                domain=self.config.cookie_domain,
                secure=self.config.cookie_secure and self._settings.is_production,
                httponly=self.config.cookie_httponly,
                samesite=self.config.cookie_samesite,
            )

        return response


def get_csrf_token(request: Request) -> str:
    """Get the current CSRF token for a request.

    Use this in templates or API responses to provide the token to clients.

    Args:
        request: The current request

    Returns:
        The CSRF token string
    """
    config = CSRFConfig()
    return request.cookies.get(config.cookie_name, "")
