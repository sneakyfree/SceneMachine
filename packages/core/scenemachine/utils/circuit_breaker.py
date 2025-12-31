"""Circuit breaker pattern implementation for resilient service calls.

Provides fault tolerance for external service integrations (video providers,
LLM services, etc.) by preventing cascading failures.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests flow through
    OPEN = "open"  # Failing, requests are rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    state_changes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    # Number of failures before opening circuit
    failure_threshold: int = 5

    # Time in seconds before attempting recovery
    recovery_timeout: float = 30.0

    # Number of successes needed in half-open to close
    success_threshold: int = 3

    # Timeout for individual calls
    call_timeout: Optional[float] = 30.0

    # Exceptions that should trip the circuit
    failure_exceptions: tuple = (Exception,)

    # Exceptions to exclude from circuit breaker
    exclude_exceptions: tuple = ()

    # Whether to include timeout as a failure
    timeout_as_failure: bool = True

    # Max history entries for state changes
    max_history: int = 100


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""

    pass


class CircuitOpenError(CircuitBreakerError):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, circuit_name: str, remaining_time: float):
        self.circuit_name = circuit_name
        self.remaining_time = remaining_time
        super().__init__(
            f"Circuit '{circuit_name}' is open. "
            f"Retry after {remaining_time:.1f} seconds."
        )


class CircuitBreaker:
    """Circuit breaker for fault-tolerant external service calls.

    Usage:
        # Create circuit breaker
        cb = CircuitBreaker("replicate_api")

        # Wrap calls
        try:
            result = await cb.call(async_function, arg1, arg2)
        except CircuitOpenError:
            # Handle circuit open (use fallback, queue for later, etc.)
            pass

        # Or use as decorator
        @cb.decorator
        async def my_function():
            ...
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._opened_at: Optional[float] = None
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    def _should_allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._opened_at is None:
                return False

            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.config.recovery_timeout:
                return True  # Will transition to half-open
            return False

        if self._state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open
            return self._half_open_calls < self.config.success_threshold

        return False

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state

        # Record state change
        self._stats.state_changes.append({
            "from": old_state.value,
            "to": new_state.value,
            "timestamp": time.time(),
            "consecutive_failures": self._stats.consecutive_failures,
            "consecutive_successes": self._stats.consecutive_successes,
        })

        # Trim history
        if len(self._stats.state_changes) > self.config.max_history:
            self._stats.state_changes = self._stats.state_changes[-self.config.max_history:]

        logger.info(
            f"Circuit '{self.name}' transitioned from {old_state.value} to {new_state.value}"
        )

        # Handle state-specific logic
        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._opened_at = None
            self._half_open_calls = 0

    def _record_success(self) -> None:
        """Record a successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.last_success_time = time.time()
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._stats.consecutive_successes >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.OPEN:
            # Shouldn't happen, but handle it
            self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.last_failure_time = time.time()
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0

        logger.warning(
            f"Circuit '{self.name}' recorded failure: {type(error).__name__}: {error}"
        )

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _record_rejected(self) -> None:
        """Record a rejected call (circuit open)."""
        self._stats.total_calls += 1
        self._stats.rejected_calls += 1

    def _is_failure_exception(self, error: Exception) -> bool:
        """Check if exception should count as a failure."""
        # Check exclusions first
        if isinstance(error, self.config.exclude_exceptions):
            return False

        # Check if it's a failure exception
        return isinstance(error, self.config.failure_exceptions)

    async def call(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from the function
        """
        async with self._lock:
            if not self._should_allow_request():
                self._record_rejected()
                remaining = 0.0
                if self._opened_at:
                    remaining = max(
                        0,
                        self.config.recovery_timeout - (time.monotonic() - self._opened_at),
                    )
                raise CircuitOpenError(self.name, remaining)

            # Transition to half-open if needed
            if self._state == CircuitState.OPEN:
                self._transition_to(CircuitState.HALF_OPEN)

        # Execute call
        try:
            if self.config.call_timeout:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.call_timeout,
                )
            else:
                result = await func(*args, **kwargs)

            async with self._lock:
                self._record_success()

            return result

        except asyncio.TimeoutError as e:
            if self.config.timeout_as_failure:
                async with self._lock:
                    self._record_failure(e)
            raise

        except Exception as e:
            if self._is_failure_exception(e):
                async with self._lock:
                    self._record_failure(e)
            raise

    def decorator(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap a function with circuit breaker."""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call(func, *args, **kwargs)

        return wrapper

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._opened_at = None
        self._half_open_calls = 0
        logger.info(f"Circuit '{self.name}' reset to closed state")

    def force_open(self) -> None:
        """Force circuit to open state (useful for maintenance)."""
        self._transition_to(CircuitState.OPEN)

    def force_close(self) -> None:
        """Force circuit to closed state."""
        self._transition_to(CircuitState.CLOSED)

    def get_status(self) -> Dict[str, Any]:
        """Get detailed status information."""
        remaining_timeout = 0.0
        if self._state == CircuitState.OPEN and self._opened_at:
            elapsed = time.monotonic() - self._opened_at
            remaining_timeout = max(0, self.config.recovery_timeout - elapsed)

        return {
            "name": self.name,
            "state": self._state.value,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "last_failure": self._stats.last_failure_time,
                "last_success": self._stats.last_success_time,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "call_timeout": self.config.call_timeout,
            },
            "remaining_timeout": remaining_timeout,
            "recent_state_changes": self._stats.state_changes[-10:],
        }


# ============================================================================
# Circuit Breaker Registry
# ============================================================================


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    _instance: Optional["CircuitBreakerRegistry"] = None

    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "CircuitBreakerRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name, config)
        return self._circuits[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._circuits.get(name)

    def get_all(self) -> Dict[str, CircuitBreaker]:
        """Get all circuit breakers."""
        return dict(self._circuits)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {name: cb.get_status() for name, cb in self._circuits.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._circuits.values():
            cb.reset()

    def remove(self, name: str) -> bool:
        """Remove a circuit breaker."""
        if name in self._circuits:
            del self._circuits[name]
            return True
        return False


# ============================================================================
# Provider Circuit Breakers
# ============================================================================


# Pre-configured circuit breakers for video providers
def get_provider_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create circuit breaker for a video generation provider."""
    registry = CircuitBreakerRegistry.get_instance()

    # Provider-specific configurations
    provider_configs = {
        "replicate": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,  # 1 minute
            success_threshold=2,
            call_timeout=300.0,  # 5 minutes for generation
        ),
        "fal": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
            success_threshold=2,
            call_timeout=300.0,
        ),
        "comfyui": CircuitBreakerConfig(
            failure_threshold=5,  # More tolerance for local service
            recovery_timeout=30.0,
            success_threshold=2,
            call_timeout=600.0,  # 10 minutes for local
        ),
        "runpod": CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=120.0,  # 2 minutes (serverless cold start)
            success_threshold=2,
            call_timeout=600.0,
        ),
        "local": CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=10.0,
            success_threshold=1,
            call_timeout=300.0,
        ),
    }

    config = provider_configs.get(provider.lower(), CircuitBreakerConfig())
    return registry.get_or_create(f"provider:{provider}", config)


