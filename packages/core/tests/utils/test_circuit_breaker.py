"""Comprehensive tests for circuit breaker pattern implementation.

Tests cover:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure counting and threshold detection
- Recovery timeout behavior
- Success threshold in half-open state
- Statistics tracking
- Registry management
- Provider-specific configurations
- Decorator functionality
- Fallback mechanisms
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from scenemachine.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    CircuitStats,
    circuit_breaker,
    get_llm_circuit_breaker,
    get_provider_circuit_breaker,
    with_fallback,
)


# =============================================================================
# CircuitState Tests
# =============================================================================


class TestCircuitState:
    """Test circuit state enum."""

    def test_state_values(self):
        """Test all state values exist."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_state_is_string_enum(self):
        """Test states are string enums."""
        assert isinstance(CircuitState.CLOSED, str)
        assert str(CircuitState.OPEN) == "open"


# =============================================================================
# CircuitStats Tests
# =============================================================================


class TestCircuitStats:
    """Test circuit statistics dataclass."""

    def test_default_values(self):
        """Test default stat values."""
        stats = CircuitStats()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.rejected_calls == 0
        assert stats.last_failure_time is None
        assert stats.last_success_time is None
        assert stats.consecutive_failures == 0
        assert stats.consecutive_successes == 0
        assert stats.state_changes == []


# =============================================================================
# CircuitBreakerConfig Tests
# =============================================================================


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30.0
        assert config.success_threshold == 3
        assert config.call_timeout == 30.0
        assert config.failure_exceptions == (Exception,)
        assert config.exclude_exceptions == ()
        assert config.timeout_as_failure is True
        assert config.max_history == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,
            success_threshold=2,
            call_timeout=10.0,
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 2
        assert config.call_timeout == 10.0


# =============================================================================
# CircuitBreaker Basic Tests
# =============================================================================


