# SceneMachine Monitoring Guide

This guide covers monitoring, metrics, alerting, and observability for SceneMachine.

## Table of Contents

1. [Metrics Overview](#metrics-overview)
2. [Health Endpoints](#health-endpoints)
3. [Logging](#logging)
4. [Alerting](#alerting)
5. [Dashboards](#dashboards)
6. [Performance Metrics](#performance-metrics)

---

## Metrics Overview

### Key Performance Indicators (KPIs)

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|-----------------|
| API Response Time (p95) | 95th percentile latency | < 200ms | > 500ms |
| Generation Success Rate | Successful video generations | > 95% | < 90% |
| Queue Wait Time | Average time in queue | < 60s | > 300s |
| Error Rate | Errors per minute | < 1% | > 5% |
| Active Jobs | Currently processing | 1-5 | > 10 |

### System Metrics

| Metric | Description | Warning | Critical |
|--------|-------------|---------|----------|
| CPU Usage | Processor utilization | > 70% | > 90% |
| Memory Usage | RAM utilization | > 80% | > 95% |
| Disk Usage | Storage utilization | > 80% | > 95% |
| DB Connections | Active connections | > 80% pool | 100% pool |

---

## Health Endpoints

### Endpoint Reference

```
GET /health              - Basic health check
GET /health/detailed     - Detailed component status
GET /health/providers    - Video provider status
GET /health/ready        - Kubernetes readiness probe
GET /health/live         - Kubernetes liveness probe
```

### Health Check Script

```bash
#!/bin/bash
# health_check.sh - Run periodically via cron

ENDPOINT="http://localhost:8000"

# Basic health
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $ENDPOINT/health)
if [ "$HEALTH" != "200" ]; then
    echo "CRITICAL: Health check failed with status $HEALTH"
    exit 2
fi

# Detailed health
DETAILED=$(curl -s $ENDPOINT/health/detailed)
STATUS=$(echo $DETAILED | jq -r '.status')

if [ "$STATUS" = "unhealthy" ]; then
    echo "CRITICAL: System unhealthy"
    echo $DETAILED | jq '.'
    exit 2
elif [ "$STATUS" = "degraded" ]; then
    echo "WARNING: System degraded"
    echo $DETAILED | jq '.'
    exit 1
fi

echo "OK: System healthy"
exit 0
```

---

## Logging

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| ERROR | System errors requiring attention | Database connection failed |
| WARNING | Potential issues | Provider rate limited |
| INFO | Normal operations | Job completed successfully |
| DEBUG | Detailed debugging | API request/response |

### Log Format

```json
{
  "timestamp": "2024-12-30T10:00:00.000Z",
  "level": "INFO",
  "logger": "scenemachine.services.generation",
  "message": "Job completed",
  "context": {
    "job_id": "abc123",
    "duration_ms": 45000,
    "provider": "replicate"
  },
  "request_id": "req-xyz789"
}
```

### Log Locations

| Environment | Location |
|-------------|----------|
| Development | Console (stdout) |
| Production | `/var/log/scenemachine/app.log` |
| Docker | Container stdout |
| Systemd | `journalctl -u scenemachine` |

### Log Rotation

```bash
# /etc/logrotate.d/scenemachine
/var/log/scenemachine/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 scenemachine scenemachine
}
```

### Key Log Patterns

```bash
# Find errors
grep '"level":"ERROR"' /var/log/scenemachine/app.log

# Find slow requests (>5s)
grep '"duration_ms":[5-9][0-9]{3}' /var/log/scenemachine/app.log

# Find circuit breaker events
grep 'Circuit.*transitioned' /var/log/scenemachine/app.log

# Find failed jobs
grep 'Job.*failed' /var/log/scenemachine/app.log
```

---

## Alerting

### Alert Configuration

#### Critical Alerts (Page Immediately)

| Alert | Condition | Description |
|-------|-----------|-------------|
| HealthCheckFailed | /health returns non-200 | System completely down |
| DatabaseDown | DB connection failed | No data access |
| AllProvidersDown | All circuit breakers open | No generation capability |
| DiskFull | Disk usage > 95% | System will fail |

#### Warning Alerts (Notify Team)

| Alert | Condition | Description |
|-------|-----------|-------------|
| HighErrorRate | Error rate > 5% for 5 min | Degraded performance |
| QueueBacklog | Pending jobs > 100 | Processing delays |
| ProviderDegraded | Single circuit breaker open | Reduced capacity |
| HighLatency | p95 > 500ms for 5 min | Slow responses |

### Alert Examples

```yaml
# Prometheus alerting rules
groups:
  - name: scenemachine
    rules:
      - alert: HealthCheckFailed
        expr: probe_success{job="scenemachine"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "SceneMachine health check failed"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Error rate above 5%"

      - alert: QueueBacklog
        expr: scenemachine_queue_pending_jobs > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Queue backlog exceeds 100 jobs"
```

---

## Dashboards

### Overview Dashboard

Key panels for the main operations dashboard:

1. **System Health**
   - Health status (healthy/degraded/unhealthy)
   - Component status grid
   - Provider availability

2. **Request Metrics**
   - Requests per second
   - Response time (p50, p95, p99)
   - Error rate percentage

3. **Queue Metrics**
   - Pending jobs count
   - Running jobs count
   - Processing rate (jobs/minute)
   - Average wait time

4. **Provider Metrics**
   - Circuit breaker states
   - Provider success rates
   - Provider latencies

### Example Grafana Panels

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])",
          "legendFormat": "{{method}} {{path}}"
        }
      ]
    },
    {
      "title": "Response Time",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "p95"
        }
      ]
    },
    {
      "title": "Queue Status",
      "type": "stat",
      "targets": [
        {
          "expr": "scenemachine_queue_pending_jobs",
          "legendFormat": "Pending"
        }
      ]
    }
  ]
}
```

---

## Performance Metrics

### API Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `http_requests_in_progress` | Gauge | Active requests |

### Queue Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `queue_pending_jobs` | Gauge | Jobs waiting |
| `queue_running_jobs` | Gauge | Jobs processing |
| `queue_completed_total` | Counter | Jobs completed |
| `queue_failed_total` | Counter | Jobs failed |
| `job_processing_seconds` | Histogram | Job duration |

### Provider Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `provider_requests_total` | Counter | Requests to provider |
| `provider_errors_total` | Counter | Provider errors |
| `provider_latency_seconds` | Histogram | Provider latency |
| `circuit_breaker_state` | Gauge | 0=closed, 1=open |

### Database Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `db_connections_active` | Gauge | Active connections |
| `db_query_duration_seconds` | Histogram | Query latency |
| `db_errors_total` | Counter | Database errors |

### Example Metrics Collection

```python
# Custom metrics with prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# Request counter
http_requests = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)

# Request duration histogram
http_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'path'],
    buckets=[.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)

# Queue gauge
queue_pending = Gauge(
    'scenemachine_queue_pending_jobs',
    'Number of pending jobs in queue'
)
```

---

## Best Practices

### Monitoring Checklist

- [ ] Health endpoints accessible
- [ ] Logs aggregated and searchable
- [ ] Key metrics collected
- [ ] Alerts configured for critical conditions
- [ ] Dashboard for operations team
- [ ] Regular review of metrics and thresholds

### Performance Baselines

Establish baselines during low-traffic periods:

1. Normal API response times (p50, p95, p99)
2. Normal queue processing rates
3. Normal memory and CPU usage
4. Normal provider latencies

Use these baselines to set alert thresholds.

### Incident Response

1. **Alert triggers** → Check dashboard
2. **Identify impact** → Which users/features affected?
3. **Diagnose** → Check logs, metrics, traces
4. **Mitigate** → Apply quick fixes
5. **Resolve** → Fix root cause
6. **Post-mortem** → Document and improve
