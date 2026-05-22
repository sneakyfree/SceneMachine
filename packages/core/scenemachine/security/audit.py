"""Audit Logging Module.

Provides structured audit logging for security-relevant events.
Useful for compliance, debugging, and security monitoring.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("scenemachine.audit")


class AuditEventType(StrEnum):
    """Types of audit events."""

    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_PASSWORD_CHANGE = "auth.password.change"
    AUTH_PASSWORD_RESET_REQUEST = "auth.password.reset.request"
    AUTH_PASSWORD_RESET_COMPLETE = "auth.password.reset.complete"
    AUTH_ACCOUNT_LOCKED = "auth.account.locked"
    AUTH_ACCOUNT_UNLOCKED = "auth.account.unlocked"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role.changed"

    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_DELETED = "project.deleted"
    PROJECT_SHARED = "project.shared"
    PROJECT_EXPORT = "project.export"

    # Security events
    SECURITY_CSRF_FAILURE = "security.csrf.failure"
    SECURITY_RATE_LIMIT = "security.rate_limit"
    SECURITY_BLOCKED_REQUEST = "security.blocked"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious"
    SECURITY_API_KEY_CREATED = "security.api_key.created"
    SECURITY_API_KEY_REVOKED = "security.api_key.revoked"

    # Data events
    DATA_ACCESS = "data.access"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"

    # System events
    SYSTEM_CONFIG_CHANGED = "system.config.changed"
    SYSTEM_ERROR = "system.error"


@dataclass
class AuditEvent:
    """Represents an audit event."""

    event_type: AuditEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))

    # Actor information
    user_id: str | None = None
    user_email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    # Request context
    request_id: str | None = None
    method: str | None = None
    path: str | None = None

    # Event details
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    outcome: str = "success"  # "success", "failure", "error"
    message: str | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLog:
    """Audit logging handler.

    Records security-relevant events in a structured format.
    Supports multiple output handlers (logging, file, database).
    """

    def __init__(self) -> None:
        self._handlers: list[Callable[[AuditEvent], None]] = []
        # Add default logging handler
        self._handlers.append(self._log_handler)

    def _log_handler(self, event: AuditEvent) -> None:
        """Default handler that logs events."""
        log_level = logging.INFO
        if event.outcome == "failure":
            log_level = logging.WARNING
        elif event.outcome == "error":
            log_level = logging.ERROR

        logger.log(
            log_level,
            f"AUDIT: {event.event_type.value} - {event.to_json()}"
        )

    def add_handler(self, handler: Callable[[AuditEvent], None]) -> None:
        """Add a custom audit event handler.

        Args:
            handler: Callable that receives AuditEvent
        """
        self._handlers.append(handler)

    def log(self, event: AuditEvent) -> None:
        """Log an audit event.

        Args:
            event: The audit event to log
        """
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Audit handler error: {e}")

    def log_event(
        self,
        event_type: AuditEventType,
        *,
        user_id: str | None = None,
        user_email: str | None = None,
        ip_address: str | None = None,
        request: Request | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        outcome: str = "success",
        message: str | None = None,
        **metadata: Any,
    ) -> AuditEvent:
        """Log an audit event with convenience parameters.

        Args:
            event_type: Type of event
            user_id: ID of user performing action
            user_email: Email of user
            ip_address: Client IP address
            request: FastAPI Request object (extracts context automatically)
            resource_type: Type of resource being accessed
            resource_id: ID of resource
            outcome: "success", "failure", or "error"
            message: Human-readable message
            **metadata: Additional metadata

        Returns:
            The created AuditEvent
        """
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            message=message,
            metadata=metadata,
        )

        # Extract request context if provided
        if request:
            event.request_id = getattr(request.state, "request_id", None)
            event.method = request.method
            event.path = str(request.url.path)
            event.user_agent = request.headers.get("user-agent")

            if not ip_address:
                forwarded = request.headers.get("x-forwarded-for")
                if forwarded:
                    event.ip_address = forwarded.split(",")[0].strip()
                elif request.client:
                    event.ip_address = request.client.host

        self.log(event)
        return event


# Global instance
_audit_logger: AuditLog | None = None


def get_audit_logger() -> AuditLog:
    """Get the global audit logger instance.

    Returns:
        The AuditLog instance
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLog()

    return _audit_logger


# Convenience functions


def log_auth_event(
    event_type: AuditEventType,
    user_id: str | None = None,
    user_email: str | None = None,
    request: Request | None = None,
    outcome: str = "success",
    message: str | None = None,
    **metadata: Any,
) -> AuditEvent:
    """Log an authentication-related event.

    Args:
        event_type: Type of auth event
        user_id: User ID
        user_email: User email
        request: Request object
        outcome: Event outcome
        message: Description
        **metadata: Additional data

    Returns:
        The created AuditEvent
    """
    return get_audit_logger().log_event(
        event_type,
        user_id=user_id,
        user_email=user_email,
        request=request,
        outcome=outcome,
        message=message,
        **metadata,
    )


def log_security_event(
    event_type: AuditEventType,
    request: Request | None = None,
    outcome: str = "failure",
    message: str | None = None,
    **metadata: Any,
) -> AuditEvent:
    """Log a security-related event.

    Args:
        event_type: Type of security event
        request: Request object
        outcome: Event outcome
        message: Description
        **metadata: Additional data

    Returns:
        The created AuditEvent
    """
    return get_audit_logger().log_event(
        event_type,
        request=request,
        outcome=outcome,
        message=message,
        **metadata,
    )