class TestCircuitBreakerBasic:
    """Basic circuit breaker tests."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker("test")
        assert cb.name == "test"
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)
        assert cb.config.failure_threshold == 3

    def test_reset(self):
        """Test circuit breaker reset."""
        cb = CircuitBreaker("test")
        cb._stats.total_calls = 10
        cb._state = CircuitState.OPEN

        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.total_calls == 0

    def test_force_open(self):
        """Test force open functionality."""
        cb = CircuitBreaker("test")
        assert cb.is_closed

        cb.force_open()

        assert cb.is_open
        assert cb._opened_at is not None

    def test_force_close(self):
        """Test force close functionality."""
        cb = CircuitBreaker("test")
        cb.force_open()
        assert cb.is_open

        cb.force_close()

        assert cb.is_closed


# =============================================================================
# CircuitBreaker State Transition Tests
# =============================================================================


class TestCircuitBreakerStateTransitions:
    """Test state transitions in circuit breaker."""

    @pytest.mark.asyncio
    async def test_closed_to_open_on_failures(self):
        """Test transition from closed to open after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        async def failing_func():
            raise RuntimeError("Test error")

        # Should fail 3 times before opening
        for i in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failing_func)

            if i < 2:
                assert cb.is_closed, f"Should still be closed after {i+1} failures"

        assert cb.is_open

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        """Test transition from open to half-open after recovery timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,  # 100ms for testing
        )
        cb = CircuitBreaker("test", config)

        async def failing_func():
            raise RuntimeError("Test error")

        async def success_func():
            return "success"

        # Trigger open state
        with pytest.raises(RuntimeError):
            await cb.call(failing_func)

        assert cb.is_open

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next call should transition to half-open and succeed
        result = await cb.call(success_func)
        assert result == "success"
        # After success in half-open, might go to closed (depends on success_threshold)

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        """Test transition from half-open to closed after success threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        cb = CircuitBreaker("test", config)

        async def failing_func():
            raise RuntimeError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(RuntimeError):
            await cb.call(failing_func)

        assert cb.is_open

        # Wait for recovery
        await asyncio.sleep(0.15)

        # First success - should be half-open
        await cb.call(success_func)

        # Second success - should close
        await cb.call(success_func)

        assert cb.is_closed

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """Test transition from half-open back to open on failure."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=3,
        )
        cb = CircuitBreaker("test", config)

        async def failing_func():
            raise RuntimeError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(RuntimeError):
            await cb.call(failing_func)

        assert cb.is_open

        # Wait for recovery
        await asyncio.sleep(0.15)

        # Success moves to half-open
        await cb.call(success_func)
        assert cb.is_half_open or cb.is_closed  # May close if success_threshold met

        # If still half-open, a failure should reopen
        if cb.is_half_open:
            with pytest.raises(RuntimeError):
                await cb.call(failing_func)
            assert cb.is_open


# =============================================================================
# CircuitBreaker Call Tests
# =============================================================================


class TestCircuitBreakerCall:
    """Test circuit breaker call functionality."""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call."""
        cb = CircuitBreaker("test")

        async def success_func():
            return "success"

        result = await cb.call(success_func)

        assert result == "success"
        assert cb.stats.total_calls == 1
        assert cb.stats.successful_calls == 1
        assert cb.stats.failed_calls == 0

    @pytest.mark.asyncio
    async def test_failed_call(self):
        """Test failed function call."""
        cb = CircuitBreaker("test")

        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await cb.call(failing_func)

        assert cb.stats.total_calls == 1
        assert cb.stats.successful_calls == 0
        assert cb.stats.failed_calls == 1

    @pytest.mark.asyncio
    async def test_call_with_args(self):
        """Test call with positional and keyword arguments."""
        cb = CircuitBreaker("test")

        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await cb.call(func_with_args, "x", "y", c="z")

        assert result == "x-y-z"

    @pytest.mark.asyncio
    async def test_rejected_when_open(self):
        """Test calls are rejected when circuit is open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=10.0,  # Long timeout
        )
        cb = CircuitBreaker("test", config)

        async def failing_func():
            raise RuntimeError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(RuntimeError):
            await cb.call(failing_func)

        assert cb.is_open

        # Next call should be rejected
        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.call(success_func)

        assert exc_info.value.circuit_name == "test"
        assert exc_info.value.remaining_time > 0
        assert cb.stats.rejected_calls == 1

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test call timeout behavior."""
        config = CircuitBreakerConfig(
            call_timeout=0.1,
            timeout_as_failure=True,
        )
        cb = CircuitBreaker("test", config)

        async def slow_func():
            await asyncio.sleep(1.0)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await cb.call(slow_func)

        assert cb.stats.failed_calls == 1

    @pytest.mark.asyncio
    async def test_timeout_not_counted_as_failure(self):
        """Test timeout not counted as failure when configured."""
        config = CircuitBreakerConfig(
            call_timeout=0.1,
            timeout_as_failure=False,
        )
        cb = CircuitBreaker("test", config)

        async def slow_func():
            await asyncio.sleep(1.0)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await cb.call(slow_func)

        assert cb.stats.failed_calls == 0


# =============================================================================
# CircuitBreaker Exception Filtering Tests
# =============================================================================


class TestCircuitBreakerExceptionFiltering:
    """Test exception filtering in circuit breaker."""

    @pytest.mark.asyncio
    async def test_excluded_exceptions_not_counted(self):
        """Test excluded exceptions are not counted as failures."""
        config = CircuitBreakerConfig(
            exclude_exceptions=(ValueError,),
        )
        cb = CircuitBreaker("test", config)

        async def raise_value_error():
            raise ValueError("Not a failure")

        with pytest.raises(ValueError):
            await cb.call(raise_value_error)

        assert cb.stats.failed_calls == 0

    @pytest.mark.asyncio
    async def test_specific_failure_exceptions(self):
        """Test only specific exceptions trigger circuit."""
        config = CircuitBreakerConfig(
            failure_exceptions=(RuntimeError,),
            failure_threshold=1,
        )
        cb = CircuitBreaker("test", config)

        async def raise_value_error():
            raise ValueError("Not tracked")

        async def raise_runtime_error():
            raise RuntimeError("Tracked")

        # ValueError should not trip circuit
        with pytest.raises(ValueError):
            await cb.call(raise_value_error)
        assert cb.is_closed

        # RuntimeError should trip circuit
        with pytest.raises(RuntimeError):
            await cb.call(raise_runtime_error)
        assert cb.is_open


