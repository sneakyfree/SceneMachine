# SceneMachine Caching Strategy

Complete documentation for SceneMachine's caching system including LRU cache, LLM response caching, file-based caching, and best practices.

## Table of Contents

- [Overview](#overview)
- [Cache Hierarchy](#cache-hierarchy)
- [LRU Cache](#lru-cache)
- [LLM Response Cache](#llm-response-cache)
- [File-Based Cache](#file-based-cache)
- [Cache Decorator](#cache-decorator)
- [Invalidation Strategies](#invalidation-strategies)
- [Monitoring & Statistics](#monitoring--statistics)
- [Best Practices](#best-practices)
- [Configuration](#configuration)

---

## Overview

SceneMachine uses a multi-tier caching strategy to optimize performance:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CACHE HIERARCHY                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐       │
│   │  L1 Cache   │   │  L2 Cache   │   │     L3 Cache        │       │
│   │  (Memory)   │──►│  (LLM)      │──►│   (File System)     │       │
│   │             │   │             │   │                     │       │
│   │ - LRUCache  │   │ - LLMCache  │   │ - FileCache         │       │
│   │ - Function  │   │ - Prompt    │   │ - Generated videos  │       │
│   │   results   │   │   responses │   │ - Thumbnails        │       │
│   │ - API data  │   │ - Embeddings│   │ - Exported files    │       │
│   │             │   │             │   │                     │       │
│   │ TTL: 1 hour │   │ TTL: 24 hrs │   │ TTL: 7 days         │       │
│   │ Size: ~100MB│   │ Size: 100MB │   │ Size: 10GB          │       │
│   └─────────────┘   └─────────────┘   └─────────────────────┘       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- **Reduced Latency**: Cache hits are 10-1000x faster than source
- **Cost Savings**: LLM cache saves API costs (tracked in real-time)
- **Bandwidth Savings**: File cache avoids regeneration
- **Improved UX**: Instant responses for cached data

---

## Cache Hierarchy

### L1: In-Memory LRU Cache

**Purpose:** Fast access to frequently used data
**Location:** `LRUCache` class
**Characteristics:**
- Sub-millisecond access time
- Limited by memory
- Lost on restart (unless persisted)

**Use Cases:**
- API response caching
- Computed values
- Database query results
- Configuration lookups

### L2: LLM Response Cache

**Purpose:** Avoid redundant LLM API calls
**Location:** `LLMCache` class
**Characteristics:**
- Prompt-based keying
- Temperature-aware (only caches deterministic responses)
- Cost tracking
- Optional persistence

**Use Cases:**
- Screenplay analysis
- Scene planning suggestions
- Character description generation
- Any LLM-generated content

### L3: File-Based Cache

**Purpose:** Store large generated assets
**Location:** `FileCache` class
**Characteristics:**
- Disk-based storage
- Configurable size limits
- LRU eviction
- Metadata tracking

**Use Cases:**
- Generated videos
- Thumbnails
- Exported files
- Model weights

---

## LRU Cache

### Implementation

Thread-safe LRU (Least Recently Used) cache with TTL support.

**File:** `packages/core/scenemachine/utils/cache.py`

```python
from scenemachine.utils.cache import LRUCache

# Create cache with 1000 entries, 100MB limit, 1 hour TTL
cache = LRUCache[dict](
    max_entries=1000,
    max_size_bytes=100 * 1024 * 1024,  # 100MB
    default_ttl_seconds=3600,           # 1 hour
)
```

### API Reference

#### Constructor

```python
LRUCache(
    max_entries: int = 1000,           # Maximum number of entries
    max_size_bytes: Optional[int] = None,  # Size limit (None = unlimited)
    default_ttl_seconds: Optional[int] = 3600,  # Default TTL (None = no expiry)
)
```

#### Methods

```python
# Get value (returns None if not found or expired)
value = await cache.get("key")

# Set value with optional custom TTL
await cache.set("key", value, ttl_seconds=1800)

# Delete entry
deleted = await cache.delete("key")

# Clear all entries
await cache.clear()

# Remove expired entries
removed_count = await cache.cleanup_expired()

# Get statistics
stats = cache.stats()
```

### Example Usage

```python
from scenemachine.utils.cache import LRUCache

# Create cache for project data
project_cache = LRUCache[dict](
    max_entries=100,
    default_ttl_seconds=300,  # 5 minutes
)

async def get_project(project_id: str) -> dict:
    # Check cache first
    cached = await project_cache.get(project_id)
    if cached:
        return cached

    # Fetch from database
    project = await db.get_project(project_id)

    # Cache the result
    await project_cache.set(project_id, project)

    return project
```

### Cache Entry Structure

Each cache entry stores:

```python
@dataclass
class CacheEntry:
    value: T              # The cached value
    created_at: float     # Timestamp when created
    expires_at: float     # Timestamp when expires (None = never)
    hits: int = 0         # Number of cache hits
    size_bytes: int = 0   # Estimated size in bytes
```

---

## LLM Response Cache

### Overview

Specialized cache for LLM API responses with cost tracking.

**Key Features:**
- Prompt-based keying with model awareness
- Only caches deterministic responses (temperature=0)
- Tracks tokens and cost saved
- Optional disk persistence

### Implementation

```python
from scenemachine.utils.cache import LLMCache

# Create LLM cache
llm_cache = LLMCache(
    max_entries=500,           # Max cached responses
    max_size_mb=100.0,         # 100MB limit
    default_ttl_hours=24.0,    # 24 hour TTL
    persist_path=Path("./cache/llm_cache.pkl"),  # Optional persistence
)
```

### API Reference

#### Constructor

```python
LLMCache(
    max_entries: int = 500,
    max_size_mb: float = 100.0,
    default_ttl_hours: float = 24.0,
    persist_path: Optional[Path] = None,
)
```

#### Methods

```python
# Get cached response (None if not found)
response = await llm_cache.get(
    prompt="Analyze this scene...",
    model="claude-3-opus-20240229",
    temperature=0.0,  # Only caches if temperature=0
    max_tokens=1000,
)

# Cache a response
await llm_cache.set(
    prompt="Analyze this scene...",
    model="claude-3-opus-20240229",
    response={"content": "...", "usage": {"total_tokens": 500}},
    temperature=0.0,
    ttl_hours=48.0,  # Optional custom TTL
)

# Get statistics
stats = llm_cache.stats()
# Returns: {
#     "entries": 100,
#     "hits": 500,
#     "misses": 50,
#     "hit_rate": 0.91,
#     "cost_saved_usd": 5.50,
#     "tokens_saved": 550000,
# }
```

### Cache Key Generation

Keys are generated from prompt + model + parameters:

```python
def _hash_prompt(prompt: str, model: str, **kwargs) -> str:
    data = {
        "prompt": prompt,
        "model": model,
        **{k: v for k, v in sorted(kwargs.items()) if v is not None},
    }
    content = json.dumps(data, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()
```

### Example Usage

```python
from scenemachine.utils.cache import get_llm_cache

llm_cache = get_llm_cache()  # Get global instance

async def analyze_scene(scene_text: str) -> dict:
    prompt = f"Analyze this scene: {scene_text}"

    # Check cache first
    cached = await llm_cache.get(
        prompt=prompt,
        model="claude-3-opus",
        temperature=0.0,
    )
    if cached:
        return cached

    # Call LLM API
    response = await anthropic_client.create(
        model="claude-3-opus",
        prompt=prompt,
        temperature=0.0,
    )

    # Cache the response
    await llm_cache.set(
        prompt=prompt,
        model="claude-3-opus",
        response=response,
        temperature=0.0,
    )

    return response
```

### Cost Tracking

The LLM cache tracks cost savings:

```python
# Get cost savings report
stats = llm_cache.stats()

print(f"Tokens saved: {stats['tokens_saved']:,}")
print(f"Cost saved: ${stats['cost_saved_usd']:.2f}")
print(f"Cache hit rate: {stats['hit_rate']:.1%}")
```

**Estimated cost per 1K tokens:** ~$0.01 (averaged across models)

---

## File-Based Cache

### Overview

Disk-based cache for large files with LRU eviction.

**Key Features:**
- Stores large files (videos, images, models)
- Configurable size limits (default 10GB)
- Automatic LRU eviction
- TTL-based expiration
- Metadata tracking

### Implementation

```python
from pathlib import Path
from scenemachine.utils.cache import FileCache

# Create file cache
file_cache = FileCache(
    cache_dir=Path("./data/cache"),
    max_size_gb=10.0,       # 10GB limit
    default_ttl_days=7,     # 7 day TTL
)
```

### API Reference

#### Constructor

```python
FileCache(
    cache_dir: Path,                  # Directory for cached files
    max_size_gb: float = 10.0,        # Maximum size in GB
    default_ttl_days: int = 7,        # Default TTL in days
)
```

#### Methods

```python
# Get cached file path (None if not found/expired)
path = await file_cache.get("video_shot_123")
if path:
    # Use cached file at path
    pass

# Cache a file (copy by default)
cached_path = await file_cache.put(
    key="video_shot_123",
    source_path=Path("/tmp/generated_video.mp4"),
    ttl_seconds=86400 * 30,  # Optional: 30 days
    move=False,              # Copy (True = move instead)
)

# Delete cached file
deleted = await file_cache.delete("video_shot_123")

# Cleanup expired entries
removed_count = await file_cache.cleanup_expired()

# Get statistics
stats = file_cache.stats()
# Returns: {
#     "entries": 50,
#     "size_bytes": 5000000000,
#     "size_mb": 4768.37,
#     "max_size_gb": 10.0,
#     "total_hits": 200,
# }
```

### Directory Structure

Files are stored with hashed paths to avoid conflicts:

```
./data/cache/
├── .cache_meta.json          # Metadata file
├── ab/
│   └── cdef1234...           # Cached file (hash: abcdef1234...)
├── cd/
│   └── ef567890...           # Another cached file
└── ...
```

### Example Usage

```python
from scenemachine.utils.cache import FileCache
from pathlib import Path

video_cache = FileCache(
    cache_dir=Path("./data/video_cache"),
    max_size_gb=50.0,
    default_ttl_days=30,
)

async def get_shot_video(shot_id: str) -> Path:
    cache_key = f"shot_{shot_id}"

    # Check cache
    cached = await video_cache.get(cache_key)
    if cached and cached.exists():
        return cached

    # Generate video
    video_path = await generate_video(shot_id)

    # Cache the result
    cached_path = await video_cache.put(
        key=cache_key,
        source_path=video_path,
        move=True,  # Move instead of copy
    )

    return cached_path
```

---

## Cache Decorator

### Overview

Convenient decorator for caching async function results.

### Usage

```python
from scenemachine.utils.cache import cached, LRUCache

# Basic usage (creates new cache per function)
@cached(ttl_seconds=3600)
async def expensive_computation(x: int, y: int) -> int:
    await asyncio.sleep(1)  # Simulate expensive work
    return x + y

# Call normally - first call computes, subsequent calls use cache
result = await expensive_computation(1, 2)  # Computes
result = await expensive_computation(1, 2)  # Uses cache
```

### Custom Key Function

```python
# Custom cache key generation
def make_key(project_id: str, **kwargs) -> str:
    return f"project_{project_id}"

@cached(ttl_seconds=300, key_func=make_key)
async def get_project_stats(project_id: str) -> dict:
    return await db.compute_stats(project_id)
```

### Shared Cache Instance

```python
# Share cache between multiple functions
shared_cache = LRUCache[dict](max_entries=500)

@cached(ttl_seconds=3600, cache=shared_cache)
async def get_user(user_id: str) -> dict:
    return await db.get_user(user_id)

@cached(ttl_seconds=3600, cache=shared_cache)
async def get_profile(user_id: str) -> dict:
    return await db.get_profile(user_id)
```

### Clearing Cache

```python
@cached(ttl_seconds=3600)
async def get_data():
    pass

# Clear cache for this function
await get_data.cache_clear()

# Access cache directly
stats = get_data.cache.stats()
```

---

## Invalidation Strategies

### Time-Based Invalidation

All caches support TTL-based expiration:

```python
# Set TTL on cache creation
cache = LRUCache(default_ttl_seconds=3600)

# Override TTL per entry
await cache.set("key", value, ttl_seconds=300)

# Cleanup expired entries
removed = await cache.cleanup_expired()
```

### Event-Based Invalidation

Invalidate cache when data changes:

```python
class ProjectService:
    def __init__(self):
        self.cache = LRUCache[dict]()

    async def get_project(self, project_id: str) -> dict:
        cached = await self.cache.get(project_id)
        if cached:
            return cached

        project = await self._load_project(project_id)
        await self.cache.set(project_id, project)
        return project

    async def update_project(self, project_id: str, data: dict) -> dict:
        # Update database
        project = await self._save_project(project_id, data)

        # Invalidate cache
        await self.cache.delete(project_id)

        return project

    async def delete_project(self, project_id: str) -> None:
        await self._delete_project(project_id)
        await self.cache.delete(project_id)
```

### Pattern-Based Invalidation

For invalidating related entries:

```python
async def invalidate_project_caches(project_id: str):
    """Invalidate all caches related to a project."""
    # Clear project cache
    await project_cache.delete(project_id)

    # Clear scene caches for this project
    # (In practice, you'd track project->scene mappings)
    for scene_id in await get_scene_ids(project_id):
        await scene_cache.delete(scene_id)

    # Clear file cache for generated videos
    for shot_id in await get_shot_ids(project_id):
        await video_cache.delete(f"shot_{shot_id}")
```

### Manual Invalidation

Clear specific entries or entire cache:

```python
# Delete specific entry
await cache.delete("key")

# Clear all entries
await cache.clear()
```

---

## Monitoring & Statistics

### Cache Statistics

All caches provide statistics:

```python
# LRU Cache stats
lru_stats = cache.stats()
# {
#     "entries": 150,
#     "max_entries": 1000,
#     "size_bytes": 15000000,
#     "max_size_bytes": 104857600,
#     "hits": 500,
#     "misses": 50,
#     "hit_rate": 0.91,
# }

# LLM Cache stats (includes cost tracking)
llm_stats = llm_cache.stats()
# {
#     ...base stats...,
#     "cost_saved_usd": 12.50,
#     "tokens_saved": 1250000,
# }

# File Cache stats
file_stats = file_cache.stats()
# {
#     "entries": 50,
#     "size_bytes": 5000000000,
#     "size_mb": 4768.37,
#     "max_size_gb": 10.0,
#     "total_hits": 200,
# }
```

### Health Checks

```python
async def check_cache_health():
    """Check cache system health."""
    results = {}

    # Check LRU cache
    lru_stats = cache.stats()
    results["lru_cache"] = {
        "status": "healthy" if lru_stats["hit_rate"] > 0.5 else "degraded",
        "hit_rate": lru_stats["hit_rate"],
        "entries": lru_stats["entries"],
    }

    # Check LLM cache
    llm_stats = get_llm_cache().stats()
    results["llm_cache"] = {
        "status": "healthy" if llm_stats["hit_rate"] > 0.3 else "degraded",
        "hit_rate": llm_stats["hit_rate"],
        "cost_saved": llm_stats["cost_saved_usd"],
    }

    # Check file cache
    file_stats = file_cache.stats()
    usage_pct = file_stats["size_mb"] / (file_stats["max_size_gb"] * 1024)
    results["file_cache"] = {
        "status": "healthy" if usage_pct < 0.9 else "warning",
        "usage_percent": usage_pct * 100,
        "entries": file_stats["entries"],
    }

    return results
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log cache performance periodically
async def log_cache_stats():
    stats = cache.stats()
    logger.info(
        "cache_stats",
        extra={
            "entries": stats["entries"],
            "hit_rate": stats["hit_rate"],
            "size_mb": stats["size_bytes"] / (1024 * 1024),
        }
    )
```

---

## Best Practices

### When to Cache

**Good candidates for caching:**
- Expensive database queries
- API responses from external services
- Computed values that don't change frequently
- LLM responses (especially with temperature=0)
- Generated assets (videos, thumbnails)

**Poor candidates for caching:**
- User-specific real-time data
- Frequently updated data
- Security-sensitive data
- Very large objects (use file cache instead)

### Cache Key Design

```python
# Good: Specific, deterministic keys
key = f"project_{project_id}_stats_v2"
key = f"scene_{scene_id}_shots"

# Bad: Generic or non-deterministic keys
key = f"data_{random.randint(0, 100)}"  # Non-deterministic
key = "stats"  # Too generic
```

### TTL Guidelines

| Data Type | Recommended TTL | Notes |
|-----------|-----------------|-------|
| Static config | 24 hours | Rarely changes |
| User preferences | 1 hour | May be updated |
| API responses | 5-15 minutes | Balance freshness/performance |
| LLM responses | 24+ hours | Expensive to regenerate |
| Generated videos | 7-30 days | Very expensive to regenerate |
| Thumbnails | 7 days | Can regenerate if needed |

### Memory Management

```python
# Set appropriate limits
cache = LRUCache(
    max_entries=1000,
    max_size_bytes=100 * 1024 * 1024,  # 100MB
)

# Schedule regular cleanup
async def cleanup_task():
    while True:
        await cache.cleanup_expired()
        await asyncio.sleep(300)  # Every 5 minutes
```

### Error Handling

```python
async def get_with_fallback(key: str) -> Optional[dict]:
    try:
        return await cache.get(key)
    except Exception as e:
        logger.warning(f"Cache error for {key}: {e}")
        return None  # Fall through to source

async def set_safe(key: str, value: dict) -> None:
    try:
        await cache.set(key, value)
    except Exception as e:
        logger.warning(f"Failed to cache {key}: {e}")
        # Don't fail the operation if caching fails
```

### Testing

```python
import pytest
from scenemachine.utils.cache import LRUCache

@pytest.fixture
async def test_cache():
    """Create a fresh cache for each test."""
    cache = LRUCache(max_entries=10, default_ttl_seconds=60)
    yield cache
    await cache.clear()

async def test_cache_hit(test_cache):
    await test_cache.set("key", "value")
    result = await test_cache.get("key")
    assert result == "value"

async def test_cache_expiry(test_cache):
    await test_cache.set("key", "value", ttl_seconds=0)
    result = await test_cache.get("key")
    assert result is None  # Expired immediately
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CACHE_SIZE_GB` | `10` | Maximum file cache size |
| `LLM_CACHE_MAX_ENTRIES` | `500` | Maximum LLM cache entries |
| `LLM_CACHE_TTL_HOURS` | `24` | LLM cache default TTL |
| `CACHE_DIR` | `./data/cache` | Cache directory path |

### Runtime Settings

Via database settings (UserSettings model):

```python
# Settings table
max_cache_size_gb: int = 10
auto_cleanup_temp_files: bool = True
```

### Recommended Settings

**Development:**
```python
LRUCache(max_entries=100, max_size_bytes=10*1024*1024)
FileCache(max_size_gb=5.0)
LLMCache(max_entries=100, persist_path=None)  # No persistence
```

**Production:**
```python
LRUCache(max_entries=1000, max_size_bytes=100*1024*1024)
FileCache(max_size_gb=50.0)
LLMCache(max_entries=500, persist_path=Path("/var/cache/llm.pkl"))
```

---

## Related Documentation

- [PERFORMANCE.md](PERFORMANCE.md) - Performance optimization
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [DATABASE.md](DATABASE.md) - Database caching considerations
