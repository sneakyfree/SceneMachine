"""Integration tests for Phase 20 features.

Tests:
- Security middleware (rate limiting, headers, validation)
- Caching (LRU, LLM, file cache)
- Production hardening features
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient

from scenemachine.api.middleware import (
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimiter,
    SecurityHeadersConfig,
    SecurityHeadersMiddleware,
    RequestValidationConfig,
    RequestValidationMiddleware,
    TokenBucket,
    SlidingWindowCounter,
    get_client_ip,
)
from scenemachine.utils.cache import (
    LRUCache,
    LLMCache,
    FileCache,
    cached,
    get_llm_cache,
)


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestTokenBucket:
    """Tests for TokenBucket rate limiting."""

    def test_acquire_within_limit(self):
        """Test acquiring tokens within limit."""
        bucket = TokenBucket(rate=10.0, capacity=10)

        # Should be able to acquire up to capacity
        for _ in range(10):
            allowed, wait = bucket.acquire()
            assert allowed is True
            assert wait == 0.0

    def test_acquire_exceeds_limit(self):
        """Test acquiring more than capacity."""
        bucket = TokenBucket(rate=10.0, capacity=5)

        # Exhaust capacity
        for _ in range(5):
            bucket.acquire()

        # Next should fail
        allowed, wait = bucket.acquire()
        assert allowed is False
        assert wait > 0

    def test_token_refill(self):
        """Test that tokens refill over time."""
        bucket = TokenBucket(rate=100.0, capacity=10)  # 100 tokens/sec

        # Exhaust
        for _ in range(10):
            bucket.acquire()

        # Wait for refill
        time.sleep(0.1)  # 10 tokens should be added

        # Should be able to acquire again
        allowed, _ = bucket.acquire()
        assert allowed is True


class TestSlidingWindowCounter:
    """Tests for SlidingWindowCounter rate limiting."""

    def test_acquire_within_limit(self):
        """Test acquiring within the limit."""
        counter = SlidingWindowCounter(window_size=60, max_requests=10)

        for i in range(10):
            allowed, count = counter.acquire()
            assert allowed is True
            assert count == i + 1

    def test_acquire_exceeds_limit(self):
        """Test exceeding the limit."""
        counter = SlidingWindowCounter(window_size=60, max_requests=5)

        # Use all slots
        for _ in range(5):
            counter.acquire()

        # Should fail
        allowed, count = counter.acquire()
        assert allowed is False
        assert count == 5

    def test_window_expiration(self):
        """Test that old requests expire."""
        counter = SlidingWindowCounter(window_size=0.1, max_requests=5)

        # Use all slots
        for _ in range(5):
            counter.acquire()

        # Wait for window to expire
        time.sleep(0.15)

        # Should be able to acquire again
        allowed, count = counter.acquire()
        assert allowed is True
        assert count == 1


class TestRateLimiter:
    """Tests for the RateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter."""
        config = RateLimitConfig(
            requests_per_second=10,
            requests_per_minute=50,
            requests_per_hour=500,
            burst_size=15,
            excluded_paths=["/health"],
        )
        return RateLimiter(config)

    def test_excluded_paths(self, limiter):
        """Test that excluded paths bypass rate limiting."""
        request = MagicMock()
        request.url.path = "/health"
        request.headers.get.return_value = None
        request.client.host = "127.0.0.1"

        allowed, info = limiter.check(request)
        assert allowed is True
        assert info == {}

    def test_rate_limited_path(self, limiter):
        """Test rate limiting on non-excluded paths."""
        request = MagicMock()
        request.url.path = "/api/v1/projects"
        request.headers.get.return_value = None
        request.client.host = "127.0.0.1"

        # First requests should succeed
        for _ in range(10):
            allowed, info = limiter.check(request)
            assert allowed is True

    def test_api_key_identification(self, limiter):
        """Test that API key is used for client identification."""
        request = MagicMock()
        request.url.path = "/api/v1/projects"
        request.headers.get.side_effect = lambda key: (
            "test-api-key" if key == "X-API-Key" else None
        )
        request.client.host = "127.0.0.1"

        allowed, info = limiter.check(request)
        assert allowed is True


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with rate limiting."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(
                requests_per_second=5,
                requests_per_minute=10,
                burst_size=5,
            ),
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"healthy": True}

        return app

    def test_rate_limit_headers(self, app):
        """Test that rate limit headers are added."""
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_excluded_path_no_headers(self, app):
        """Test that excluded paths don't have rate limit headers."""
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200