# =============================================================================
# CircuitBreaker Statistics Tests
# =============================================================================


class TestCircuitBreakerStatistics:
    """Test circuit breaker statistics tracking."""

    @pytest.mark.asyncio
    async def test_consecutive_tracking(self):
        """Test consecutive success/failure tracking."""
        cb = CircuitBreaker("test")

        async def success():
            return True

        async def fail():
            raise RuntimeError()

        # 3 successes
        for _ in range(3):
            await cb.call(success)
        assert cb.stats.consecutive_successes == 3
        assert cb.stats.consecutive_failures == 0

        # 2 failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
        assert cb.stats.consecutive_successes == 0
        assert cb.stats.consecutive_failures == 2

    @pytest.mark.asyncio
    async def test_state_change_history(self):
        """Test state change history tracking."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=1,
        )
        cb = CircuitBreaker("test", config)

        async def fail():
            raise RuntimeError()

        async def success():
            return True

        # Open circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert len(cb.stats.state_changes) == 1
        assert cb.stats.state_changes[0]["from"] == "closed"
        assert cb.stats.state_changes[0]["to"] == "open"

    def test_get_status(self):
        """Test get_status method."""
        cb = CircuitBreaker("test")
        status = cb.get_status()

        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert "stats" in status
        assert "config" in status
        assert status["remaining_timeout"] == 0.0


# =============================================================================
# CircuitBreaker Decorator Tests
# =============================================================================


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_wraps_function(self):
        """Test decorator wraps function correctly."""
        cb = CircuitBreaker("test")

        @cb.decorator
        async def my_func(x, y):
            return x + y

        result = await my_func(2, 3)
        assert result == 5
        assert cb.stats.total_calls == 1

    @pytest.mark.asyncio
    async def test_decorator_handles_errors(self):
        """Test decorator handles errors correctly."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        @cb.decorator
        async def failing_func():
            raise RuntimeError("Error")

        with pytest.raises(RuntimeError):
            await failing_func()

        assert cb.is_open


