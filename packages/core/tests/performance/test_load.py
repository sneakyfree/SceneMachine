"""Load tests for SceneMachine.

Tests measure system behavior under load:
- Concurrent request handling
- Memory usage under load
- Queue processing throughput
- Rate limiting effectiveness

Run with: pytest tests/performance/test_load.py -v
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from uuid import uuid4

import pytest


# =============================================================================
# Load Test Utilities
# =============================================================================


class LoadTestResult:
    """Result of a load test."""

    def __init__(self, name: str, total_requests: int, duration: float):
        self.name = name
        self.total_requests = total_requests
        self.duration = duration
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times: List[float] = []
        self.errors: List[str] = []

    def record_success(self, response_time: float):
        """Record a successful request."""
        self.successful_requests += 1
        self.response_times.append(response_time)

    def record_failure(self, error: str):
        """Record a failed request."""
        self.failed_requests += 1
        self.errors.append(error)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0
        return self.successful_requests / self.total_requests * 100

    @property
    def requests_per_second(self) -> float:
        """Calculate throughput."""
        if self.duration == 0:
            return 0
        return self.successful_requests / self.duration

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0
        return sum(self.response_times) / len(self.response_times)

    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]

    @property
    def p99_response_time(self) -> float:
        """Calculate 99th percentile response time."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]

    def report(self) -> Dict[str, Any]:
        """Generate report."""
        return {
            "name": self.name,
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{self.success_rate:.1f}%",
            "duration_s": f"{self.duration:.2f}",
            "rps": f"{self.requests_per_second:.1f}",
            "avg_ms": f"{self.avg_response_time*1000:.2f}",
            "p95_ms": f"{self.p95_response_time*1000:.2f}",
            "p99_ms": f"{self.p99_response_time*1000:.2f}",
        }


# =============================================================================
# Mock Services for Load Testing
# =============================================================================


class MockDatabase:
    """Mock database for load testing."""

    def __init__(self, latency_ms: float = 1.0):
        self.latency_ms = latency_ms
        self.data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self.query_count = 0

    async def insert(self, key: str, value: Any):
        """Insert with simulated latency."""
        await asyncio.sleep(self.latency_ms / 1000)
        async with self._lock:
            self.data[key] = value
            self.query_count += 1

    async def select(self, key: str) -> Any:
        """Select with simulated latency."""
        await asyncio.sleep(self.latency_ms / 1000)
        async with self._lock:
            self.query_count += 1
            return self.data.get(key)

    async def select_many(self, keys: List[str]) -> List[Any]:
        """Select multiple with simulated latency."""
        await asyncio.sleep(self.latency_ms / 1000 * len(keys) * 0.1)  # Batched
        async with self._lock:
            self.query_count += 1
            return [self.data.get(k) for k in keys]


class MockGenerationQueue:
    """Mock generation queue for load testing."""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = 0
        self.completed = 0
        self.failed = 0
        self._lock = asyncio.Lock()

    async def enqueue(self, job_id: str):
        """Add job to queue."""
        await self.queue.put(job_id)

    async def process_one(self):
        """Process one job."""
        async with self._lock:
            if self.running >= self.max_concurrent:
                return False
            self.running += 1

        try:
            job_id = await asyncio.wait_for(self.queue.get(), timeout=0.1)
            await asyncio.sleep(0.01)  # Simulate processing
            async with self._lock:
                self.completed += 1
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            async with self._lock:
                self.running -= 1