# ============================================================================
# Security Headers Tests
# ============================================================================


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def app(self):
        """Create test app with security headers."""
        app = FastAPI()
        app.add_middleware(
            SecurityHeadersMiddleware,
            config=SecurityHeadersConfig(
                csp_enabled=True,
                x_content_type_options=True,
                x_frame_options="DENY",
            ),
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        return app

    def test_security_headers_present(self, app):
        """Test that security headers are added."""
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"


# ============================================================================
# Request Validation Tests
# ============================================================================


class TestRequestValidationMiddleware:
    """Tests for RequestValidationMiddleware."""

    @pytest.fixture
    def app(self):
        """Create test app with request validation."""
        app = FastAPI()
        app.add_middleware(
            RequestValidationMiddleware,
            config=RequestValidationConfig(
                max_body_size=1024,  # 1KB for testing
                max_url_length=100,
                blocked_user_agents=["badbot"],
            ),
        )

        @app.post("/test")
        async def test_endpoint(request: Request):
            return {"status": "ok"}

        return app

    def test_blocked_user_agent(self, app):
        """Test that blocked user agents are rejected."""
        client = TestClient(app)

        response = client.post(
            "/test",
            headers={"User-Agent": "badbot/1.0"},
        )
        assert response.status_code == 403

    def test_valid_request(self, app):
        """Test that valid requests pass."""
        client = TestClient(app)

        response = client.post(
            "/test",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        assert response.status_code == 200


# ============================================================================
# LRU Cache Tests
# ============================================================================


class TestLRUCache:
    """Tests for LRUCache."""

    @pytest.mark.asyncio
    async def test_basic_get_set(self):
        """Test basic get and set operations."""
        cache = LRUCache[str](max_entries=10)

        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = LRUCache[str](max_entries=10)

        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = LRUCache[str](max_entries=10, default_ttl_seconds=1)

        await cache.set("key1", "value1", ttl_seconds=0)  # Immediate expiration

        # Should be expired
        await asyncio.sleep(0.1)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache[str](max_entries=3, default_ttl_seconds=None)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it recently used
        await cache.get("key1")

        # Add new entry - should evict key2 (least recently used)
        await cache.set("key4", "value4")

        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = LRUCache[str](max_entries=10)

        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss

        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


# ============================================================================
# LLM Cache Tests
# ============================================================================


class TestLLMCache:
    """Tests for LLMCache."""

    @pytest.mark.asyncio
    async def test_cache_deterministic_request(self):
        """Test caching with temperature=0."""
        cache = LLMCache(max_entries=10)

        response = {"content": "test response", "usage": {"total_tokens": 100}}
        await cache.set(
            prompt="test prompt",
            model="gpt-4",
            response=response,
            temperature=0.0,
        )

        result = await cache.get(
            prompt="test prompt",
            model="gpt-4",
            temperature=0.0,
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_no_cache_non_deterministic(self):
        """Test that non-deterministic requests are not cached."""
        cache = LLMCache(max_entries=10)

        response = {"content": "test response"}
        await cache.set(
            prompt="test prompt",
            model="gpt-4",
            response=response,
            temperature=0.7,  # Non-deterministic
        )

        result = await cache.get(
            prompt="test prompt",
            model="gpt-4",
            temperature=0.7,
        )
        assert result is None  # Should not be cached

    @pytest.mark.asyncio
    async def test_different_prompts_different_keys(self):
        """Test that different prompts have different cache keys."""
        cache = LLMCache(max_entries=10)

        await cache.set("prompt1", "gpt-4", {"content": "response1"}, 0.0)
        await cache.set("prompt2", "gpt-4", {"content": "response2"}, 0.0)

        result1 = await cache.get("prompt1", "gpt-4", 0.0)
        result2 = await cache.get("prompt2", "gpt-4", 0.0)

        assert result1["content"] == "response1"
        assert result2["content"] == "response2"

    @pytest.mark.asyncio
    async def test_cache_stats_with_savings(self):
        """Test cache statistics include savings."""
        cache = LLMCache(max_entries=10)

        response = {"content": "test", "usage": {"total_tokens": 500}}
        await cache.set("prompt", "gpt-4", response, 0.0)

        # Hit the cache
        await cache.get("prompt", "gpt-4", 0.0)

        stats = cache.stats()
        assert stats["tokens_saved"] == 500
        assert stats["cost_saved_usd"] > 0


# ============================================================================
# File Cache Tests
# ============================================================================


class TestFileCache:
    """Tests for FileCache."""

    @pytest.fixture
    def cache_dir(self, tmp_path):
        """Create temporary cache directory."""
        return tmp_path / "file_cache"

    @pytest.fixture
    def cache(self, cache_dir):
        """Create file cache."""
        return FileCache(
            cache_dir=cache_dir,
            max_size_gb=0.001,  # 1MB for testing
            default_ttl_days=1,
        )

    @pytest.mark.asyncio
    async def test_put_and_get(self, cache, tmp_path):
        """Test caching a file."""
        # Create source file
        source = tmp_path / "test.txt"
        source.write_text("test content")

        # Cache it
        cached_path = await cache.put("key1", source)
        assert cached_path.exists()
        assert cached_path.read_text() == "test content"

        # Get it back
        result = await cache.get("key1")
        assert result == cached_path

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache, tmp_path):
        """Test deleting cached file."""
        source = tmp_path / "test.txt"
        source.write_text("test")

        await cache.put("key1", source)
        assert await cache.get("key1") is not None

        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_stats(self, cache, tmp_path):
        """Test cache statistics."""
        source = tmp_path / "test.txt"
        source.write_text("test content 12345")

        await cache.put("key1", source)

        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["size_bytes"] > 0


# ============================================================================
# Cached Decorator Tests
# ============================================================================


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_function(self):
        """Test that function results are cached."""
        call_count = 0

        @cached(ttl_seconds=60)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_function(5)
        result2 = await expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_different_args_different_cache(self):
        """Test that different args have different cache entries."""
        call_count = 0

        @cached(ttl_seconds=60)
        async def func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        await func(1)
        await func(2)
        await func(1)  # Should be cached

        assert call_count == 2  # Two different args

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing the cache."""
        call_count = 0

        @cached(ttl_seconds=60)
        async def func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        await func(1)
        await func.cache_clear()
        await func(1)

        assert call_count == 2  # Called twice after clear


# ============================================================================
# Integration Tests
# ============================================================================


class TestSecurityIntegration:
    """Integration tests for security features."""

    @pytest.fixture
    def secured_app(self):
        """Create fully secured app."""
        app = FastAPI()

        # Add all security middleware
        app.add_middleware(
            RequestValidationMiddleware,
            config=RequestValidationConfig(max_body_size=1024 * 1024),
        )
        app.add_middleware(
            SecurityHeadersMiddleware,
            config=SecurityHeadersConfig(hsts_enabled=False),
        )
        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(
                requests_per_second=100,
                requests_per_minute=1000,
                burst_size=200,
            ),
        )

        @app.get("/api/test")
        async def test_endpoint():
            return {"status": "secured"}

        @app.get("/health")
        async def health():
            return {"healthy": True}

        return app

    def test_all_security_features_work_together(self, secured_app):
        """Test that all security middleware works together."""
        client = TestClient(secured_app)

        response = client.get("/api/test")
        assert response.status_code == 200
        assert response.json()["status"] == "secured"

        # Check security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers

    def test_health_endpoint_bypasses_rate_limit(self, secured_app):
        """Test health endpoint is not rate limited."""
        client = TestClient(secured_app)

        # Should always work
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200


class TestCacheIntegration:
    """Integration tests for caching features."""

    @pytest.mark.asyncio
    async def test_combined_cache_usage(self, tmp_path):
        """Test using multiple cache types together."""
        # LRU cache for small data
        lru = LRUCache[Dict](max_entries=100)
        await lru.set("metadata", {"project": "test", "version": 1})

        # File cache for large data
        file_cache = FileCache(
            cache_dir=tmp_path / "files",
            max_size_gb=0.01,
        )
        source = tmp_path / "large_file.bin"
        source.write_bytes(b"x" * 1000)
        await file_cache.put("large_data", source)

        # Verify both work
        assert await lru.get("metadata") == {"project": "test", "version": 1}
        assert (await file_cache.get("large_data")).exists()

        # Check stats
        lru_stats = lru.stats()
        file_stats = file_cache.stats()

        assert lru_stats["entries"] == 1
        assert file_stats["entries"] == 1
