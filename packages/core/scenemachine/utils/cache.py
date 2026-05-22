"""Caching utilities for performance optimization.

Provides:
- LLM response caching with TTL
- General-purpose async caching
- File-based cache persistence
- Memory-efficient LRU cache
- Redis-based distributed caching
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# LRU Cache with TTL
# ============================================================================


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with value and metadata."""

    value: T
    created_at: float
    expires_at: float | None
    hits: int = 0
    size_bytes: int = 0


class LRUCache(Generic[T]):
    """Thread-safe LRU cache with TTL support.

    Features:
    - Maximum size limit (entries or bytes)
    - Time-to-live expiration
    - Hit/miss statistics
    - Memory usage tracking
    """

    def __init__(
        self,
        max_entries: int = 1000,
        max_size_bytes: int | None = None,
        default_ttl_seconds: int | None = 3600,
    ) -> None:
        """
        Initialize cache.

        Args:
            max_entries: Maximum number of entries
            max_size_bytes: Maximum total size in bytes (None = no limit)
            default_ttl_seconds: Default TTL (None = no expiration)
        """
        self.max_entries = max_entries
        self.max_size_bytes = max_size_bytes
        self.default_ttl = default_ttl_seconds

        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._total_size = 0
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> T | None:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                self._remove_entry(key)
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._hits += 1

            return entry.value

    async def set(
        self,
        key: str,
        value: T,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set value in cache."""
        async with self._lock:
            now = time.time()
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            expires_at = now + ttl if ttl else None

            # Estimate size
            try:
                size_bytes = len(pickle.dumps(value))
            except Exception:
                size_bytes = 0

            # Remove old entry if exists
            if key in self._cache:
                self._remove_entry(key)

            # Evict if needed
            await self._evict_if_needed(size_bytes)

            # Add entry
            entry = CacheEntry(
                value=value,
                created_at=now,
                expires_at=expires_at,
                size_bytes=size_bytes,
            )
            self._cache[key] = entry
            self._total_size += size_bytes

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()
            self._total_size = 0

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        async with self._lock:
            now = time.time()
            expired = [
                key
                for key, entry in self._cache.items()
                if entry.expires_at and entry.expires_at < now
            ]
            for key in expired:
                self._remove_entry(key)
            return len(expired)

    def _remove_entry(self, key: str) -> None:
        """Remove entry (must hold lock)."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._total_size -= entry.size_bytes

    async def _evict_if_needed(self, new_entry_size: int) -> None:
        """Evict entries if cache is full (must hold lock)."""
        # Evict by entry count
        while len(self._cache) >= self.max_entries:
            key = next(iter(self._cache))
            self._remove_entry(key)

        # Evict by size
        if self.max_size_bytes:
            while self._total_size + new_entry_size > self.max_size_bytes and self._cache:
                key = next(iter(self._cache))
                self._remove_entry(key)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "size_bytes": self._total_size,
            "max_size_bytes": self.max_size_bytes,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total_requests if total_requests > 0 else 0.0,
        }


# ============================================================================
# LLM Response Cache
# ============================================================================


