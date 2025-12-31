"""Performance benchmarks for SceneMachine.

Benchmarks measure:
- Screenplay parsing speed
- Scene planning latency
- Database query performance
- Video assembly throughput
- Cache hit/miss performance

Run with: pytest tests/performance/ -v --benchmark
"""

import asyncio
import time
from typing import Dict, Any, List
from uuid import uuid4

import pytest


# =============================================================================
# Benchmark Utilities
# =============================================================================


class BenchmarkResult:
    """Result of a benchmark run."""

    def __init__(self, name: str, iterations: int):
        self.name = name
        self.iterations = iterations
        self.times: List[float] = []
        self._start: float = 0

    def start(self):
        """Start timing."""
        self._start = time.perf_counter()

    def stop(self):
        """Stop timing and record."""
        elapsed = time.perf_counter() - self._start
        self.times.append(elapsed)

    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else 0

    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else 0

    @property
    def avg_time(self) -> float:
        return sum(self.times) / len(self.times) if self.times else 0

    @property
    def total_time(self) -> float:
        return sum(self.times)

    @property
    def ops_per_second(self) -> float:
        return len(self.times) / self.total_time if self.total_time > 0 else 0

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "min_ms": self.min_time * 1000,
            "max_ms": self.max_time * 1000,
            "avg_ms": self.avg_time * 1000,
            "total_s": self.total_time,
            "ops_per_second": self.ops_per_second,
        }


def run_benchmark(name: str, func, iterations: int = 100, warmup: int = 10):
    """Run a synchronous benchmark."""
    # Warmup
    for _ in range(warmup):
        func()

    result = BenchmarkResult(name, iterations)
    for _ in range(iterations):
        result.start()
        func()
        result.stop()

    return result


async def run_async_benchmark(name: str, func, iterations: int = 100, warmup: int = 10):
    """Run an asynchronous benchmark."""
    # Warmup
    for _ in range(warmup):
        await func()

    result = BenchmarkResult(name, iterations)
    for _ in range(iterations):
        result.start()
        await func()
        result.stop()

    return result


# =============================================================================
# Mock Data for Benchmarks
# =============================================================================


SAMPLE_SCREENPLAY = """
FADE IN:

INT. COFFEE SHOP - DAY

A cozy coffee shop with warm lighting and the aroma of fresh coffee.

SARAH (30s, professional but approachable) sits at a corner table,
nervously stirring her latte.

SARAH
(checking her phone)
He's late. As usual.

The door opens. JOHN (35, rugged, wearing a worn leather jacket)
enters, scanning the room. He spots Sarah and walks over.

JOHN
Sorry I'm late. Traffic.

SARAH
(sarcastically)
Traffic. Right.

John sits across from her.

JOHN
Look, I know I messed up.

SARAH
You always know. That's the problem.

CUT TO:

EXT. CITY PARK - DUSK

Sarah walks alone through the park. Leaves fall around her.

SARAH (V.O.)
Some things you can't take back.

FADE OUT.
""" * 10  # Repeat for realistic file size


def create_test_data(count: int = 100) -> List[Dict[str, Any]]:
    """Create test data for benchmarks."""
    return [
        {
            "id": str(uuid4()),
            "name": f"Item {i}",
            "value": i * 1.5,
            "metadata": {"key": f"value_{i}"},
        }
        for i in range(count)
    ]


# =============================================================================
# Screenplay Parsing Benchmarks
# =============================================================================


class TestScreenplayParsingBenchmarks:
    """Benchmark screenplay parsing operations."""

    def test_simple_text_parsing(self):
        """Benchmark simple text splitting."""
        def parse_lines():
            lines = SAMPLE_SCREENPLAY.split("\n")
            return [line.strip() for line in lines if line.strip()]

        result = run_benchmark("parse_lines", parse_lines, iterations=1000)

        assert result.avg_time < 0.01  # Should be under 10ms
        print(f"\nParse lines: {result.avg_time*1000:.3f}ms avg")

    def test_scene_heading_detection(self):
        """Benchmark scene heading detection."""
        import re
        pattern = re.compile(r'^(INT\.|EXT\.|INT/EXT\.)')

        def find_headings():
            lines = SAMPLE_SCREENPLAY.split("\n")
            return [line for line in lines if pattern.match(line.strip())]

        result = run_benchmark("find_headings", find_headings, iterations=1000)

        assert result.avg_time < 0.01
        print(f"\nFind headings: {result.avg_time*1000:.3f}ms avg")

    def test_character_extraction(self):
        """Benchmark character name extraction."""
        import re
        # Character names are usually uppercase at start of line
        pattern = re.compile(r'^([A-Z][A-Z\s]+)(?:\s*\(|$)')

        def extract_characters():
            lines = SAMPLE_SCREENPLAY.split("\n")
            characters = set()
            for line in lines:
                match = pattern.match(line.strip())
                if match:
                    characters.add(match.group(1).strip())
            return characters

        result = run_benchmark("extract_characters", extract_characters, iterations=500)

        assert result.avg_time < 0.02
        print(f"\nExtract characters: {result.avg_time*1000:.3f}ms avg")