def get_llm_circuit_breaker(provider: str = "default") -> CircuitBreaker:
    """Get or create circuit breaker for LLM services."""
    registry = CircuitBreakerRegistry.get_instance()

    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        success_threshold=2,
        call_timeout=120.0,  # 2 minutes
    )

    return registry.get_or_create(f"llm:{provider}", config)


# ============================================================================
# Utility Functions
# ============================================================================


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator factory for circuit breaker.

    Usage:
        @circuit_breaker("my_service")
        async def call_external_service():
            ...
    """
    registry = CircuitBreakerRegistry.get_instance()
    cb = registry.get_or_create(name, config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return cb.decorator(func)

    return decorator


async def with_fallback(
    primary: Callable[..., T],
    fallback: Callable[..., T],
    circuit_name: str,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute primary function with fallback on circuit open.

    Args:
        primary: Primary function to call
        fallback: Fallback function if circuit is open
        circuit_name: Name of circuit breaker to use
        *args: Arguments for both functions
        **kwargs: Keyword arguments for both functions

    Returns:
        Result from primary or fallback function
    """
    registry = CircuitBreakerRegistry.get_instance()
    cb = registry.get_or_create(circuit_name)

    try:
        return await cb.call(primary, *args, **kwargs)
    except CircuitOpenError:
        logger.info(f"Circuit '{circuit_name}' open, using fallback")
        return await fallback(*args, **kwargs)
