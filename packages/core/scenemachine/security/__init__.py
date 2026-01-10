"""SceneMachine Security Module.

Provides security utilities including:
- Secrets management
- Audit logging
- Input sanitization
- Security validation
"""

from scenemachine.security.secrets import (
    SecretsManager,
    SecretProvider,
    EnvironmentSecretProvider,
    FileSecretProvider,
    get_secrets_manager,
    mask_secret,
)
from scenemachine.security.audit import (
    AuditLog,
    AuditEvent,
    AuditEventType,
    get_audit_logger,
    log_auth_event,
    log_security_event,
)
from scenemachine.security.validation import (
    sanitize_filename,
    sanitize_html,
    validate_email,
    validate_url,
    is_safe_redirect,
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