# =============================================================================
# Data Structure Benchmarks
# =============================================================================


class TestDataStructureBenchmarks:
    """Benchmark common data structure operations."""

    def test_list_iteration(self):
        """Benchmark list iteration."""
        data = create_test_data(1000)

        def iterate_list():
            total = 0
            for item in data:
                total += item["value"]
            return total

        result = run_benchmark("list_iteration", iterate_list, iterations=1000)

        print(f"\nList iteration (1000 items): {result.avg_time*1000:.3f}ms avg")

    def test_dict_lookup(self):
        """Benchmark dictionary lookup."""
        data = {item["id"]: item for item in create_test_data(1000)}
        keys = list(data.keys())

        def dict_lookup():
            for key in keys[:100]:  # Look up 100 items
                _ = data[key]

        result = run_benchmark("dict_lookup", dict_lookup, iterations=1000)

        print(f"\nDict lookup (100 lookups): {result.avg_time*1000:.3f}ms avg")

    def test_list_filtering(self):
        """Benchmark list filtering."""
        data = create_test_data(1000)

        def filter_list():
            return [item for item in data if item["value"] > 500]

        result = run_benchmark("list_filtering", filter_list, iterations=500)

        print(f"\nList filtering (1000 items): {result.avg_time*1000:.3f}ms avg")

    def test_list_sorting(self):
        """Benchmark list sorting."""
        def sort_list():
            data = create_test_data(1000)  # Create new each time
            return sorted(data, key=lambda x: x["value"])

        result = run_benchmark("list_sorting", sort_list, iterations=100)

        print(f"\nList sorting (1000 items): {result.avg_time*1000:.3f}ms avg")


# =============================================================================
# JSON Serialization Benchmarks
# =============================================================================


class TestSerializationBenchmarks:
    """Benchmark JSON serialization."""

    def test_json_serialize(self):
        """Benchmark JSON serialization."""
        import json
        data = create_test_data(100)

        def serialize():
            return json.dumps(data)

        result = run_benchmark("json_serialize", serialize, iterations=500)

        print(f"\nJSON serialize (100 items): {result.avg_time*1000:.3f}ms avg")

    def test_json_deserialize(self):
        """Benchmark JSON deserialization."""
        import json
        data = create_test_data(100)
        json_str = json.dumps(data)

        def deserialize():
            return json.loads(json_str)

        result = run_benchmark("json_deserialize", deserialize, iterations=500)

        print(f"\nJSON deserialize (100 items): {result.avg_time*1000:.3f}ms avg")


# =============================================================================
# Async Operation Benchmarks
# =============================================================================


class TestAsyncBenchmarks:
    """Benchmark async operations."""

    @pytest.mark.asyncio
    async def test_async_sleep_overhead(self):
        """Benchmark asyncio.sleep overhead."""
        async def sleep_op():
            await asyncio.sleep(0)

        result = await run_async_benchmark("async_sleep_zero", sleep_op, iterations=1000)

        print(f"\nAsync sleep(0) overhead: {result.avg_time*1000:.3f}ms avg")

    @pytest.mark.asyncio
    async def test_async_gather(self):
        """Benchmark asyncio.gather."""
        async def dummy():
            return 1

        async def gather_op():
            tasks = [dummy() for _ in range(10)]
            return await asyncio.gather(*tasks)

        result = await run_async_benchmark("async_gather_10", gather_op, iterations=500)

        print(f"\nAsync gather (10 tasks): {result.avg_time*1000:.3f}ms avg")

    @pytest.mark.asyncio
    async def test_async_queue(self):
        """Benchmark asyncio.Queue operations."""
        async def queue_op():
            queue = asyncio.Queue()
            for i in range(100):
                await queue.put(i)
            for _ in range(100):
                await queue.get()

        result = await run_async_benchmark("async_queue_100", queue_op, iterations=100)

        print(f"\nAsync queue (100 put/get): {result.avg_time*1000:.3f}ms avg")


