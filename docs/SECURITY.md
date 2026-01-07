# SceneMachine Security Architecture

Comprehensive security documentation for the SceneMachine platform, covering API key encryption, rate limiting, security headers, request validation, and authentication.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Security Layers](#security-layers)
3. [API Key Encryption](#api-key-encryption)
4. [Rate Limiting](#rate-limiting)
5. [Security Headers](#security-headers)
6. [Request Validation](#request-validation)
7. [Authentication & Authorization](#authentication--authorization)
8. [Security Event Logging](#security-event-logging)
9. [Production Hardening Checklist](#production-hardening-checklist)
10. [Vulnerability Reporting](#vulnerability-reporting)

---

## Security Overview

SceneMachine implements defense-in-depth security with multiple protection layers. The security architecture is designed to:

- **Protect sensitive data** - API keys encrypted at rest using Fernet (AES-128-CBC)
- **Prevent abuse** - Multi-strategy rate limiting with token buckets and sliding windows
- **Block attacks** - Security headers prevent XSS, clickjacking, and MIME sniffing
- **Validate requests** - Size limits and user-agent filtering block malicious requests
- **Enable tracing** - Request IDs and security event logging for forensics

### Security Philosophy

1. **Defense in Depth** - Multiple independent security layers
2. **Fail Secure** - Default to denying access when uncertain
3. **Least Privilege** - Minimal permissions by default
4. **Audit Everything** - Log security-relevant events
5. **Secure by Default** - Production security enabled automatically

---

## Security Layers

Requests pass through multiple security middleware layers before reaching API endpoints:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Incoming Request                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Request ID Middleware                                          │
│  - Assigns unique X-Request-ID for tracing                      │
│  - Preserves existing ID if provided                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Rate Limiting Middleware (Production Only)                     │
│  - Token bucket for burst control                               │
│  - Sliding window for sustained rate limits                     │
│  - Per-client tracking (API key or IP)                          │
│  - Custom limits per endpoint                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Security Headers Middleware                                    │
│  - Content-Security-Policy                                      │
│  - X-Frame-Options, X-Content-Type-Options                      │
│  - HSTS (production only)                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Request Validation Middleware                                  │
│  - Max body size (100 MB)                                       │
│  - Max URL length (2048 chars)                                  │
│  - Blocked user agents (sqlmap, nikto, etc.)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CORS Middleware                                                │
│  - Origin validation                                            │
│  - Credential handling                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Endpoint                               │
└─────────────────────────────────────────────────────────────────┘
```

**Source:** `packages/core/scenemachine/api/app.py` (lines 119-152)

---

## API Key Encryption

All API keys stored in the database are encrypted at rest using Fernet symmetric encryption with PBKDF2 key derivation.

### Encryption Implementation

**Algorithm:** Fernet (AES-128-CBC with HMAC-SHA256)

**Key Derivation:**
- Algorithm: PBKDF2HMAC
- Hash: SHA-256
- Iterations: 480,000
- Salt: `scenemachine-settings-salt`
- Key length: 32 bytes (256 bits)

**Source:** `packages/core/scenemachine/models/settings.py` (lines 41-53)

### Encrypted Fields

The following API keys are encrypted when stored:

| Provider | Database Column | Property Accessor |
|----------|-----------------|-------------------|
| Anthropic | `anthropic_api_key` | `settings.anthropic_api_key` |
| OpenAI | `openai_api_key` | `settings.openai_api_key` |
| Replicate | `replicate_api_key` | `settings.replicate_api_key` |
| Fal.ai | `fal_api_key` | `settings.fal_api_key` |
| RunwayML | `runwayml_api_key` | `settings.runwayml_api_key` |

### How Encryption Works

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

def _get_encryption_key() -> bytes:
    """Derive encryption key from SECRET_KEY environment variable."""
    secret = os.environ.get("SECRET_KEY", "scenemachine-default-key-change-me")
    salt = b"scenemachine-settings-salt"

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))

def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value."""
    if not value:
        return ""
    key = _get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    """Decrypt a sensitive value."""
    if not encrypted:
        return ""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return ""
```

### Setting API Keys

API keys are automatically encrypted when set via property accessors:

```python
from scenemachine.models.settings import UserSettings

# Get settings from database
settings = await session.get(UserSettings, settings_id)

# Set API key - automatically encrypted before storage
settings.anthropic_api_key = "sk-ant-api..."

# Retrieve API key - automatically decrypted
key = settings.anthropic_api_key  # Returns decrypted value

# Check if key is configured
has_key = settings.has_api_key("anthropic")  # Returns True/False

# Get masked version for display
masked = settings.mask_api_key(settings.anthropic_api_key)  # "sk-a...pi03"
```

### SECRET_KEY Management

**Critical:** The `SECRET_KEY` environment variable is used to derive the encryption key. If this value changes, all encrypted API keys become unreadable.

**Best Practices:**

1. **Generate a strong key:**
   ```bash
   # Generate a cryptographically secure key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set in environment:**
   ```bash
   export SECRET_KEY="your-secure-random-key-here-minimum-32-chars"
   ```

3. **Never commit to version control** - Use environment variables or secrets management

4. **Backup securely** - Store the key in a secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)

5. **Rotate periodically** - When rotating, re-encrypt all API keys with the new key

### Key Rotation Procedure

1. Export all API keys (decrypted)
2. Set new `SECRET_KEY` environment variable
3. Restart application
4. Re-set all API keys via the Settings API

```bash
# 1. Get current keys (via API while old SECRET_KEY is active)
curl http://localhost:8000/api/v1/settings | jq '.apiKeys'

# 2. Update SECRET_KEY
export SECRET_KEY="new-secure-key-here"

# 3. Restart application
systemctl restart scenemachine

# 4. Re-set each API key
curl -X POST http://localhost:8000/api/v1/settings/api-keys \
  -H "Content-Type: application/json" \
  -d '{"provider": "anthropic", "api_key": "sk-ant-..."}'
```

---

## Rate Limiting

SceneMachine implements multi-strategy rate limiting to prevent abuse while allowing legitimate burst traffic.

### Rate Limiting Strategies

**1. Token Bucket (Per-Second with Burst)**

Allows short bursts of traffic while enforcing average rate:

```python
class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # Tokens added per second
        self.capacity = capacity  # Maximum tokens (burst)
        self.tokens = capacity
        self.last_update = time.monotonic()
```

- Tokens refill at `rate` per second
- Maximum `capacity` tokens can accumulate
- Each request consumes 1 token
- If tokens available → request allowed
- If no tokens → request denied with retry time

**2. Sliding Window Counter (Per-Minute and Per-Hour)**

Provides accurate rate limiting over longer windows:

```python
class SlidingWindowCounter:
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size    # Seconds
        self.max_requests = max_requests  # Max per window
        self.requests: List[float] = []   # Timestamps
```

- Tracks request timestamps within the window
- Removes expired timestamps on each check
- Provides smooth rate limiting without sharp edges

### Default Rate Limits

| Window | Limit | Burst | Notes |
|--------|-------|-------|-------|
| Per Second | 20 requests | 50 | Token bucket with burst |
| Per Minute | 200 requests | N/A | Sliding window |
| Per Hour | 2000 requests | N/A | Sliding window |

### Custom Endpoint Limits

High-resource endpoints have stricter limits:

| Endpoint Pattern | Limit | Window | Reason |
|------------------|-------|--------|--------|
| `/api/v1/generation` | 30 | 60s | GPU resource protection |
| `/api/v1/projects` | 60 | 60s | Database protection |

### Excluded Paths

These paths are not rate limited:

- `/health` - Health checks
- `/docs` - OpenAPI documentation
- `/openapi.json` - OpenAPI schema
- `/redoc` - ReDoc documentation

### Client Identification

Clients are identified for rate limiting in this priority order:

1. **API Key** - Hash of `X-API-Key` header (if present)
2. **IP Address** - From `X-Forwarded-For` header or direct connection

```python
def _get_client_id(self, request: Request) -> str:
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
```

### Rate Limit Response Headers

All responses include rate limit information:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Seconds until window resets |
| `Retry-After` | Seconds to wait before retrying (429 responses only) |

### Rate Limit Exceeded Response

When rate limited, clients receive HTTP 429:

```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED"
}
```

**Headers:**
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 45
Retry-After: 45
```

### Configuring Rate Limits

Rate limiting is configured in `app.py`:

```python
from scenemachine.api.middleware import RateLimitConfig, RateLimitMiddleware

# Only enabled in production (not debug mode)
if not settings.debug:
    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig(
            requests_per_second=20,
            requests_per_minute=200,
            requests_per_hour=2000,
            burst_size=50,
            custom_limits={
                "/api/v1/generation": (30, 60),  # 30 per minute
                "/api/v1/projects": (60, 60),    # 60 per minute
            },
            excluded_paths=["/health", "/docs", "/openapi.json", "/redoc"],
        ),
    )
```

**Source:** `packages/core/scenemachine/api/middleware/security.py` (lines 31-286)

---

## Security Headers

Security headers are added to all responses to protect against common web vulnerabilities.

### Headers Applied

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | See below | Prevents XSS, data injection |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer information |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Restricts browser features |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS (production only) |

### Content Security Policy

The default CSP policy:

```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:;
font-src 'self';
connect-src 'self' ws: wss:;
frame-ancestors 'none';
```

**Directive Breakdown:**

| Directive | Value | Purpose |
|-----------|-------|---------|
| `default-src` | `'self'` | Default to same-origin |
| `script-src` | `'self' 'unsafe-inline'` | Allow same-origin and inline scripts |
| `style-src` | `'self' 'unsafe-inline'` | Allow same-origin and inline styles |
| `img-src` | `'self' data: blob:` | Allow images from same-origin, data URIs, blobs |
| `font-src` | `'self'` | Fonts from same-origin only |
| `connect-src` | `'self' ws: wss:` | Allow same-origin + WebSocket connections |
| `frame-ancestors` | `'none'` | Prevent embedding in iframes |

### HSTS (HTTP Strict Transport Security)

HSTS is **only enabled in production** (when `debug=False`) to prevent accidental lockout during development.

**Configuration:**
- Max Age: 31,536,000 seconds (1 year)
- Include Subdomains: Yes

### Configuring Security Headers

```python
from scenemachine.api.middleware import SecurityHeadersConfig, SecurityHeadersMiddleware

app.add_middleware(
    SecurityHeadersMiddleware,
    config=SecurityHeadersConfig(
        csp_enabled=True,
        csp_policy="default-src 'self'; ...",
        x_content_type_options=True,
        x_frame_options="DENY",
        x_xss_protection=True,
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy="geolocation=(), camera=(), microphone=()",
        hsts_enabled=not settings.debug,  # Production only
        hsts_max_age=31536000,
        hsts_include_subdomains=True,
    ),
)
```

**Source:** `packages/core/scenemachine/api/middleware/security.py` (lines 331-402)

---

## Request Validation

The request validation middleware blocks malicious or oversized requests before they reach the application.

### Validation Rules

| Rule | Default Value | HTTP Status | Error Code |
|------|---------------|-------------|------------|
| Max Body Size | 100 MB | 413 | `BODY_TOO_LARGE` |
| Max URL Length | 2048 characters | 414 | `URL_TOO_LONG` |
| Blocked User Agents | See below | 403 | `FORBIDDEN` |

### Blocked User Agents

The following user agent strings are blocked:

- `sqlmap` - SQL injection tool
- `nikto` - Web vulnerability scanner
- `nmap` - Network scanner
- `masscan` - Port scanner

These are substring matches, so `Mozilla/5.0 (sqlmap)` would be blocked.

### Request Validation Response Examples

**Body Too Large (413):**
```json
{
  "error": "Request body too large",
  "code": "BODY_TOO_LARGE"
}
```

**URL Too Long (414):**
```json
{
  "error": "URL too long",
  "code": "URL_TOO_LONG"
}
```

**Blocked User Agent (403):**
```json
{
  "error": "Forbidden",
  "code": "FORBIDDEN"
}
```

### Configuring Request Validation

```python
from scenemachine.api.middleware import RequestValidationConfig, RequestValidationMiddleware

app.add_middleware(
    RequestValidationMiddleware,
    config=RequestValidationConfig(
        max_body_size=100 * 1024 * 1024,  # 100MB for video uploads
        max_url_length=2048,
        allowed_content_types=[
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
            "text/plain",
        ],
        blocked_user_agents=[
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
        ],
    ),
)
```

**Source:** `packages/core/scenemachine/api/middleware/security.py` (lines 410-482)

---

## Authentication & Authorization

SceneMachine currently implements API key authentication for external API access.

### API Key Authentication

**Header:** `X-API-Key`

**Authentication Flow:**

1. Client includes API key in request header
2. Middleware validates key against configured valid keys
3. If valid → request proceeds
4. If invalid/missing → 401 Unauthorized

### Using API Key Authentication

```python
from scenemachine.api.middleware.security import APIKeyAuth, require_api_key

# Initialize with valid keys
auth = APIKeyAuth(valid_keys=["your-api-key-here"])

# Add keys dynamically
auth.add_key("another-key")

# Remove keys
auth.remove_key("old-key")

# Protect an endpoint
@router.post("/protected-endpoint")
@require_api_key(auth)
async def protected_endpoint(request: Request):
    # Only accessible with valid API key
    return {"message": "Access granted"}
```

### Authentication Response

**Invalid or Missing API Key (401):**

```json
{
  "detail": "Invalid or missing API key"
}
```

**Headers:**
```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: API-Key
```

### Current Permission Model

SceneMachine is designed as a single-user desktop application. The current permission model:

- **Desktop App (Electron)** - Full access via IPC, no authentication required
- **Local REST API** - Rate limited, optional API key authentication
- **Production REST API** - Full authentication required (API key)

### Request Tracing

Every request is assigned a unique ID for tracing:

```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Use provided ID or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
```

**Headers:**
- Request: `X-Request-ID: optional-client-provided-id`
- Response: `X-Request-ID: uuid-used-for-this-request`

**Source:** `packages/core/scenemachine/api/middleware/security.py` (lines 490-529)

---

## Security Event Logging

Security-relevant events are logged for monitoring and forensics.

### Logged Events

| Event Type | Description | Log Level |
|------------|-------------|-----------|
| `rate_limit_exceeded` | Client exceeded rate limit | WARNING |
| `blocked_user_agent` | Suspicious user agent blocked | WARNING |
| `authentication_failed` | Invalid API key used | WARNING |
| `validation_failed` | Request validation failed | WARNING |

### Log Format

Security events are logged as structured JSON:

```json
{
  "event": "rate_limit_exceeded",
  "client_ip": "192.168.1.100",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "/api/v1/generation/queue",
  "method": "POST",
  "timestamp": "2026-01-06T12:00:00Z",
  "limit": 30,
  "window": 60
}
```

### Logging Utility

```python
from scenemachine.api.middleware.security import log_security_event

# Log a custom security event
log_security_event(
    event_type="suspicious_activity",
    request=request,
    details={
        "reason": "Multiple failed auth attempts",
        "attempt_count": 5,
    }
)
```

**Source:** `packages/core/scenemachine/api/middleware/security.py` (lines 545-567)

---

## Production Hardening Checklist

Before deploying SceneMachine to production, complete this security checklist:

### Critical (Must Do)

- [ ] **Set strong SECRET_KEY** - Minimum 32 characters, cryptographically random
  ```bash
  export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
  ```

- [ ] **Enable HTTPS** - Configure TLS certificates
  ```bash
  # Using Let's Encrypt
  certbot --nginx -d your-domain.com
  ```

- [ ] **Set DEBUG=False** - Enables rate limiting and HSTS
  ```bash
  export DEBUG=false
  ```

- [ ] **Configure CORS origins** - Restrict to known domains
  ```bash
  export CORS_ORIGINS="https://your-domain.com"
  ```

- [ ] **Secure database** - Strong password, restricted network access
  ```bash
  export DATABASE_URL="postgresql://user:strongpassword@localhost/scenemachine"
  ```

### Recommended

- [ ] **Configure firewall** - Only expose necessary ports (443, 80 for redirect)

- [ ] **Enable log aggregation** - Send security logs to SIEM

- [ ] **Set up monitoring alerts** - Alert on rate limit violations, auth failures

- [ ] **Regular security updates** - Keep dependencies updated

- [ ] **API key rotation schedule** - Rotate keys quarterly

- [ ] **Backup encryption keys** - Store SECRET_KEY in secure vault

### Optional

- [ ] **Custom rate limits** - Tune for your expected traffic

- [ ] **Additional blocked user agents** - Add known attack tools

- [ ] **Stricter CSP** - Remove `'unsafe-inline'` if possible

- [ ] **IP allowlisting** - Restrict API access to known IPs

---

## Vulnerability Reporting

If you discover a security vulnerability in SceneMachine, please report it responsibly.

### Reporting Process

1. **Do not** create a public GitHub issue for security vulnerabilities

2. **Email** security concerns to: [security@scenemachine.io] (or project maintainer)

3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

4. **Response timeline:**
   - Acknowledgment: Within 48 hours
   - Initial assessment: Within 7 days
   - Fix timeline: Depends on severity

### Severity Levels

| Level | Description | Example |
|-------|-------------|---------|
| Critical | Remote code execution, data breach | SQL injection, auth bypass |
| High | Significant data exposure | API key leak, IDOR |
| Medium | Limited impact | Rate limit bypass, XSS |
| Low | Minor issues | Information disclosure |

### Bug Bounty

Currently no formal bug bounty program. Responsible disclosure is appreciated and acknowledged in release notes.

---

## Related Documentation

- [Configuration Reference](CONFIGURATION.md) - Environment variables and settings
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Monitoring Guide](MONITORING.md) - Metrics and alerting setup
- [REST API Reference](api/REST-API.md) - API endpoint documentation
