"""API middleware modules."""

from scenemachine.api.middleware.csrf import (
    CSRFConfig,
    CSRFMiddleware,
    get_csrf_token,
)
from scenemachine.api.middleware.security import (
    # API key auth
    APIKeyAuth,
    # Rate limiting
    RateLimitConfig,
    RateLimiter,
    RateLimitMiddleware,
    # Request validation
    RequestValidationConfig,
    RequestValidationMiddleware,
    # Security headers
    SecurityHeadersConfig,
    SecurityHeadersMiddleware,
    SlidingWindowCounter,
    TokenBucket,
    # Utilities
    get_client_ip,
    log_security_event,
    require_api_key,
)

__all__ = [
    # Rate limiting
    "RateLimitConfig",
    "RateLimiter",
    "RateLimitMiddleware",
    "TokenBucket",
    "SlidingWindowCounter",
    # Security headers
    "SecurityHeadersConfig",
    "SecurityHeadersMiddleware",
    # Request validation
    "RequestValidationConfig",
    "RequestValidationMiddleware",
    # API key auth
    "APIKeyAuth",
    "require_api_key",
    # CSRF protection
    "CSRFConfig",
    "CSRFMiddleware",
    "get_csrf_token",
    # Utilities
    "get_client_ip",
    "log_security_event",
]