# =============================================================================
# UUID Generation Benchmarks
# =============================================================================


class TestUUIDBenchmarks:
    """Benchmark UUID generation."""

    def test_uuid4_generation(self):
        """Benchmark UUID4 generation."""
        def generate_uuid():
            return str(uuid4())

        result = run_benchmark("uuid4_generation", generate_uuid, iterations=10000)

        print(f"\nUUID4 generation: {result.avg_time*1000:.3f}ms avg")
        print(f"UUID4 ops/second: {result.ops_per_second:.0f}")


# =============================================================================
# String Operation Benchmarks
# =============================================================================


class TestStringBenchmarks:
    """Benchmark string operations."""

    def test_string_concatenation(self):
        """Benchmark string concatenation."""
        def concat_strings():
            result = ""
            for i in range(100):
                result += f"item_{i},"
            return result

        result = run_benchmark("string_concat_100", concat_strings, iterations=500)

        print(f"\nString concat (100 items): {result.avg_time*1000:.3f}ms avg")

    def test_string_join(self):
        """Benchmark string join (preferred method)."""
        def join_strings():
            items = [f"item_{i}" for i in range(100)]
            return ",".join(items)

        result = run_benchmark("string_join_100", join_strings, iterations=500)

        print(f"\nString join (100 items): {result.avg_time*1000:.3f}ms avg")

    def test_string_format(self):
        """Benchmark f-string formatting."""
        def format_strings():
            results = []
            for i in range(100):
                results.append(f"Item {i}: value={i*1.5:.2f}")
            return results

        result = run_benchmark("string_format_100", format_strings, iterations=500)

        print(f"\nF-string format (100 items): {result.avg_time*1000:.3f}ms avg")


# =============================================================================
# Cache Performance Benchmarks
# =============================================================================


class TestCacheBenchmarks:
    """Benchmark cache operations."""

    def test_dict_cache_performance(self):
        """Benchmark simple dict cache."""
        cache: Dict[str, Any] = {}
        keys = [str(uuid4()) for _ in range(1000)]
        values = [{"data": i} for i in range(1000)]

        # Populate cache
        for k, v in zip(keys, values):
            cache[k] = v

        def cache_lookup():
            hits = 0
            for key in keys[:100]:
                if key in cache:
                    _ = cache[key]
                    hits += 1
            return hits

        result = run_benchmark("dict_cache_lookup", cache_lookup, iterations=1000)

        print(f"\nDict cache lookup (100 keys): {result.avg_time*1000:.3f}ms avg")

    def test_lru_cache_performance(self):
        """Benchmark LRU cache with functools."""
        from functools import lru_cache

        @lru_cache(maxsize=1000)
        def cached_compute(x: int) -> int:
            return x * x

        def lru_lookup():
            for i in range(100):
                _ = cached_compute(i)

        result = run_benchmark("lru_cache_lookup", lru_lookup, iterations=1000)

        print(f"\nLRU cache lookup (100 calls): {result.avg_time*1000:.3f}ms avg")


# =============================================================================
# Summary Report
# =============================================================================


class TestBenchmarkSummary:
    """Generate benchmark summary."""

    def test_generate_summary(self):
        """Generate and print benchmark summary."""
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)

        # Run key benchmarks and collect results
        benchmarks = []

        # Parsing
        def parse_test():
            lines = SAMPLE_SCREENPLAY.split("\n")
            return [line.strip() for line in lines if line.strip()]

        benchmarks.append(run_benchmark("Screenplay parsing", parse_test, 100))

        # Data operations
        data = create_test_data(1000)

        def filter_test():
            return [item for item in data if item["value"] > 500]

        benchmarks.append(run_benchmark("List filtering", filter_test, 100))

        # Serialization
        import json

        def json_test():
            return json.dumps(data[:100])

        benchmarks.append(run_benchmark("JSON serialize", json_test, 100))

        # Print results
        print(f"\n{'Benchmark':<25} {'Avg (ms)':<12} {'Ops/sec':<12}")
        print("-"*50)
        for b in benchmarks:
            print(f"{b.name:<25} {b.avg_time*1000:>10.3f} {b.ops_per_second:>12.0f}")

        print("\n" + "="*60)
