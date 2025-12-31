# SceneMachine Operations Guide

This guide covers the operational aspects of running SceneMachine in production, including monitoring, maintenance, and troubleshooting.

## Table of Contents

1. [Health Monitoring](#health-monitoring)
2. [Circuit Breaker Management](#circuit-breaker-management)
3. [Queue Management](#queue-management)
4. [Database Maintenance](#database-maintenance)
5. [Performance Tuning](#performance-tuning)
6. [Troubleshooting](#troubleshooting)
7. [Disaster Recovery](#disaster-recovery)

---

## Health Monitoring

### Health Check Endpoints

SceneMachine exposes several health check endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Basic health check (database connectivity) |
| `GET /health/detailed` | Detailed health with component status |
| `GET /health/providers` | Video generation provider status |

### Basic Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### Detailed Health Check

```bash
curl http://localhost:8000/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy", "latency_ms": 5.2},
    "storage": {"status": "healthy", "free_space_gb": 100},
    "memory": {"status": "healthy", "used_percent": 45},
    "queue": {"status": "healthy", "pending_jobs": 3}
  }
}
```

### Provider Health

```bash
curl http://localhost:8000/health/providers
```

Response:
```json
{
  "providers": {
    "replicate": {
      "status": "healthy",
      "available": true,
      "circuit_state": "closed",
      "models": ["minimax/video-01", "luma/photon"]
    },
    "fal": {
      "status": "healthy",
      "available": true,
      "circuit_state": "closed",
      "models": ["ltx-video", "cogvideox"]
    }
  }
}
```

### Health Status Values

| Status | Description |
|--------|-------------|
| `healthy` | All systems operational |
| `degraded` | Some issues but functional |
| `unhealthy` | Critical failures |
| `unavailable` | Service not available |

---

## Circuit Breaker Management

SceneMachine uses circuit breakers to prevent cascading failures when external services are unavailable.

### Circuit Breaker States

```
CLOSED → OPEN → HALF_OPEN → CLOSED
         ↑          ↓
         ←──────────←
```

| State | Description |
|-------|-------------|
| `closed` | Normal operation, requests flow through |
| `open` | Failing, requests rejected immediately |
| `half_open` | Testing if service recovered |

### Provider Circuit Breaker Configuration

| Provider | Failure Threshold | Recovery Timeout | Call Timeout |
|----------|------------------|------------------|--------------|
| Replicate | 3 failures | 60 seconds | 5 minutes |
| Fal.ai | 3 failures | 60 seconds | 5 minutes |
| ComfyUI | 5 failures | 30 seconds | 10 minutes |
| RunPod | 3 failures | 120 seconds | 10 minutes |

### Viewing Circuit Breaker Status

```bash
curl http://localhost:8000/api/v1/settings/circuit-breakers
```

### Manually Resetting a Circuit Breaker

```bash
curl -X POST http://localhost:8000/api/v1/settings/circuit-breakers/reset?provider=replicate
```

### When Circuits Open

When a circuit breaker opens:
1. All new requests to that provider are immediately rejected
2. Jobs are re-queued with fallback providers (if configured)
3. After the recovery timeout, one test request is allowed
4. If successful, circuit closes; if not, remains open

---

## Queue Management

### Viewing Queue Status

```bash
curl http://localhost:8000/api/v1/generation/queue
```

Response:
```json
{
  "pending_count": 5,
  "running_count": 3,
  "completed_today": 47,
  "failed_today": 2,
  "avg_processing_time_ms": 45000
}
```

### Queue Priority Levels

| Priority | Value | Description |
|----------|-------|-------------|
| URGENT | 100 | Process immediately |
| HIGH | 50 | Before normal jobs |
| NORMAL | 0 | Default priority |
| LOW | -50 | Process when idle |
| BACKGROUND | -100 | Lowest priority |

### Managing Queue Workers

```bash
# Check worker status
curl http://localhost:8000/api/v1/generation/worker/status

# Pause queue processing
curl -X POST http://localhost:8000/api/v1/generation/worker/pause

# Resume queue processing
curl -X POST http://localhost:8000/api/v1/generation/worker/resume
```

### Queue Backlog Alerts

Configure alerts when queue backlog exceeds thresholds:

| Level | Threshold | Action |
|-------|-----------|--------|
| Warning | 50 pending | Monitor closely |
| Critical | 200 pending | Scale workers |
| Emergency | 500 pending | Throttle new submissions |

---

## Database Maintenance

### Running Migrations

```bash
cd packages/core
alembic upgrade head
```

### Checking Migration Status

```bash
alembic current
alembic history
```

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h localhost -U scenemachine scenemachine_db > backup_$(date +%Y%m%d).sql

# SQLite backup (development)
cp data/scenemachine.db backups/scenemachine_$(date +%Y%m%d).db
```

### Integrity Constraints

SceneMachine enforces data integrity at the database level:

| Table | Constraint | Description |
|-------|------------|-------------|
| projects | ck_projects_state | Valid project states only |
| shots | ck_shots_duration_positive | Duration 0-60 seconds |
| generation_jobs | ck_generation_jobs_progress | Progress 0-100% |
| generation_jobs | ck_generation_jobs_priority | Priority -100 to 100 |

### Query Optimization

Key indexes for common queries:
- `ix_scenes_project_sequence` - Scene ordering
- `ix_shots_scene_sequence` - Shot ordering
- `ix_generation_jobs_queue` - Job queue ordering (partial index)
- `ix_shots_active` - Active shots (partial index)

---

## Performance Tuning

### Recommended Settings

| Setting | Development | Production |
|---------|-------------|------------|
| Max concurrent jobs | 1 | 3-5 |
| Database pool size | 5 | 20 |
| Rate limit (req/min) | 1000 | 200 |
| Cache TTL | 60s | 300s |
| Worker poll interval | 5s | 1s |

### Caching Configuration

```python
# LRU Cache settings
LRU_CACHE_MAX_SIZE = 1000
LRU_CACHE_TTL_SECONDS = 300

# LLM Response Cache
LLM_CACHE_MAX_SIZE = 500
LLM_CACHE_TTL_SECONDS = 3600
```

### Memory Optimization

- Limit concurrent video processing to prevent memory exhaustion
- Use streaming for large file uploads
- Implement pagination for list endpoints (default: 20 items)

---

## Troubleshooting

### Common Issues

#### Jobs Stuck in "Preparing" State

**Cause**: Provider API timeout or network issue

**Solution**:
1. Check provider health: `GET /health/providers`
2. Check circuit breaker state
3. Cancel stuck job: `POST /api/v1/generation/jobs/{id}/cancel`
4. Retry with different provider if available

#### High Memory Usage

**Cause**: Too many concurrent video processing jobs

**Solution**:
1. Reduce `max_concurrent_jobs` setting
2. Pause queue processing temporarily
3. Check for memory leaks in custom providers

#### Database Connection Errors

**Cause**: Connection pool exhausted

**Solution**:
1. Increase pool size in configuration
2. Check for connection leaks
3. Reduce concurrent requests

#### Provider Rate Limiting

**Cause**: Too many API requests to provider

**Solution**:
1. Circuit breaker will auto-throttle
2. Increase delays between requests
3. Consider using multiple API keys

### Log Analysis

Key log patterns to monitor:

```
# Circuit breaker opened
Circuit 'provider:replicate' transitioned from closed to open

# Job failure
Job {job_id} failed: {error_message}

# Rate limit hit
Rate limit exceeded for client {client_id}
```

### Recovery Procedures

#### Recovering from Provider Outage

1. Circuit breaker automatically opens after failure threshold
2. Jobs re-queued to fallback providers (if configured)
3. Monitor `/health/providers` for recovery
4. Circuit auto-closes after successful test requests

#### Recovering from Database Issues

1. Stop application: `systemctl stop scenemachine`
2. Restore from backup if needed
3. Run migrations: `alembic upgrade head`
4. Start application: `systemctl start scenemachine`
5. Verify health: `GET /health/detailed`

---

## Disaster Recovery

### Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single component failure | 5 minutes | 0 (no data loss) |
| Full system failure | 30 minutes | 30 minutes |
| Data center failure | 4 hours | 1 hour |

### Backup Schedule

| Data | Frequency | Retention |
|------|-----------|-----------|
| Database | Hourly | 7 days |
| Generated videos | Daily | 30 days |
| Configurations | On change | Forever |

### Recovery Steps

1. **Assess the failure**
   - Check health endpoints
   - Review logs for error patterns
   - Identify affected components

2. **Isolate the problem**
   - Pause queue processing if generation issues
   - Enable maintenance mode if needed

3. **Restore services**
   - Restart failed components
   - Restore from backup if data loss
   - Verify data integrity

4. **Verify recovery**
   - Check all health endpoints
   - Process test job through queue
   - Monitor for recurring issues

### Contact Information

For production support:
- Check logs first: `/var/log/scenemachine/`
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- Documentation: `/docs/` directory
