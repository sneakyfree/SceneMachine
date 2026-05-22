"""SceneMachine Security Module.

Provides security utilities including:
- Secrets management
- Audit logging
- Input sanitization
- Security validation
"""

from scenemachine.security.audit import (
    AuditEvent,
    AuditEventType,
    AuditLog,
    get_audit_logger,
    log_auth_event,
    log_security_event,
)
from scenemachine.security.secrets import (
    EnvironmentSecretProvider,
    FileSecretProvider,
    SecretProvider,
    SecretsManager,
    get_secrets_manager,
    mask_secret,
)
from scenemachine.security.validation import (
    is_safe_redirect,
    sanitize_filename,
    sanitize_html,
    validate_email,
    validate_url,
)

__all__ = [
    # Secrets
    "SecretsManager",
    "SecretProvider",
    "EnvironmentSecretProvider",
    "FileSecretProvider",
    "get_secrets_manager",
    "mask_secret",
    # Audit
    "AuditLog",
    "AuditEvent",
    "AuditEventType",
    "get_audit_logger",
    "log_auth_event",
    "log_security_event",
    # Validation
    "sanitize_filename",
    "sanitize_html",
    "validate_email",
    "validate_url",
    "is_safe_redirect",
]
