# SceneMachine Security Audit Report

**Date**: 2026-02-08
**Revised**: 2026-02-16
**Auditor**: Automated + Manual Code Review
**Scope**: Full backend (`packages/core/scenemachine/`)

---

## Executive Summary

SceneMachine's security posture is **strong**. All critical areas have defense-in-depth protections. No critical vulnerabilities were found during this audit.

| Category | Status | Rating |
|----------|--------|--------|
| Authentication | ✅ Hardened | 9/10 |
| Authorization | ✅ Role-based | 8/10 |
| Input Validation | ✅ Layered | 9/10 |
| File Upload Security | ✅ Validated | 9/10 |
| SQL Injection | ✅ ORM-only | 10/10 |
| CORS / CSRF | ✅ Configured | 8/10 |
| Rate Limiting | ✅ Active | 8/10 |
| Dependency Security | ⚠️ Needs audit | 6/10 |

---

## Authentication (FEAT-006)

### Findings ✅

| Control | Implementation | File |
|---------|---------------|------|
| Password hashing | bcrypt via `passlib` | `auth/password.py` |
| JWT access tokens | Configurable expiry (`jwt_access_token_expire_minutes`) | `auth/jwt.py` |
| JWT refresh tokens | Separate expiry (`jwt_refresh_token_expire_days`) | `auth/jwt.py` |
| Token signing | `jwt_secret_key` from `Settings` (env var) | `auth/jwt.py` |
| Refresh rotation | Old token revoked, new token issued | `auth/service.py` |
| Logout invalidation | Refresh token revoked on logout | `auth/service.py` |
| Account lockout | 5 failed attempts → 15 min lock | `auth/service.py` |
| Lockout HTTP response | HTTP 429 Too Many Requests | `api/routes/auth.py` |

### Recommendations

- [ ] Set `JWT_SECRET_KEY` to a strong random value in production (≥256 bits)
- [ ] Consider reducing `jwt_access_token_expire_minutes` to 15 for sensitive deployments
- [ ] Add `iss` (issuer) and `aud` (audience) claims to JWTs for multi-service setups

---

## Input Validation & File Uploads

### Findings ✅

| Control | Location | Details |
|---------|----------|---------|
| File type validation | `ALLOWED_EXTENSIONS` in `ipc/handlers.py`, `api/routes/watermarks.py` | Whitelist of allowed extensions |
| File size limits | `MAX_FILE_SIZE` (100MB audio, 5MB watermarks) | Hard limits enforced |
| Path traversal prevention | `contains_path_traversal()` in `security/validation.py` | Checks `..`, `//`, encoded variants |
| Filename sanitization | `sanitize_filename()` in `security/validation.py` | Strips path separators |
| Request validation middleware | `RequestValidationMiddleware` in `api/app.py` | Body size limits |

### Recommendations

- [ ] Add MIME type validation (not just extension check) for uploaded files
- [ ] Add virus/malware scanning for uploaded media in production

---

## SQL Injection Prevention

### Findings ✅

**All database queries use SQLAlchemy ORM** — no raw SQL strings found in application code. The only `text()` usage is for health checks (`SELECT 1`).

---

## CORS & CSRF

### Findings ✅

| Control | Configuration |
|---------|--------------|
| CORS | `CORSMiddleware` with `settings.cors_origins` (configurable per environment) |
| CSRF | `CSRFMiddleware` mounted in `api/app.py` |
| Security Headers | `SecurityHeadersMiddleware` in `api/app.py` |

### Recommendations

- [ ] Ensure `cors_origins` does NOT contain `*` in production
- [ ] Verify `Strict-Transport-Security` header is set for HTTPS deployments

---

## Rate Limiting

### Findings ✅

- Rate limiting middleware is mounted in `api/app.py`
- Security audit events tracked via `security/audit.py` (`SECURITY_RATE_LIMIT`)
- Account lockout provides additional brute-force protection

### Recommendations

- [ ] Configure per-endpoint rate limits (stricter for `/auth/login`, `/auth/register`)
- [ ] Add IP-based rate limiting for unauthenticated endpoints

---

## Dependency Security

### Action Required ⚠️

Run the following commands to check for known vulnerabilities:

```bash
# Python dependencies
pip-audit --requirement packages/core/requirements.txt

# Frontend dependencies
cd apps/desktop && npm audit
```

### Recommendations

- [ ] Run `pip-audit` and `npm audit` before each release
- [ ] Add dependency audit step to CI pipeline
- [ ] Pin all production dependencies to specific versions

---

## Monitoring & Observability

### Findings ✅

| Control | Implementation |
|---------|---------------|
| Prometheus metrics | `/metrics` endpoint with 8 metric families |
| Health checks | `/api/health` with DB, storage, provider checks |
| Structured logging | `logging` throughout with consistent patterns |
| Audit trail | `security/audit.py` with event tracking |
| Circuit breakers | `utils/circuit_breaker.py` with state monitoring |

---

## Summary of Recommendations

### High Priority
1. Set strong `JWT_SECRET_KEY` in production environment
2. Run `pip-audit` and `npm audit` before launch
3. Verify `cors_origins` is restrictive in production

### Medium Priority
4. Add MIME type validation for file uploads
5. Configure per-endpoint rate limits
6. Add `iss`/`aud` claims to JWTs

### Low Priority
7. Add virus scanning for uploaded media
8. Set up Prometheus Alertmanager for security events
