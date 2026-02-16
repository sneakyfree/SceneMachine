# SceneMachine Performance Report & Budgets

**Date**: 2026-02-08
**Load Test Suite**: `tests/performance/load_test_suite.py` (657 lines, Locust-based)

---

## Load Test Profiles

| Profile | Users | Ramp | RPS Target | Duration |
|---------|-------|------|-----------|----------|
| Smoke | 1 | instant | 1 | 30s |
| Load | 10 | 1/s | 10 | 5m |
| Stress | 50 | 5/s | 50 | 10m |
| Spike | 100 | instant | 100 | 2m |

## Performance Budgets

| Endpoint Category | p50 | p95 | p99 | Max |
|-------------------|-----|-----|-----|-----|
| Health / Status | <10ms | <50ms | <100ms | 200ms |
| Auth (login/register) | <100ms | <300ms | <500ms | 1s |
| Project CRUD | <50ms | <200ms | <500ms | 1s |
| Character CRUD | <50ms | <200ms | <500ms | 1s |
| Generation Queue | <100ms | <300ms | <500ms | 1s |
| Timeline / Scenes | <50ms | <200ms | <500ms | 1s |
| Cost Estimation | <100ms | <300ms | <500ms | 1s |
| Copilot Chat | <500ms | <2s | <5s | 10s |
| File Upload | <500ms | <2s | <5s | 30s |

## Error Rate Budgets

| Condition | Max Error Rate |
|-----------|---------------|
| Normal load (10 users) | <0.1% |
| Stress load (50 users) | <1% |
| Spike load (100 users) | <5% |

## Resource Budgets

| Metric | Budget |
|--------|--------|
| API process RSS | <512MB |
| DB connections | <20 active |
| Response time degradation under load | <2x p95 vs single-user |

## Running Load Tests

```bash
# Smoke test
cd packages/core
locust -f tests/performance/load_test_suite.py --headless \
    -u 1 -r 1 --run-time 30s --host http://localhost:8000

# Load test (10 concurrent users)  
locust -f tests/performance/load_test_suite.py --headless \
    -u 10 -r 1 --run-time 5m --host http://localhost:8000

# Stress test
locust -f tests/performance/load_test_suite.py --headless \
    -u 50 -r 5 --run-time 10m --host http://localhost:8000
```

## Test Scenarios Covered

The load test suite (`load_test_suite.py`, 657 lines) includes:

1. **HealthCheckUser** (weight 3): `/health`, `/api/health`
2. **ProjectUser** (weight 5): List, get, settings
3. **CharacterLabUser** (weight 4): List, get, create characters
4. **GenerationUser** (weight 3): Queue status, job status, cost estimates
5. **TimelineUser** (weight 4): Timeline data, scene listing

## Monitoring During Tests

Use the `/metrics` Prometheus endpoint to observe:
- `scenemachine_db_latency_seconds` — DB response time
- `process_resident_memory_bytes` — Memory growth
- `scenemachine_provider_available` — Provider health under load