def _hash_prompt(prompt: str, model: str, **kwargs: Any) -> str:
    """Create hash key for LLM prompt."""
    data = {
        "prompt": prompt,
        "model": model,
        **{k: v for k, v in sorted(kwargs.items()) if v is not None},
    }
    content = json.dumps(data, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


class LLMCache:
    """Specialized cache for LLM responses.

    Features:
    - Prompt-based caching with model awareness
    - Semantic similarity matching (optional)
    - Cost tracking
    - Persistence support
    """

    def __init__(
        self,
        max_entries: int = 500,
        max_size_mb: float = 100.0,
        default_ttl_hours: float = 24.0,
        persist_path: Path | None = None,
    ) -> None:
        """
        Initialize LLM cache.

        Args:
            max_entries: Maximum cached responses
            max_size_mb: Maximum cache size in MB
            default_ttl_hours: Default TTL in hours
            persist_path: Path for cache persistence
        """
        self._cache = LRUCache[dict[str, Any]](
            max_entries=max_entries,
            max_size_bytes=int(max_size_mb * 1024 * 1024),
            default_ttl_seconds=int(default_ttl_hours * 3600),
        )
        self._persist_path = persist_path
        self._cost_saved = 0.0
        self._tokens_saved = 0

        # Load persisted cache
        if persist_path and persist_path.exists():
            self._load()

    async def get(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """
        Get cached LLM response.

        Only caches deterministic requests (temperature=0).
        """
        # Only cache deterministic responses
        if temperature > 0:
            return None

        key = _hash_prompt(prompt, model, **kwargs)
        result = await self._cache.get(key)

        if result:
            # Track savings
            self._tokens_saved += result.get("usage", {}).get("total_tokens", 0)
            # Estimate cost saved (rough approximation)
            tokens = result.get("usage", {}).get("total_tokens", 0)
            self._cost_saved += tokens * 0.00001  # ~$0.01 per 1K tokens average

        return result

    async def set(
        self,
        prompt: str,
        model: str,
        response: dict[str, Any],
        temperature: float = 0.0,
        ttl_hours: float | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Cache an LLM response.

        Only caches deterministic requests (temperature=0).
        """
        if temperature > 0:
            return

        key = _hash_prompt(prompt, model, **kwargs)
        ttl_seconds = int(ttl_hours * 3600) if ttl_hours else None
        await self._cache.set(key, response, ttl_seconds)

        # Persist if configured
        if self._persist_path:
            await self._save()

    async def invalidate_for_model(self, model: str) -> int:
        """Invalidate all cached responses for a model.

        Args:
            model: Model name to invalidate cache for

        Returns:
            Number of entries invalidated
        """
        count = 0
        keys_to_remove = []

        # Iterate through cache to find matching entries
        async with self._cache._lock:
            for key, entry in self._cache._cache.items():
                # Check if the cached response was for this model
                if isinstance(entry.value, dict) and entry.value.get("model") == model:
                    keys_to_remove.append(key)

        # Remove matching entries
        for key in keys_to_remove:
            await self._cache.delete(key)
            count += 1

        if count > 0:
            logger.info(f"Invalidated {count} cache entries for model: {model}")

        return count

    async def evict_by_age(self, max_age_hours: float) -> int:
        """Evict entries older than specified age.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of entries evicted
        """
        count = 0
        max_age_seconds = max_age_hours * 3600
        now = time.time()
        keys_to_remove = []

        async with self._cache._lock:
            for key, entry in self._cache._cache.items():
                age = now - entry.created_at
                if age > max_age_seconds:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            await self._cache.delete(key)
            count += 1

        if count > 0:
            logger.info(f"Evicted {count} cache entries older than {max_age_hours} hours")

        return count

    async def evict_low_hit_entries(self, min_hits: int = 1, max_evict: int = 100) -> int:
        """Evict entries with low hit counts to free space.

        Useful for clearing rarely-accessed cached responses.

        Args:
            min_hits: Minimum hits required to keep entry
            max_evict: Maximum entries to evict

        Returns:
            Number of entries evicted
        """
        count = 0
        keys_to_remove = []

        async with self._cache._lock:
            # Sort by hits (ascending) to evict least-used first
            sorted_entries = sorted(
                self._cache._cache.items(),
                key=lambda x: x[1].hits,
            )

            for key, entry in sorted_entries:
                if entry.hits < min_hits and count < max_evict:
                    keys_to_remove.append(key)
                    count += 1

        for key in keys_to_remove:
            await self._cache.delete(key)

        if count > 0:
            logger.info(f"Evicted {count} low-hit cache entries (hits < {min_hits})")

        return count

    async def evict_by_size(self, target_size_mb: float) -> int:
        """Evict entries until cache is below target size.

        Evicts least-recently-used entries first.

        Args:
            target_size_mb: Target cache size in MB

        Returns:
            Number of entries evicted
        """
        count = 0
        target_bytes = int(target_size_mb * 1024 * 1024)

        async with self._cache._lock:
            while self._cache._total_size > target_bytes and self._cache._cache:
                # Remove oldest (LRU) entry
                key = next(iter(self._cache._cache))
                self._cache._remove_entry(key)
                count += 1

        if count > 0:
            logger.info(f"Evicted {count} cache entries to reach target size of {target_size_mb}MB")

        return count

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        cache_stats = self._cache.stats()
        return {
            **cache_stats,
            "cost_saved_usd": round(self._cost_saved, 4),
            "tokens_saved": self._tokens_saved,
        }

    async def _save(self) -> None:
        """Save cache to disk."""
        if not self._persist_path:
            return

        try:
            data = {
                "cache": dict(self._cache._cache),
                "cost_saved": self._cost_saved,
                "tokens_saved": self._tokens_saved,
                "saved_at": datetime.now(UTC).isoformat(),
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to persist LLM cache: {e}")

    def _load(self) -> None:
        """Load cache from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return

        try:
            with open(self._persist_path, "rb") as f:
                data = pickle.load(f)

            # Restore cache entries
            for key, entry in data.get("cache", {}).items():
                self._cache._cache[key] = entry

            self._cost_saved = data.get("cost_saved", 0.0)
            self._tokens_saved = data.get("tokens_saved", 0)
            logger.info(f"Loaded LLM cache with {len(self._cache._cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to load LLM cache: {e}")


# Global LLM cache instance
_llm_cache: LLMCache | None = None


def get_llm_cache() -> LLMCache:
    """Get global LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        from scenemachine.config import get_settings

        settings = get_settings()
        cache_path = settings.cache_dir / "llm_cache.pkl"
        _llm_cache = LLMCache(persist_path=cache_path)
    return _llm_cache


# ============================================================================
# Async Cache Decorator
# ============================================================================


def cached(
    ttl_seconds: int = 3600,
    key_func: Callable[..., str] | None = None,
    cache: LRUCache | None = None,
):
    """
    Decorator for caching async function results.

    Args:
        ttl_seconds: Time to live in seconds
        key_func: Function to generate cache key from args
        cache: Cache instance to use (creates new if None)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        nonlocal cache
        if cache is None:
            cache = LRUCache[T](default_ttl_seconds=ttl_seconds)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": str(sorted(kwargs.items())),
                }
                key = hashlib.md5(str(key_data).encode()).hexdigest()

            # Check cache
            result = await cache.get(key)
            if result is not None:
                return result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(key, result, ttl_seconds)

            return result

        wrapper.cache = cache  # type: ignore
        wrapper.cache_clear = cache.clear  # type: ignore

        return wrapper

    return decorator


# ============================================================================
# File-based Cache
# ============================================================================


class FileCache:
    """File-based cache for large objects.

    Useful for caching generated videos, images, etc.
    """

    def __init__(
        self,
        cache_dir: Path,
        max_size_gb: float = 10.0,
        default_ttl_days: int = 7,
    ) -> None:
        """
        Initialize file cache.

        Args:
            cache_dir: Directory for cached files
            max_size_gb: Maximum cache size in GB
            default_ttl_days: Default TTL in days
        """
        self.cache_dir = cache_dir
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.default_ttl = default_ttl_days * 24 * 3600
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file
        self._meta_file = cache_dir / ".cache_meta.json"
        self._meta: dict[str, dict[str, Any]] = {}
        self._load_meta()

    def _load_meta(self) -> None:
        """Load cache metadata."""
        if self._meta_file.exists():
            try:
                with open(self._meta_file) as f:
                    self._meta = json.load(f)
            except Exception:
                self._meta = {}

    def _save_meta(self) -> None:
        """Save cache metadata."""
        try:
            with open(self._meta_file, "w") as f:
                json.dump(self._meta, f)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def _get_path(self, key: str) -> Path:
        """Get file path for key."""
        # Use hash for filename to avoid path issues
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / hashed[:2] / hashed[2:]

    async def get(self, key: str) -> Path | None:
        """
        Get cached file path.

        Returns None if not cached or expired.
        """
        path = self._get_path(key)
        if not path.exists():
            return None

        meta = self._meta.get(key)
        if meta:
            # Check expiration
            if meta.get("expires_at", 0) < time.time():
                await self.delete(key)
                return None

            # Update access time
            meta["accessed_at"] = time.time()
            meta["hits"] = meta.get("hits", 0) + 1
            self._save_meta()

        return path

    async def put(
        self,
        key: str,
        source_path: Path,
        ttl_seconds: int | None = None,
        move: bool = False,
    ) -> Path:
        """
        Cache a file.

        Args:
            key: Cache key
            source_path: Path to source file
            ttl_seconds: TTL (uses default if None)
            move: Move instead of copy

        Returns:
            Path to cached file
        """
        import shutil

        dest_path = self._get_path(key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if move:
            shutil.move(str(source_path), str(dest_path))
        else:
            shutil.copy2(str(source_path), str(dest_path))

        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

        self._meta[key] = {
            "created_at": now,
            "accessed_at": now,
            "expires_at": now + ttl if ttl else None,
            "size_bytes": dest_path.stat().st_size,
            "hits": 0,
        }
        self._save_meta()

        # Evict if needed
        await self._evict_if_needed()

        return dest_path

    async def delete(self, key: str) -> bool:
        """Delete cached file."""
        path = self._get_path(key)
        if path.exists():
            path.unlink()

        if key in self._meta:
            del self._meta[key]
            self._save_meta()
            return True

        return False

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = time.time()
        expired = [
            key
            for key, meta in self._meta.items()
            if meta.get("expires_at") and meta["expires_at"] < now
        ]

        for key in expired:
            await self.delete(key)

        return len(expired)

    async def _evict_if_needed(self) -> None:
        """Evict entries if cache is too large."""
        total_size = sum(m.get("size_bytes", 0) for m in self._meta.values())

        while total_size > self.max_size_bytes and self._meta:
            # Find least recently accessed
            oldest_key = min(
                self._meta.keys(),
                key=lambda k: self._meta[k].get("accessed_at", 0),
            )
            oldest_size = self._meta[oldest_key].get("size_bytes", 0)
            await self.delete(oldest_key)
            total_size -= oldest_size

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(m.get("size_bytes", 0) for m in self._meta.values())
        total_hits = sum(m.get("hits", 0) for m in self._meta.values())

        return {
            "entries": len(self._meta),
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_gb": self.max_size_bytes / (1024 * 1024 * 1024),
            "total_hits": total_hits,
        }


# ============================================================================
# Redis Cache
# ============================================================================


class RedisCache(Generic[T]):
    """Redis-based distributed cache with fallback to in-memory.

    Features:
    - Async Redis operations
    - Automatic serialization/deserialization
    - Connection pooling
    - Fallback to LRU cache when Redis unavailable
    - Namespaced keys
    - TTL support
    """

    def __init__(
        self,
        namespace: str = "scenemachine",
        default_ttl_seconds: int = 3600,
        fallback_max_entries: int = 1000,
    ) -> None:
        """
        Initialize Redis cache.

        Args:
            namespace: Key prefix for namespacing
            default_ttl_seconds: Default TTL for entries
            fallback_max_entries: Max entries for fallback cache
        """
        self.namespace = namespace
        self.default_ttl = default_ttl_seconds

        # Redis client (lazy initialized)
        self._redis: Any | None = None
        self._redis_available = False
        self._redis_checked = False

        # Fallback in-memory cache
        self._fallback = LRUCache[T](
            max_entries=fallback_max_entries,
            default_ttl_seconds=default_ttl_seconds,
        )

        # Stats
        self._redis_hits = 0
        self._redis_misses = 0
        self._fallback_used = 0

    async def _get_redis(self) -> Any | None:
        """Get Redis client, initializing if needed."""
        if self._redis_checked:
            return self._redis

        try:
            import redis.asyncio as redis

            from scenemachine.config import get_settings

            settings = get_settings()

            self._redis = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                max_connections=settings.redis_max_connections,
                decode_responses=False,  # We handle encoding ourselves
            )

            # Test connection
            await self._redis.ping()
            self._redis_available = True
            logger.info("Redis cache connected successfully")

        except ImportError:
            logger.warning("redis package not installed, using in-memory fallback")
            self._redis_available = False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using in-memory fallback")
            self._redis_available = False

        self._redis_checked = True
        return self._redis if self._redis_available else None

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> T | None:
        """Get value from cache."""
        redis_client = await self._get_redis()

        if redis_client:
            try:
                data = await redis_client.get(self._make_key(key))
                if data:
                    self._redis_hits += 1
                    return pickle.loads(data)
                self._redis_misses += 1
                return None
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                self._fallback_used += 1

        # Fallback to in-memory
        return await self._fallback.get(key)

    async def set(
        self,
        key: str,
        value: T,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set value in cache."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        redis_client = await self._get_redis()

        if redis_client:
            try:
                data = pickle.dumps(value)
                await redis_client.setex(
                    self._make_key(key),
                    ttl,
                    data,
                )
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Fallback to in-memory
        await self._fallback.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        redis_client = await self._get_redis()

        if redis_client:
            try:
                result = await redis_client.delete(self._make_key(key))
                return result > 0
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        return await self._fallback.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        redis_client = await self._get_redis()

        if redis_client:
            try:
                return await redis_client.exists(self._make_key(key)) > 0
            except Exception as e:
                logger.warning(f"Redis exists error: {e}")

        return await self._fallback.get(key) is not None

    async def clear_namespace(self) -> int:
        """Clear all keys in namespace."""
        redis_client = await self._get_redis()
        count = 0

        if redis_client:
            try:
                pattern = f"{self.namespace}:*"
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100,
                    )
                    if keys:
                        await redis_client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")

        # Also clear fallback
        await self._fallback.clear()

        return count

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl_seconds: int | None = None,
    ) -> T:
        """Get value from cache or compute and store it."""
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        await self.set(key, value, ttl_seconds)
        return value

    async def mget(self, keys: list[str]) -> dict[str, T | None]:
        """Get multiple values at once."""
        redis_client = await self._get_redis()
        results: dict[str, T | None] = {}

        if redis_client:
            try:
                full_keys = [self._make_key(k) for k in keys]
                values = await redis_client.mget(full_keys)

                for key, value in zip(keys, values, strict=False):
                    if value:
                        results[key] = pickle.loads(value)
                        self._redis_hits += 1
                    else:
                        results[key] = None
                        self._redis_misses += 1

                return results
            except Exception as e:
                logger.warning(f"Redis mget error: {e}")

        # Fallback
        for key in keys:
            results[key] = await self._fallback.get(key)
        return results

    async def mset(
        self,
        items: dict[str, T],
        ttl_seconds: int | None = None,
    ) -> None:
        """Set multiple values at once."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        redis_client = await self._get_redis()

        if redis_client:
            try:
                pipe = redis_client.pipeline()
                for key, value in items.items():
                    data = pickle.dumps(value)
                    pipe.setex(self._make_key(key), ttl, data)
                await pipe.execute()
                return
            except Exception as e:
                logger.warning(f"Redis mset error: {e}")

        # Fallback
        for key, value in items.items():
            await self._fallback.set(key, value, ttl)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        fallback_stats = self._fallback.stats()
        total_redis = self._redis_hits + self._redis_misses

        return {
            "redis_available": self._redis_available,
            "redis_hits": self._redis_hits,
            "redis_misses": self._redis_misses,
            "redis_hit_rate": self._redis_hits / total_redis if total_redis > 0 else 0.0,
            "fallback_used": self._fallback_used,
            "fallback": fallback_stats,
        }

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._redis_checked = False


# Global Redis cache instances for different purposes
_generation_cache: RedisCache | None = None
_api_cache: RedisCache | None = None


def get_generation_cache() -> RedisCache:
    """Get cache for generation results."""
    global _generation_cache
    if _generation_cache is None:
        _generation_cache = RedisCache(
            namespace="scenemachine:gen",
            default_ttl_seconds=86400,  # 24 hours
        )
    return _generation_cache


def get_api_cache() -> RedisCache:
    """Get cache for API responses."""
    global _api_cache
    if _api_cache is None:
        from scenemachine.config import get_settings

        settings = get_settings()
        _api_cache = RedisCache(
            namespace="scenemachine:api",
            default_ttl_seconds=settings.cache_default_ttl_seconds,
        )
    return _api_cache


# ============================================================================
# Redis-backed Cache Decorator
# ============================================================================


def redis_cached(
    ttl_seconds: int = 3600,
    namespace: str = "scenemachine:func",
    key_func: Callable[..., str] | None = None,
):
    """
    Decorator for caching async function results in Redis.

    Args:
        ttl_seconds: Time to live in seconds
        namespace: Cache namespace
        key_func: Function to generate cache key from args
    """
    cache = RedisCache(namespace=namespace, default_ttl_seconds=ttl_seconds)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": str(sorted(kwargs.items())),
                }
                key = hashlib.md5(str(key_data).encode()).hexdigest()

            # Check cache
            result = await cache.get(key)
            if result is not None:
                return result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(key, result, ttl_seconds)

            return result

        wrapper.cache = cache  # type: ignore
        wrapper.cache_stats = cache.stats  # type: ignore

        return wrapper

    return decorator
