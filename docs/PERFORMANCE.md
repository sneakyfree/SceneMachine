# SceneMachine Performance Guide

Performance benchmarks, load testing results, optimization techniques, and tuning recommendations.

## Table of Contents

- [Overview](#overview)
- [Performance Baselines](#performance-baselines)
- [Benchmark Results](#benchmark-results)
- [Load Testing](#load-testing)
- [Optimization Techniques](#optimization-techniques)
- [Performance Monitoring](#performance-monitoring)
- [Tuning Guide](#tuning-guide)
- [Troubleshooting](#troubleshooting)

---

## Overview

SceneMachine is designed for responsive user experience while handling compute-intensive AI operations. The architecture separates:

- **UI Thread** - Electron/React frontend (target: <16ms frame time)
- **IPC Handler** - Unix socket communication (<5ms latency)
- **API Layer** - FastAPI async operations (<100ms typical)
- **Generation Workers** - Background GPU operations (async, non-blocking)

**Performance Philosophy:**
- Keep UI responsive at all times
- Offload heavy work to background workers
- Use async I/O throughout the backend
- Cache aggressively (LLM responses, file operations)
- Stream large operations (video assembly, exports)

---

## Performance Baselines

### Target Metrics

| Operation | Target | Warning | Critical |
|-----------|--------|---------|----------|
| API response (simple) | <50ms | >100ms | >500ms |
| API response (DB query) | <100ms | >200ms | >1s |
| Screenplay parsing | <500ms/page | >1s | >2s |
| Scene planning (LLM) | <5s | >10s | >30s |
| IPC round-trip | <10ms | >50ms | >200ms |
| UI frame time | <16ms | >33ms | >100ms |
| Export encoding | Real-time | 2x real-time | 5x real-time |

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent projects | 10+ | Limited by memory |
| Active generation jobs | 2-10 | Configurable via `MAX_CONCURRENT_GENERATIONS` |
| API requests/second | 100+ | Single instance |
| Database connections | 20-50 | Pool size tunable |
| WebSocket connections | 50+ | Per instance |

---

## Benchmark Results

### Screenplay Parsing

Parsing performance for screenplay text processing:

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| Line splitting (1000 lines) | 0.5ms | 2000 | Basic text processing |
| Scene heading detection | 0.8ms | 1250 | Regex matching |
| Character extraction | 1.2ms | 833 | Name pattern matching |
| Full screenplay parse | 50-200ms | 5-20 | Depends on page count |

**Benchmark Code:**
```bash
pytest tests/performance/test_benchmarks.py -v -k "parsing"
```

### Data Structure Operations

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| List iteration (1000 items) | 0.1ms | 10000 | Simple traversal |
| Dict lookup (100 keys) | 0.01ms | 100000 | Hash table performance |
| List filtering (1000 items) | 0.2ms | 5000 | List comprehension |
| List sorting (1000 items) | 0.5ms | 2000 | Timsort |

### JSON Serialization

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| Serialize 100 objects | 0.3ms | 3300 | json.dumps() |
| Deserialize 100 objects | 0.2ms | 5000 | json.loads() |
| Pydantic model validation | 0.5ms | 2000 | Type checking overhead |

### Async Operations

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| asyncio.sleep(0) | 0.01ms | 100000 | Event loop overhead |
| asyncio.gather (10 tasks) | 0.1ms | 10000 | Task scheduling |
| asyncio.Queue (100 put/get) | 1ms | 1000 | Synchronized queue |

### Cache Performance

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| Dict cache lookup (100 keys) | 0.01ms | 100000 | Simple dict |
| LRU cache hit (100 calls) | 0.02ms | 50000 | functools.lru_cache |
| File cache read | 1-5ms | 200-1000 | Depends on file size |

### UUID Generation

| Operation | Avg Time | Ops/sec | Notes |
|-----------|----------|---------|-------|
| uuid4() generation | 0.002ms | 500000 | Standard library |
| UUID to string | 0.001ms | 1000000 | str(uuid) |

---

## Load Testing

### Concurrent Database Operations

Tested with mock database (1ms simulated latency):

| Test | Requests | RPS | Success Rate | Avg Latency | P95 Latency |
|------|----------|-----|--------------|-------------|-------------|
| 50 concurrent writes | 50 | 45 | 100% | 1.2ms | 1.5ms |
| 100 concurrent reads | 100 | 180 | 100% | 0.6ms | 0.8ms |
| Mixed read/write | 100 | 90 | 100% | 1.1ms | 1.4ms |
| 500 concurrent (stress) | 500 | 400+ | >99% | 1.5ms | 3.0ms |

### Queue Throughput

Generation queue processing with mock jobs:

| Concurrency | Jobs | Duration | Throughput |
|-------------|------|----------|------------|
| 2 workers | 50 | 0.3s | 166 jobs/sec |
| 5 workers | 50 | 0.12s | 416 jobs/sec |
| 10 workers | 100 | 0.1s | 1000 jobs/sec |

### Rate Limiting Effectiveness

| Limit | Window | Requests | Allowed | Blocked |
|-------|--------|----------|---------|---------|
| 10/sec | 1s | 20 | 10 | 10 |
| 100/min | 60s | 200 | 100 | 100 |
| 1000/min (burst) | 60s | 1100 | ~1050 | ~50 |

### Memory Usage

| Dataset | Size | Memory | Notes |
|---------|------|--------|-------|
| 10,000 project items | ~10MB | ~15MB | Dict overhead |
| 50,000 small objects | ~5MB | ~20MB | Object overhead |
| Large screenplay (200 pages) | ~2MB | ~5MB | Parsed structure |

### Running Load Tests

```bash
# Run all load tests
pytest tests/performance/test_load.py -v

# Run specific test
pytest tests/performance/test_load.py -v -k "concurrent"

# Generate summary
pytest tests/performance/test_load.py -v -k "summary"
```

---

## Optimization Techniques

### Frontend (React/Electron)

**Code Splitting:**
```javascript
// Lazy load heavy components
const VideoPlayer = React.lazy(() => import('./VideoPlayer'));
const Timeline = React.lazy(() => import('./Timeline'));

// Use Suspense for loading states
<Suspense fallback={<Skeleton />}>
  <VideoPlayer />
</Suspense>
```

**Memoization:**
```javascript
// Memoize expensive renders
const SceneList = React.memo(({ scenes }) => {
  return scenes.map(scene => <SceneCard key={scene.id} {...scene} />);
});

// Use useMemo for computed values
const sortedShots = useMemo(() => {
  return shots.sort((a, b) => a.sequence - b.sequence);
}, [shots]);

// Use useCallback for stable function references
const handleClick = useCallback((id) => {
  onSelect(id);
}, [onSelect]);
```

**Virtual Scrolling:**
```javascript
// Use virtualization for long lists
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={shots.length}
  itemSize={80}
>
  {({ index, style }) => (
    <ShotRow style={style} shot={shots[index]} />
  )}
</FixedSizeList>
```

### Backend (Python/FastAPI)

**Async I/O:**
```python
# Use async for all I/O operations
async def process_screenplay(file_path: str):
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    return await parse_screenplay(content)

# Parallel API calls
async def get_all_data():
    results = await asyncio.gather(
        get_project_data(),
        get_character_data(),
        get_scene_data(),
    )
    return results
```

**Connection Pooling:**
```python
# SQLAlchemy async engine with pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # Base pool size
    max_overflow=10,        # Additional connections allowed
    pool_timeout=30,        # Wait time for connection
    pool_recycle=1800,      # Recycle connections after 30 min
)
```

**Eager Loading:**
```python
# Avoid N+1 queries with eager loading
stmt = (
    select(Project)
    .options(
        selectinload(Project.screenplay),
        selectinload(Project.characters),
        selectinload(Project.scenes).selectinload(Scene.shots),
    )
    .where(Project.id == project_id)
)
```

**Response Streaming:**
```python
# Stream large responses
from fastapi.responses import StreamingResponse

async def export_video():
    async def generate():
        async for chunk in assemble_video():
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="video/mp4",
    )
```

### Database

**Indexing Strategy:**
```sql
-- Frequently filtered columns
CREATE INDEX ix_shots_scene_id ON shots(scene_id);
CREATE INDEX ix_generation_jobs_status ON generation_jobs(status);

-- Composite index for common queries
CREATE INDEX ix_shots_scene_state ON shots(scene_id, state);

-- Partial index for active records
CREATE INDEX ix_active_jobs ON generation_jobs(status)
WHERE status IN ('pending', 'queued', 'running');
```

**Query Optimization:**
```python
# Use specific columns instead of SELECT *
stmt = select(Project.id, Project.name, Project.state)

# Use EXISTS for existence checks
stmt = select(exists().where(Shot.scene_id == scene_id))

# Batch updates
stmt = (
    update(Shot)
    .where(Shot.scene_id == scene_id)
    .values(state=ShotState.QUEUED)
)
await session.execute(stmt)
```

### Caching

**LLM Response Caching:**
```python
from scenemachine.utils.cache import LLMCache

llm_cache = LLMCache(max_size=1000, ttl_seconds=3600)

async def generate_with_cache(prompt: str):
    cached = await llm_cache.get(prompt)
    if cached:
        return cached

    response = await llm_client.generate(prompt)
    await llm_cache.set(prompt, response)
    return response
```

**File Caching:**
```python
from scenemachine.utils.cache import FileCache

file_cache = FileCache(
    cache_dir="./data/cache",
    max_size_gb=10,
    ttl_seconds=86400,
)

async def get_thumbnail(shot_id: str):
    cached = await file_cache.get(f"thumb_{shot_id}")
    if cached:
        return cached

    thumbnail = await generate_thumbnail(shot_id)
    await file_cache.set(f"thumb_{shot_id}", thumbnail)
    return thumbnail
```

---

## Performance Monitoring

### Key Metrics to Track

**Application Metrics:**
- Request latency (avg, p95, p99)
- Error rate
- Active connections
- Queue depth
- Cache hit ratio

**System Metrics:**
- CPU utilization
- Memory usage
- Disk I/O
- Network I/O
- GPU utilization (for generation)

### Profiling Tools

**Python Profiling:**
```bash
# cProfile for CPU profiling
python -m cProfile -o profile.stats app.py

# Visualize with snakeviz
snakeviz profile.stats

# Memory profiling with memory_profiler
python -m memory_profiler app.py
```

**Async Profiling:**
```python
import yappi

yappi.set_clock_type("wall")  # Wall clock for async
yappi.start()

# ... run your code ...

yappi.stop()
stats = yappi.get_func_stats()
stats.print_all()
```

**Database Query Analysis:**
```python
# Enable SQL echo for debugging
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Logs all SQL
)

# Use EXPLAIN ANALYZE
async with session.begin():
    result = await session.execute(
        text("EXPLAIN ANALYZE SELECT * FROM projects WHERE state = 'generating'")
    )
    print(result.fetchall())
```

### Logging Performance Data

```python
import time
import logging

logger = logging.getLogger(__name__)

async def timed_operation():
    start = time.perf_counter()

    result = await some_operation()

    elapsed = time.perf_counter() - start
    logger.info(
        "operation_completed",
        extra={
            "operation": "some_operation",
            "duration_ms": elapsed * 1000,
            "result_size": len(result),
        }
    )

    return result
```

---

## Tuning Guide

### Application Tuning

**Worker Configuration:**
```bash
# Single user (desktop app)
WORKERS=1
MAX_CONCURRENT_GENERATIONS=2

# Multi-user server
WORKERS=4  # Match CPU cores
MAX_CONCURRENT_GENERATIONS=10
```

**Timeout Configuration:**
```bash
# Standard operations
GENERATION_TIMEOUT_SECONDS=600  # 10 minutes

# For complex generations
GENERATION_TIMEOUT_SECONDS=1800  # 30 minutes
```

**Cache Configuration:**
```bash
# LLM cache (in-memory)
LLM_CACHE_MAX_SIZE=1000
LLM_CACHE_TTL_SECONDS=3600

# File cache
MAX_CACHE_SIZE_GB=10
FILE_CACHE_TTL_SECONDS=86400
```

### Database Tuning

**PostgreSQL Configuration:**
```conf
# postgresql.conf

# Memory
shared_buffers = 256MB          # 25% of RAM
work_mem = 16MB                 # Per-operation memory
maintenance_work_mem = 128MB    # For maintenance tasks

# Connections
max_connections = 100
connection_timeout = 30

# Write performance
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Query planning
effective_cache_size = 768MB    # 75% of RAM
random_page_cost = 1.1          # SSD optimization
```

**SQLite Configuration (Development):**
```python
# Enable WAL mode for better concurrency
engine = create_async_engine(
    "sqlite+aiosqlite:///./data/scenemachine.db",
    connect_args={"check_same_thread": False},
)

# Set pragmas
async with engine.connect() as conn:
    await conn.execute(text("PRAGMA journal_mode=WAL"))
    await conn.execute(text("PRAGMA synchronous=NORMAL"))
    await conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB
```

### System Tuning

**Linux:**
```bash
# Increase file descriptor limit
ulimit -n 65535

# TCP tuning
sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_max_syn_backlog=65535

# Memory
sysctl -w vm.swappiness=10
```

**GPU (NVIDIA):**
```bash
# Set persistence mode
nvidia-smi -pm 1

# Set power limit (optional, for thermal management)
nvidia-smi -pl 250

# Monitor GPU
nvidia-smi dmon -s u
```

---

## Troubleshooting

### High Latency

**Symptoms:**
- API responses slow (>500ms)
- UI feels sluggish

**Diagnosis:**
```python
# Check database query time
import time

async def diagnose_latency():
    start = time.perf_counter()
    await session.execute(select(Project).limit(1))
    db_time = time.perf_counter() - start

    if db_time > 0.1:
        print(f"Database slow: {db_time*1000:.2f}ms")

    # Check cache hit rate
    cache_stats = await get_cache_stats()
    print(f"Cache hit rate: {cache_stats.hit_rate}%")
```

**Solutions:**
1. Add missing indexes
2. Enable eager loading
3. Increase connection pool size
4. Check network latency to database

### Memory Issues

**Symptoms:**
- Increasing memory usage over time
- OOM errors

**Diagnosis:**
```python
import tracemalloc

tracemalloc.start()

# ... run operations ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

**Solutions:**
1. Check for unclosed resources
2. Limit cache sizes
3. Use generators for large datasets
4. Enable garbage collection logging

### Queue Backlogs

**Symptoms:**
- Jobs stuck in pending state
- Generation takes too long

**Diagnosis:**
```bash
# Check queue depth
curl http://localhost:8000/api/v1/generation/queue/status

# Check worker status
curl http://localhost:8000/api/v1/generation/workers
```

**Solutions:**
1. Increase `MAX_CONCURRENT_GENERATIONS`
2. Add more GPU workers
3. Check for failed jobs blocking queue
4. Increase job timeout

### High CPU Usage

**Symptoms:**
- CPU at 100%
- System unresponsive

**Diagnosis:**
```bash
# Profile CPU usage
py-spy record -o profile.svg -- python app.py

# Check for busy loops
py-spy dump --pid <pid>
```

**Solutions:**
1. Check for synchronous blocking calls
2. Add async to I/O operations
3. Reduce polling frequency
4. Offload work to background workers

---

## Related Documentation

- [CACHING.md](CACHING.md) - Caching strategy details
- [CONFIGURATION.md](CONFIGURATION.md) - Tuning configuration options
- [DATABASE.md](DATABASE.md) - Database optimization
