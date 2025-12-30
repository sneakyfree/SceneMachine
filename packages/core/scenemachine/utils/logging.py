"""Structured logging configuration for SceneMachine.

Provides JSON-formatted logging for production and human-readable
logs for development.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the formatter with optional extra fields."""
        super().__init__()
        self.extra_fields = kwargs

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
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
                "thread",
                "threadName",
                "taskName",
                "message",
            }:
                log_data[key] = value

        # Add configured extra fields
        log_data.update(self.extra_fields)

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Build the message
        msg = f"{timestamp} | {record.levelname:18} | {record.name}: {record.getMessage()}"

        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"

        return msg


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    service_name: str = "scenemachine",
    version: str = "0.1.0",
) -> None:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (for production)
        service_name: Service name for log context
        version: Application version
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if json_format:
        formatter = JSONFormatter(service=service_name, version=version)
    else:
        formatter = ColoredFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured",
        extra={
            "log_level": level,
            "json_format": json_format,
            "service": service_name,
            "version": version,
        },
    )


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter with context support."""

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Add extra context to log messages."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str, **context: Any) -> LoggerAdapter:
    """Get a logger with optional context.

    Args:
        name: Logger name (usually __name__)
        **context: Extra context to include in all log messages

    Returns:
        Logger adapter with context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)


# Request logging middleware
class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests."""

    def __init__(self, app: Any) -> None:
        """Initialize middleware."""
        self.app = app
        self.logger = logging.getLogger("scenemachine.requests")

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Process request and log details."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        start_time = time.time()

        # Track response status
        status_code = 500

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = (time.time() - start_time) * 1000

            # Log request
            self.logger.info(
                f"{scope['method']} {scope['path']} {status_code}",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "query_string": scope.get("query_string", b"").decode(),
                    "status_code": status_code,
                    "duration_ms": round(duration, 2),
                    "client_host": scope.get("client", ("unknown", 0))[0],
                },
            )
