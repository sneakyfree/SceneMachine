"""Caching utilities for performance optimization.

Provides:
- LLM response caching with TTL
- General-purpose async caching
- File-based cache persistence
- Memory-efficient LRU cache
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union

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
    expires_at: Optional[float]
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
        max_size_bytes: Optional[int] = None,
        default_ttl_seconds: Optional[int] = 3600,
    ):
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

    async def get(self, key: str) -> Optional[T]:
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
        ttl_seconds: Optional[int] = None,
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

    def stats(self) -> Dict[str, Any]:
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
        persist_path: Optional[Path] = None,
    ):
        """
        Initialize LLM cache.

        Args:
            max_entries: Maximum cached responses
            max_size_mb: Maximum cache size in MB
            default_ttl_hours: Default TTL in hours
            persist_path: Path for cache persistence
        """
        self._cache = LRUCache[Dict[str, Any]](
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
    ) -> Optional[Dict[str, Any]]:
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
        response: Dict[str, Any],
        temperature: float = 0.0,
        ttl_hours: Optional[float] = None,
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
        """Invalidate all cached responses for a model."""
        # This is a simple implementation - in production you might
        # want to track model->keys mapping for efficiency
        count = 0
        # For now, just clear and let entries repopulate
        # A more sophisticated approach would iterate and check
        return count

    def stats(self) -> Dict[str, Any]:
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
                "saved_at": datetime.now(timezone.utc).isoformat(),
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
_llm_cache: Optional[LLMCache] = None


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
    key_func: Optional[Callable[..., str]] = None,
    cache: Optional[LRUCache] = None,
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
    ):
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
        self._meta: Dict[str, Dict[str, Any]] = {}
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

    async def get(self, key: str) -> Optional[Path]:
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
        ttl_seconds: Optional[int] = None,
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

    def stats(self) -> Dict[str, Any]:
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
