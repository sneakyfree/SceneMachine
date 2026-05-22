"""Monitoring and Alerting Service for SceneMachine.

Provides:
- Sentry integration for error tracking
- Structured logging with correlation IDs
- Performance transaction tracing
- Slack/Discord webhook alerts
- Daily health digest
"""

import logging
import os
import sys
import time
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeVar
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


class AlertChannel(StrEnum):
    """Alert notification channels."""

    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"


class AlertSeverity(StrEnum):
    """Alert severity levels."""

    CRITICAL = "critical"  # System down, data loss risk
    ERROR = "error"  # Significant error affecting users
    WARNING = "warning"  # Potential issue, degraded service
    INFO = "info"  # Notable event, no action needed


@dataclass
class AlertConfig:
    """Configuration for alerts."""

    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None
    pagerduty_api_key: str | None = None
    email_smtp_host: str | None = None
    enabled_channels: list[AlertChannel] = field(default_factory=list)
    min_severity: AlertSeverity = AlertSeverity.WARNING


@dataclass
class MonitoringConfig:
    """Configuration for monitoring."""

    sentry_dsn: str | None = None
    environment: str = "development"
    release: str | None = None
    sample_rate: float = 1.0  # Transaction sampling rate
    enable_tracing: bool = True
    log_level: str = "INFO"
    alert_config: AlertConfig = field(default_factory=AlertConfig)


# =============================================================================
# Structured Logging
# =============================================================================


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def __init__(self) -> None:
        super().__init__()
        self._correlation_id: str | None = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set the correlation ID for current context."""
        self._correlation_id = correlation_id

    def clear_correlation_id(self) -> None:
        """Clear the correlation ID."""
        self._correlation_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to record."""
        record.correlation_id = self._correlation_id or "no-correlation"
        return True


class StructuredFormatter(logging.Formatter):
    """JSON-like structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "message",
                "correlation_id",
            ):
                log_data[key] = value

        import json

        return json.dumps(log_data)


def setup_logging(config: MonitoringConfig) -> logging.Logger:
    """Configure structured logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    handler.addFilter(correlation_filter)

    root_logger.addHandler(handler)

    return root_logger


# =============================================================================
# Sentry Integration
# =============================================================================