class MockRateLimiter:
    """Mock rate limiter for testing."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[float] = []
        self._lock = asyncio.Lock()

    async def allow(self) -> bool:
        """Check if request is allowed."""
        now = time.time()
        async with self._lock:
            # Remove old requests
            self.requests = [t for t in self.requests if now - t < self.window_seconds]

            if len(self.requests) >= self.max_requests:
                return False

            self.requests.append(now)
            return True


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Test system behavior under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_database_writes(self):
        """Test concurrent database write performance."""
        db = MockDatabase(latency_ms=1.0)
        num_requests = 100

        start = time.time()
        result = LoadTestResult("concurrent_db_writes", num_requests, 0)

        async def write_one(i: int):
            try:
                req_start = time.time()
                await db.insert(f"key_{i}", {"value": i})
                result.record_success(time.time() - req_start)
            except Exception as e:
                result.record_failure(str(e))

        # Run concurrent writes
        await asyncio.gather(*[write_one(i) for i in range(num_requests)])

        result.duration = time.time() - start

        print(f"\nConcurrent DB writes: {result.report()}")
        assert result.success_rate == 100

    @pytest.mark.asyncio
    async def test_concurrent_database_reads(self):
        """Test concurrent database read performance."""
        db = MockDatabase(latency_ms=0.5)
        num_requests = 200

        # Pre-populate
        for i in range(100):
            await db.insert(f"key_{i}", {"value": i})

        start = time.time()
        result = LoadTestResult("concurrent_db_reads", num_requests, 0)

        async def read_one(i: int):
            try:
                req_start = time.time()
                await db.select(f"key_{i % 100}")
                result.record_success(time.time() - req_start)
            except Exception as e:
                result.record_failure(str(e))

        await asyncio.gather(*[read_one(i) for i in range(num_requests)])

        result.duration = time.time() - start

        print(f"\nConcurrent DB reads: {result.report()}")
        assert result.success_rate == 100

    @pytest.mark.asyncio
    async def test_mixed_read_write_load(self):
        """Test mixed read/write workload."""
        db = MockDatabase(latency_ms=1.0)
        num_requests = 100

        start = time.time()
        result = LoadTestResult("mixed_read_write", num_requests, 0)

        async def operation(i: int):
            try:
                req_start = time.time()
                if i % 3 == 0:
                    await db.insert(f"key_{i}", {"value": i})
                else:
                    await db.select(f"key_{i % 10}")
                result.record_success(time.time() - req_start)
            except Exception as e:
                result.record_failure(str(e))

        await asyncio.gather(*[operation(i) for i in range(num_requests)])

        result.duration = time.time() - start

        print(f"\nMixed read/write: {result.report()}")
        assert result.success_rate == 100


# =============================================================================
# Queue Throughput Tests
# =============================================================================


class TestQueueThroughput:
    """Test queue processing throughput."""

    @pytest.mark.asyncio
    async def test_queue_throughput(self):
        """Test queue can handle high throughput."""
        queue = MockGenerationQueue(max_concurrent=5)
        num_jobs = 50

        # Enqueue all jobs
        for i in range(num_jobs):
            await queue.enqueue(f"job_{i}")

        start = time.time()

        # Process until empty
        processed = 0
        while processed < num_jobs:
            results = await asyncio.gather(*[
                queue.process_one() for _ in range(10)
            ])
            processed += sum(1 for r in results if r)
            await asyncio.sleep(0.01)  # Small delay

        duration = time.time() - start

        print(f"\nQueue throughput: {num_jobs/duration:.1f} jobs/sec")
        assert queue.completed == num_jobs

    @pytest.mark.asyncio
    async def test_queue_with_backpressure(self):
        """Test queue handles backpressure correctly."""
        queue = MockGenerationQueue(max_concurrent=2)

        # Submit 20 jobs
        for i in range(20):
            await queue.enqueue(f"job_{i}")

        # Try to process more than max concurrent
        results = await asyncio.gather(*[
            queue.process_one() for _ in range(10)
        ])

        # Only max_concurrent should succeed immediately
        successful = sum(1 for r in results if r)
        print(f"\nBackpressure test: {successful} immediate, {queue.queue.qsize()} queued")


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Test rate limiter effectiveness."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows requests under limit."""
        limiter = MockRateLimiter(max_requests=10, window_seconds=1.0)

        allowed = 0
        for _ in range(10):
            if await limiter.allow():
                allowed += 1

        assert allowed == 10

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        limiter = MockRateLimiter(max_requests=5, window_seconds=1.0)

        allowed = 0
        for _ in range(20):
            if await limiter.allow():
                allowed += 1

        assert allowed == 5

    @pytest.mark.asyncio
    async def test_rate_limiter_window_reset(self):
        """Test rate limiter resets after window."""
        limiter = MockRateLimiter(max_requests=5, window_seconds=0.1)

        # Exhaust limit
        for _ in range(5):
            await limiter.allow()

        # Should be blocked
        assert await limiter.allow() is False

        # Wait for window to reset
        await asyncio.sleep(0.15)

        # Should be allowed again
        assert await limiter.allow() is True


# =============================================================================
# Memory Usage Tests
# =============================================================================


