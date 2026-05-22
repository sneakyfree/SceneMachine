"""Security middleware for the SceneMachine API.

Provides:
- Rate limiting with multiple strategies
- Security headers
- Request validation
- API key authentication
"""

import hashlib
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limiting
# ============================================================================


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Requests per time window
    requests_per_second: int = 10
    requests_per_minute: int = 100
    requests_per_hour: int = 1000

    # Burst allowance (extra requests allowed in short burst)
    burst_size: int = 20

    # Slow down threshold (after this many requests, add delay)
    slowdown_threshold: int = 50
    slowdown_delay_ms: int = 100

    # Endpoints with custom limits (path pattern -> (requests, seconds))
    custom_limits: dict[str, tuple[int, int]] = field(default_factory=dict)

    # Excluded paths (no rate limiting)
    excluded_paths: list[str] = field(
        default_factory=lambda: ["/health", "/docs", "/openapi.json", "/redoc"]
    )


class TokenBucket:
    """Token bucket for rate limiting with burst support."""

    def __init__(self, rate: float, capacity: int) -> None:
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Maximum tokens (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    def acquire(self, tokens: int = 1) -> tuple[bool, float]:
        """
        Try to acquire tokens.

        Returns:
            Tuple of (success, wait_time_seconds)
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        else:
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.rate
            return False, wait_time


class SlidingWindowCounter:
    """Sliding window counter for accurate rate limiting."""

    def __init__(self, window_size: int, max_requests: int) -> None:
        """
        Initialize sliding window counter.

        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests per window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: list[float] = []

    def acquire(self) -> tuple[bool, int]:
        """
        Try to acquire a request slot.

        Returns:
            Tuple of (success, current_count)
        """
        now = time.monotonic()
        window_start = now - self.window_size

        # Remove old requests
        self.requests = [t for t in self.requests if t > window_start]

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True, len(self.requests)
        else:
            return False, len(self.requests)

    def get_reset_time(self) -> float:
        """Get time until oldest request expires."""
        if not self.requests:
            return 0.0
        return max(0.0, self.requests[0] + self.window_size - time.monotonic())


class RateLimiter:
    """Multi-strategy rate limiter."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()

        # Per-client rate limiters
        self._buckets: dict[str, TokenBucket] = {}
        self._windows: dict[str, dict[str, SlidingWindowCounter]] = defaultdict(dict)

        # Cleanup tracking
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300  # 5 minutes

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def _get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create token bucket for client."""
        if client_id not in self._buckets:
            rate = self.config.requests_per_second
            self._buckets[client_id] = TokenBucket(rate, self.config.burst_size)
        return self._buckets[client_id]

    def _get_window(self, client_id: str, window_name: str) -> SlidingWindowCounter:
        """Get or create sliding window for client."""
        if window_name not in self._windows[client_id]:
            if window_name == "minute":
                self._windows[client_id][window_name] = SlidingWindowCounter(
                    60, self.config.requests_per_minute
                )
            elif window_name == "hour":
                self._windows[client_id][window_name] = SlidingWindowCounter(
                    3600, self.config.requests_per_hour
                )
        return self._windows[client_id][window_name]

    def _cleanup(self) -> None:
        """Cleanup old rate limit data."""
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now

        # Remove empty window counters
        empty_clients = []
        for client_id, windows in self._windows.items():
            for name, window in list(windows.items()):
                if not window.requests:
                    del windows[name]
            if not windows:
                empty_clients.append(client_id)

        for client_id in empty_clients:
            del self._windows[client_id]
            self._buckets.pop(client_id, None)

    def check(self, request: Request) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (allowed, limit_info)
        """
        # Check excluded paths
        path = request.url.path
        for excluded in self.config.excluded_paths:
            if path.startswith(excluded):
                return True, {}

        self._cleanup()

        client_id = self._get_client_id(request)

        # Check custom limits first
        for pattern, (max_requests, window_seconds) in self.config.custom_limits.items():
            if pattern in path:
                window = SlidingWindowCounter(window_seconds, max_requests)
                # Use a combined key for custom limits
                key = f"{client_id}:{pattern}"
                if key not in self._windows[client_id]:
                    self._windows[client_id][key] = window
                allowed, count = self._windows[client_id][key].acquire()
                if not allowed:
                    return False, {
                        "limit": max_requests,
                        "window": window_seconds,
                        "remaining": 0,
                        "reset": self._windows[client_id][key].get_reset_time(),
                    }

        # Check token bucket (per-second with burst)
        bucket = self._get_bucket(client_id)
        allowed, wait_time = bucket.acquire()
        if not allowed:
            return False, {
                "limit": self.config.requests_per_second,
                "window": 1,
                "remaining": 0,
                "retry_after": wait_time,
            }

        # Check minute window
        minute_window = self._get_window(client_id, "minute")
        allowed, count = minute_window.acquire()
        if not allowed:
            return False, {
                "limit": self.config.requests_per_minute,
                "window": 60,
                "remaining": 0,
                "reset": minute_window.get_reset_time(),
            }

        # Check hour window
        hour_window = self._get_window(client_id, "hour")
        allowed, count = hour_window.acquire()
        if not allowed:
            return False, {
                "limit": self.config.requests_per_hour,
                "window": 3600,
                "remaining": 0,
                "reset": hour_window.get_reset_time(),
            }

        # Calculate remaining
        remaining = min(
            self.config.requests_per_minute - len(minute_window.requests),
            self.config.requests_per_hour - len(hour_window.requests),
        )

        return True, {
            "limit": self.config.requests_per_minute,
            "remaining": remaining,
            "reset": minute_window.get_reset_time(),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""

    def __init__(self, app: ASGIApp, config: RateLimitConfig | None = None) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and process request."""
        allowed, limit_info = self.limiter.check(request)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {request.url.path}: {limit_info}")
            return Response(
                content='{"error": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(limit_info.get("reset", 0))),
                    "Retry-After": str(
                        int(limit_info.get("retry_after", limit_info.get("reset", 60)))
                    ),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        if limit_info:
            response.headers["X-RateLimit-Limit"] = str(limit_info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(limit_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(int(limit_info.get("reset", 0)))

        return response


# ============================================================================
# Security Headers
# ============================================================================


@dataclass
class SecurityHeadersConfig:
    """Configuration for security headers."""

    # Content Security Policy
    csp_enabled: bool = True
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )

    # Other security headers
    x_content_type_options: bool = True
    x_frame_options: str = "DENY"
    x_xss_protection: bool = True
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), camera=(), microphone=()"

    # HSTS (only enable in production with HTTPS)
    hsts_enabled: bool = False
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    def __init__(self, app: ASGIApp, config: SecurityHeadersConfig | None = None) -> None:
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Content Security Policy
        if self.config.csp_enabled:
            response.headers["Content-Security-Policy"] = self.config.csp_policy

        # X-Content-Type-Options
        if self.config.x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        if self.config.x_frame_options:
            response.headers["X-Frame-Options"] = self.config.x_frame_options

        # X-XSS-Protection (legacy but still useful)
        if self.config.x_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        if self.config.referrer_policy:
            response.headers["Referrer-Policy"] = self.config.referrer_policy

        # Permissions-Policy
        if self.config.permissions_policy:
            response.headers["Permissions-Policy"] = self.config.permissions_policy

        # HSTS
        if self.config.hsts_enabled:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value

        return response


# ============================================================================
# Request Validation
# ============================================================================


@dataclass
class RequestValidationConfig:
    """Configuration for request validation."""

    # Maximum request body size (bytes)
    max_body_size: int = 50 * 1024 * 1024  # 50MB

    # Maximum URL length
    max_url_length: int = 2048

    # Allowed content types
    allowed_content_types: list[str] = field(
        default_factory=lambda: [
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
            "text/plain",
        ]
    )

    # Block suspicious user agents
    blocked_user_agents: list[str] = field(
        default_factory=lambda: [
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
        ]
    )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation."""

    def __init__(self, app: ASGIApp, config: RequestValidationConfig | None = None) -> None:
        super().__init__(app)
        self.config = config or RequestValidationConfig()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request and process."""
        # Check URL length
        if len(str(request.url)) > self.config.max_url_length:
            return Response(
                content='{"error": "URL too long", "code": "URL_TOO_LONG"}',
                status_code=414,
                media_type="application/json",
            )

        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.config.max_body_size:
                    return Response(
                        content='{"error": "Request body too large", "code": "BODY_TOO_LARGE"}',
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass

        # Check user agent
        user_agent = request.headers.get("user-agent", "").lower()
        for blocked in self.config.blocked_user_agents:
            if blocked.lower() in user_agent:
                logger.warning(f"Blocked suspicious user agent: {user_agent}")
                return Response(
                    content='{"error": "Forbidden", "code": "FORBIDDEN"}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)


# ============================================================================
# API Key Authentication
# ============================================================================


class APIKeyAuth:
    """Simple API key authentication helper."""

    def __init__(self, valid_keys: list[str] | None = None) -> None:
        self.valid_keys = set(valid_keys or [])

    def add_key(self, key: str) -> None:
        """Add a valid API key."""
        self.valid_keys.add(key)

    def remove_key(self, key: str) -> None:
        """Remove an API key."""
        self.valid_keys.discard(key)

    def validate(self, key: str | None) -> bool:
        """Validate an API key."""
        if not self.valid_keys:
            # No keys configured, allow all
            return True
        return key in self.valid_keys


def require_api_key(auth: APIKeyAuth):
    """Decorator to require API key authentication."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            api_key = request.headers.get("X-API-Key")
            if not auth.validate(api_key):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or missing API key",
                    headers={"WWW-Authenticate": "API-Key"},
                )
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Utility Functions
# ============================================================================


def get_client_ip(request: Request) -> str:
    """Get the real client IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def log_security_event(
    event_type: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a security-related event."""
    client_ip = get_client_ip(request)
    request_id = getattr(request.state, "request_id", "unknown")

    log_data = {
        "event": event_type,
        "client_ip": client_ip,
        "request_id": request_id,
        "path": str(request.url.path),
        "method": request.method,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if details:
        log_data.update(details)

    logger.warning(f"Security event: {log_data}")