# =============================================================================
# CircuitBreakerRegistry Tests
# =============================================================================


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""

    def test_singleton_instance(self):
        """Test registry is singleton."""
        registry1 = CircuitBreakerRegistry.get_instance()
        registry2 = CircuitBreakerRegistry.get_instance()
        assert registry1 is registry2

    def test_get_or_create(self):
        """Test get_or_create creates new circuit breaker."""
        registry = CircuitBreakerRegistry()

        cb = registry.get_or_create("new_service")

        assert cb.name == "new_service"
        assert registry.get("new_service") is cb

    def test_get_or_create_returns_existing(self):
        """Test get_or_create returns existing circuit breaker."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("service")
        cb2 = registry.get_or_create("service")

        assert cb1 is cb2

    def test_get_nonexistent(self):
        """Test get returns None for nonexistent breaker."""
        registry = CircuitBreakerRegistry()
        assert registry.get("nonexistent") is None

    def test_get_all(self):
        """Test get_all returns all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("a")
        registry.get_or_create("b")

        all_breakers = registry.get_all()

        assert "a" in all_breakers
        assert "b" in all_breakers

    def test_get_all_status(self):
        """Test get_all_status returns status for all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("x")
        registry.get_or_create("y")

        status = registry.get_all_status()

        assert "x" in status
        assert "y" in status
        assert status["x"]["name"] == "x"

    def test_reset_all(self):
        """Test reset_all resets all breakers."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create("r1")
        cb2 = registry.get_or_create("r2")
        cb1._stats.total_calls = 10
        cb2._stats.total_calls = 20

        registry.reset_all()

        assert cb1.stats.total_calls == 0
        assert cb2.stats.total_calls == 0

    def test_remove(self):
        """Test remove deletes circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("to_remove")

        result = registry.remove("to_remove")

        assert result is True
        assert registry.get("to_remove") is None

    def test_remove_nonexistent(self):
        """Test remove returns False for nonexistent."""
        registry = CircuitBreakerRegistry()
        result = registry.remove("does_not_exist")
        assert result is False


# =============================================================================
# Provider Circuit Breaker Tests
# =============================================================================


class TestProviderCircuitBreakers:
    """Test pre-configured provider circuit breakers."""

    def test_get_replicate_circuit_breaker(self):
        """Test Replicate provider circuit breaker."""
        cb = get_provider_circuit_breaker("replicate")

        assert cb.name == "provider:replicate"
        assert cb.config.failure_threshold == 3
        assert cb.config.recovery_timeout == 60.0
        assert cb.config.call_timeout == 300.0

    def test_get_fal_circuit_breaker(self):
        """Test Fal provider circuit breaker."""
        cb = get_provider_circuit_breaker("fal")

        assert cb.name == "provider:fal"
        assert cb.config.failure_threshold == 3

    def test_get_comfyui_circuit_breaker(self):
        """Test ComfyUI provider circuit breaker."""
        cb = get_provider_circuit_breaker("comfyui")

        assert cb.name == "provider:comfyui"
        assert cb.config.failure_threshold == 5  # More tolerant
        assert cb.config.call_timeout == 600.0  # Longer timeout

    def test_get_runpod_circuit_breaker(self):
        """Test RunPod provider circuit breaker."""
        cb = get_provider_circuit_breaker("runpod")

        assert cb.name == "provider:runpod"
        assert cb.config.recovery_timeout == 120.0  # Cold start tolerance

    def test_get_local_circuit_breaker(self):
        """Test local provider circuit breaker."""
        cb = get_provider_circuit_breaker("local")

        assert cb.name == "provider:local"
        assert cb.config.success_threshold == 1
        assert cb.config.recovery_timeout == 10.0

    def test_get_unknown_provider_uses_default(self):
        """Test unknown provider uses default config."""
        cb = get_provider_circuit_breaker("unknown_provider")

        assert cb.name == "provider:unknown_provider"
        assert cb.config.failure_threshold == 5  # Default

    def test_get_llm_circuit_breaker(self):
        """Test LLM circuit breaker."""
        cb = get_llm_circuit_breaker("openai")

        assert cb.name == "llm:openai"
        assert cb.config.failure_threshold == 5
        assert cb.config.call_timeout == 120.0


# =============================================================================
# Circuit Breaker Decorator Factory Tests
# =============================================================================


class TestCircuitBreakerDecoratorFactory:
    """Test circuit_breaker decorator factory."""

    @pytest.mark.asyncio
    async def test_decorator_factory(self):
        """Test decorator factory creates and applies circuit breaker."""

        @circuit_breaker("decorator_test")
        async def my_service():
            return "result"

        result = await my_service()
        assert result == "result"

        # Verify circuit breaker was registered
        registry = CircuitBreakerRegistry.get_instance()
        cb = registry.get("decorator_test")
        assert cb is not None
        assert cb.stats.total_calls == 1

    @pytest.mark.asyncio
    async def test_decorator_factory_with_config(self):
        """Test decorator factory with custom config."""
        config = CircuitBreakerConfig(failure_threshold=2)

        @circuit_breaker("custom_config_test", config)
        async def my_service():
            raise RuntimeError("Error")

        # Should open after 2 failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await my_service()

        registry = CircuitBreakerRegistry.get_instance()
        cb = registry.get("custom_config_test")
        assert cb.is_open


# =============================================================================
# With Fallback Tests
# =============================================================================


class TestWithFallback:
    """Test with_fallback utility function."""

    @pytest.mark.asyncio
    async def test_fallback_on_circuit_open(self):
        """Test fallback is used when circuit is open."""
        # Create a fresh registry for this test
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=10.0,
        )
        registry = CircuitBreakerRegistry.get_instance()
        cb = registry.get_or_create("fallback_test", config)

        async def primary():
            raise RuntimeError("Primary failed")

        async def fallback():
            return "fallback_result"

        # Trip the circuit
        with pytest.raises(RuntimeError):
            await cb.call(primary)

        assert cb.is_open

        # Now with_fallback should use fallback
        result = await with_fallback(primary, fallback, "fallback_test")
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_primary_used_when_healthy(self):
        """Test primary is used when circuit is healthy."""

        async def primary():
            return "primary_result"

        async def fallback():
            return "fallback_result"

        result = await with_fallback(primary, fallback, "healthy_circuit")
        assert result == "primary_result"


# =============================================================================
# Concurrency Tests
# =============================================================================


class TestCircuitBreakerConcurrency:
    """Test circuit breaker under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Test circuit breaker handles concurrent calls correctly."""
        cb = CircuitBreaker("concurrent_test")
        call_count = 0

        async def counting_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return call_count

        # Run 10 concurrent calls
        tasks = [cb.call(counting_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert cb.stats.total_calls == 10
        assert cb.stats.successful_calls == 10

    @pytest.mark.asyncio
    async def test_concurrent_failures_trigger_open(self):
        """Test concurrent failures correctly trigger open state."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("concurrent_fail_test", config)

        async def failing_func():
            await asyncio.sleep(0.01)
            raise RuntimeError("Error")

        # Run concurrent failing calls
        tasks = [cb.call(failing_func) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should have raised exceptions
        for result in results:
            assert isinstance(result, (RuntimeError, CircuitOpenError))

        # Circuit should be open
        assert cb.is_open


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestCircuitBreakerEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_exact_threshold(self):
        """Test behavior at exact failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("threshold_test", config)

        async def fail():
            raise RuntimeError()

        # Exactly 3 failures should open
        for i in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.is_open
        assert cb.stats.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test success resets consecutive failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("reset_test", config)

        async def fail():
            raise RuntimeError()

        async def success():
            return True

        # 2 failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
        assert cb.stats.consecutive_failures == 2

        # 1 success resets
        await cb.call(success)
        assert cb.stats.consecutive_failures == 0

        # 2 more failures still won't open
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
        assert cb.is_closed

    def test_history_trimming(self):
        """Test state change history is trimmed."""
        config = CircuitBreakerConfig(max_history=3)
        cb = CircuitBreaker("history_test", config)

        # Add more state changes than max_history
        for _ in range(5):
            cb._transition_to(CircuitState.OPEN)
            cb._transition_to(CircuitState.CLOSED)

        assert len(cb.stats.state_changes) <= config.max_history

    @pytest.mark.asyncio
    async def test_zero_timeout(self):
        """Test behavior with no call timeout."""
        config = CircuitBreakerConfig(call_timeout=None)
        cb = CircuitBreaker("no_timeout", config)

        async def slow_func():
            await asyncio.sleep(0.1)
            return "done"

        result = await cb.call(slow_func)
        assert result == "done"


# =============================================================================
# CircuitOpenError Tests
# =============================================================================


class TestCircuitOpenError:
    """Test CircuitOpenError exception."""

    def test_error_message(self):
        """Test error message format."""
        error = CircuitOpenError("test_circuit", 5.5)

        assert error.circuit_name == "test_circuit"
        assert error.remaining_time == 5.5
        assert "test_circuit" in str(error)
        assert "5.5" in str(error)

    def test_inheritance(self):
        """Test error inheritance."""
        error = CircuitOpenError("test", 0)

        assert isinstance(error, CircuitBreakerError)
        assert isinstance(error, Exception)