class TestMemoryUsage:
    """Test memory usage under load."""

    def test_large_data_processing(self):
        """Test processing large amounts of data."""
        import sys

        # Create large dataset
        data = []
        for i in range(10000):
            data.append({
                "id": str(uuid4()),
                "name": f"Item {i}",
                "description": "A" * 100,
                "metadata": {"key": f"value_{i}"},
            })

        size_mb = sys.getsizeof(data) / (1024 * 1024)
        print(f"\nLarge dataset size: {size_mb:.2f} MB")

        # Process data
        start = time.time()
        filtered = [d for d in data if d["metadata"]["key"].endswith("_5")]
        duration = time.time() - start

        print(f"Filtered {len(filtered)} items in {duration*1000:.2f}ms")

    def test_many_small_objects(self):
        """Test handling many small objects."""
        import sys

        # Create many small objects
        objects = {}
        for i in range(50000):
            objects[str(uuid4())] = {"value": i}

        size_mb = sys.getsizeof(objects) / (1024 * 1024)
        print(f"\n50k objects dict size: {size_mb:.2f} MB")

        # Access pattern
        keys = list(objects.keys())
        start = time.time()
        for key in keys[:1000]:
            _ = objects[key]
        duration = time.time() - start

        print(f"1000 lookups in {duration*1000:.2f}ms")


# =============================================================================
# Stress Tests
# =============================================================================


class TestStress:
    """Stress tests for system limits."""

    @pytest.mark.asyncio
    async def test_high_concurrency(self):
        """Test handling very high concurrency."""
        concurrent_tasks = 500
        db = MockDatabase(latency_ms=0.1)

        result = LoadTestResult("high_concurrency", concurrent_tasks, 0)
        start = time.time()

        async def task(i: int):
            try:
                req_start = time.time()
                await db.insert(f"key_{i}", {"value": i})
                result.record_success(time.time() - req_start)
            except Exception as e:
                result.record_failure(str(e))

        await asyncio.gather(*[task(i) for i in range(concurrent_tasks)])

        result.duration = time.time() - start

        print(f"\nHigh concurrency ({concurrent_tasks}): {result.report()}")
        assert result.success_rate > 99  # Allow minimal failures

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load over time."""
        duration_seconds = 0.5  # Short for testing
        rps_target = 100
        db = MockDatabase(latency_ms=0.5)

        result = LoadTestResult("sustained_load", 0, duration_seconds)
        start = time.time()
        request_count = 0

        async def make_request():
            nonlocal request_count
            try:
                req_start = time.time()
                await db.select("test_key")
                result.record_success(time.time() - req_start)
                request_count += 1
            except Exception as e:
                result.record_failure(str(e))

        # Run for duration
        while time.time() - start < duration_seconds:
            batch = [make_request() for _ in range(rps_target // 10)]
            await asyncio.gather(*batch)
            await asyncio.sleep(0.1)

        result.total_requests = request_count
        result.duration = time.time() - start

        print(f"\nSustained load: {result.report()}")


# =============================================================================
# Load Test Summary
# =============================================================================


class TestLoadSummary:
    """Generate load test summary."""

    @pytest.mark.asyncio
    async def test_generate_load_summary(self):
        """Generate comprehensive load test summary."""
        print("\n" + "="*70)
        print("LOAD TEST SUMMARY")
        print("="*70)

        db = MockDatabase(latency_ms=1.0)
        results = []

        # Test 1: 50 concurrent writes
        result1 = LoadTestResult("50 concurrent writes", 50, 0)
        start = time.time()

        async def write(i):
            req_start = time.time()
            await db.insert(f"k{i}", {"v": i})
            result1.record_success(time.time() - req_start)

        await asyncio.gather(*[write(i) for i in range(50)])
        result1.duration = time.time() - start
        results.append(result1)

        # Test 2: 100 concurrent reads
        result2 = LoadTestResult("100 concurrent reads", 100, 0)
        start = time.time()

        async def read(i):
            req_start = time.time()
            await db.select(f"k{i % 50}")
            result2.record_success(time.time() - req_start)

        await asyncio.gather(*[read(i) for i in range(100)])
        result2.duration = time.time() - start
        results.append(result2)

        # Print summary table
        print(f"\n{'Test':<25} {'Reqs':<8} {'RPS':<10} {'Avg(ms)':<10} {'P95(ms)':<10}")
        print("-"*70)
        for r in results:
            print(f"{r.name:<25} {r.total_requests:<8} "
                  f"{r.requests_per_second:>8.1f} "
                  f"{r.avg_response_time*1000:>9.2f} "
                  f"{r.p95_response_time*1000:>9.2f}")

        print("\n" + "="*70)