class SentryIntegration:
    """Sentry error tracking integration."""

    def __init__(self, config: MonitoringConfig) -> None:
        self.config = config
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Sentry SDK."""
        if not self.config.sentry_dsn:
            logger.info("Sentry DSN not configured, skipping initialization")
            return

        try:
            import sentry_sdk
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_sdk.init(
                dsn=self.config.sentry_dsn,
                environment=self.config.environment,
                release=self.config.release,
                traces_sample_rate=self.config.sample_rate if self.config.enable_tracing else 0,
                integrations=[
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR,
                    ),
                    AsyncioIntegration(),
                ],
                send_default_pii=False,
            )

            self._initialized = True
            logger.info("Sentry initialized successfully")

        except ImportError:
            logger.warning("sentry-sdk not installed, error tracking disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")

    def capture_exception(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Capture an exception in Sentry."""
        if not self._initialized:
            return

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)

                sentry_sdk.capture_exception(exception)

        except ImportError:
            pass

    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Capture a message in Sentry."""
        if not self._initialized:
            return

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)

                sentry_sdk.capture_message(message, level=level)

        except ImportError:
            pass

    def set_user(self, user_id: str, email: str | None = None) -> None:
        """Set user context for Sentry."""
        if not self._initialized:
            return

        try:
            import sentry_sdk

            sentry_sdk.set_user({"id": user_id, "email": email})
        except ImportError:
            pass


# =============================================================================
# Performance Tracing
# =============================================================================

T = TypeVar("T")


@dataclass
class TransactionContext:
    """Context for a performance transaction."""

    name: str
    op: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "ok"
    data: dict[str, Any] = field(default_factory=dict)
    spans: list["SpanContext"] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


@dataclass
class SpanContext:
    """Context for a performance span within a transaction."""

    name: str
    op: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "ok"
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


class PerformanceTracer:
    """Performance tracing for monitoring."""

    def __init__(self, config: MonitoringConfig) -> None:
        self.config = config
        self._current_transaction: TransactionContext | None = None

    @contextmanager
    def transaction(self, name: str, op: str = "task"):
        """Start a performance transaction."""
        transaction = TransactionContext(name=name, op=op)
        previous = self._current_transaction
        self._current_transaction = transaction

        try:
            yield transaction
            transaction.status = "ok"
        except Exception:
            transaction.status = "internal_error"
            raise
        finally:
            transaction.end_time = time.time()
            self._current_transaction = previous

            # Log transaction metrics
            logger.info(
                "Transaction completed",
                extra={
                    "transaction_name": name,
                    "transaction_op": op,
                    "duration_ms": transaction.duration_ms,
                    "status": transaction.status,
                    "span_count": len(transaction.spans),
                },
            )

    @contextmanager
    def span(self, name: str, op: str = "task"):
        """Start a performance span within current transaction."""
        span = SpanContext(name=name, op=op)

        if self._current_transaction:
            self._current_transaction.spans.append(span)

        try:
            yield span
            span.status = "ok"
        except Exception:
            span.status = "internal_error"
            raise
        finally:
            span.end_time = time.time()


# =============================================================================
# Alerting
# =============================================================================


@dataclass
class Alert:
    """An alert notification."""

    title: str
    message: str
    severity: AlertSeverity
    source: str = "scenemachine"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = field(default_factory=dict)
    alert_id: str = field(default_factory=lambda: str(uuid4()))


class AlertManager:
    """Manages alert notifications."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send_alert(self, alert: Alert) -> None:
        """Send alert to configured channels."""
        if alert.severity.value < self.config.min_severity.value:
            return

        tasks = []

        if AlertChannel.SLACK in self.config.enabled_channels:
            tasks.append(self._send_slack(alert))

        if AlertChannel.DISCORD in self.config.enabled_channels:
            tasks.append(self._send_discord(alert))

        if AlertChannel.PAGERDUTY in self.config.enabled_channels:
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR]:
                tasks.append(self._send_pagerduty(alert))

        import asyncio

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_slack(self, alert: Alert) -> None:
        """Send alert to Slack."""
        if not self.config.slack_webhook_url:
            return

        color_map = {
            AlertSeverity.CRITICAL: "#FF0000",
            AlertSeverity.ERROR: "#E74C3C",
            AlertSeverity.WARNING: "#F39C12",
            AlertSeverity.INFO: "#3498DB",
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#808080"),
                    "title": f"[{alert.severity.value.upper()}] {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Source", "value": alert.source, "short": True},
                        {"title": "Time", "value": alert.timestamp.isoformat(), "short": True},
                    ]
                    + [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in list(alert.context.items())[:4]
                    ],
                    "footer": f"Alert ID: {alert.alert_id}",
                }
            ]
        }

        try:
            response = await self._client.post(
                self.config.slack_webhook_url,
                json=payload,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    async def _send_discord(self, alert: Alert) -> None:
        """Send alert to Discord."""
        if not self.config.discord_webhook_url:
            return

        color_map = {
            AlertSeverity.CRITICAL: 0xFF0000,
            AlertSeverity.ERROR: 0xE74C3C,
            AlertSeverity.WARNING: 0xF39C12,
            AlertSeverity.INFO: 0x3498DB,
        }

        payload = {
            "embeds": [
                {
                    "title": f"[{alert.severity.value.upper()}] {alert.title}",
                    "description": alert.message,
                    "color": color_map.get(alert.severity, 0x808080),
                    "fields": [
                        {"name": k, "value": str(v), "inline": True}
                        for k, v in list(alert.context.items())[:6]
                    ],
                    "footer": {"text": f"Alert ID: {alert.alert_id}"},
                    "timestamp": alert.timestamp.isoformat(),
                }
            ]
        }

        try:
            response = await self._client.post(
                self.config.discord_webhook_url,
                json=payload,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

    async def _send_pagerduty(self, alert: Alert) -> None:
        """Send alert to PagerDuty."""
        if not self.config.pagerduty_api_key:
            return

        severity_map = {
            AlertSeverity.CRITICAL: "critical",
            AlertSeverity.ERROR: "error",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "info",
        }

        payload = {
            "routing_key": self.config.pagerduty_api_key,
            "event_action": "trigger",
            "dedup_key": alert.alert_id,
            "payload": {
                "summary": f"{alert.title}: {alert.message[:100]}",
                "severity": severity_map.get(alert.severity, "info"),
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "custom_details": alert.context,
            },
        }

        try:
            response = await self._client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")


# =============================================================================
# Health Check
# =============================================================================


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    healthy: bool
    latency_ms: float
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """System health checker."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], HealthCheckResult]] = {}

    def register_check(self, name: str, check_fn: Callable[[], HealthCheckResult]) -> None:
        """Register a health check function."""
        self._checks[name] = check_fn

    async def run_all_checks(self) -> dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}

        for name, check_fn in self._checks.items():
            start = time.time()
            try:
                import asyncio

                if asyncio.iscoroutinefunction(check_fn):
                    result = await check_fn()
                else:
                    result = check_fn()
                result.latency_ms = (time.time() - start) * 1000
            except Exception as e:
                result = HealthCheckResult(
                    name=name,
                    healthy=False,
                    latency_ms=(time.time() - start) * 1000,
                    message=str(e),
                )

            results[name] = result

        return results

    async def is_healthy(self) -> bool:
        """Check if all health checks pass."""
        results = await self.run_all_checks()
        return all(r.healthy for r in results.values())


# =============================================================================
# Monitoring Service
# =============================================================================


class MonitoringService:
    """Main monitoring service coordinating all monitoring features."""

    def __init__(self, config: MonitoringConfig | None = None) -> None:
        self.config = config or MonitoringConfig()

        self.sentry = SentryIntegration(self.config)
        self.tracer = PerformanceTracer(self.config)
        self.alert_manager = AlertManager(self.config.alert_config)
        self.health_checker = HealthChecker()

        self._correlation_filter: CorrelationIdFilter | None = None

    def initialize(self) -> None:
        """Initialize all monitoring components."""
        # Setup logging
        root_logger = setup_logging(self.config)

        # Get correlation filter from handlers
        for handler in root_logger.handlers:
            for filter_ in handler.filters:
                if isinstance(filter_, CorrelationIdFilter):
                    self._correlation_filter = filter_
                    break

        # Initialize Sentry
        self.sentry.initialize()

        logger.info(
            "Monitoring service initialized",
            extra={
                "environment": self.config.environment,
                "sentry_enabled": self.config.sentry_dsn is not None,
                "tracing_enabled": self.config.enable_tracing,
            },
        )

    @contextmanager
    def request_context(self, correlation_id: str | None = None):
        """Context manager for request-scoped monitoring."""
        correlation_id = correlation_id or str(uuid4())

        if self._correlation_filter:
            self._correlation_filter.set_correlation_id(correlation_id)

        try:
            yield correlation_id
        finally:
            if self._correlation_filter:
                self._correlation_filter.clear_correlation_id()

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Send an alert notification."""
        alert = Alert(
            title=title,
            message=message,
            severity=severity,
            context=context or {},
        )
        await self.alert_manager.send_alert(alert)


# =============================================================================
# Global Instance
# =============================================================================

_monitoring_service: MonitoringService | None = None


def get_monitoring_service() -> MonitoringService:
    """Get or create the global monitoring service."""
    global _monitoring_service

    if _monitoring_service is None:
        config = MonitoringConfig(
            sentry_dsn=os.environ.get("SENTRY_DSN"),
            environment=os.environ.get("ENVIRONMENT", "development"),
            release=os.environ.get("RELEASE_VERSION"),
            alert_config=AlertConfig(
                slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
                discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
                pagerduty_api_key=os.environ.get("PAGERDUTY_API_KEY"),
            ),
        )
        _monitoring_service = MonitoringService(config)
        _monitoring_service.initialize()

    return _monitoring_service
